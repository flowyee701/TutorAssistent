"""CLI-оркестратор парсера: download → parse → tag.

Примеры:
    python -m parser.pipeline sources --template
    python -m parser.pipeline download --collection math_ege_demo
    python -m parser.pipeline parse    --collection math_ege_demo --ocr
    python -m parser.pipeline tag      --subject MATH_PROFILE --exam EGE
    python -m parser.pipeline all      --collection math_ege_demo
    python -m parser.pipeline stats    --subject MATH_PROFILE --exam EGE

Идемпотентность: download пропускает скачанные файлы, parse дедуплицирует
по content_hash, tag берёт только задачи без тегов.
"""

from __future__ import annotations

import argparse
import asyncio
import logging

from sqlalchemy import func, select

from core.db.engine import SessionLocal
from core.db.models import ExamType, Subject, Task, VerificationStatus
from parser import downloader, fipi_parser
from parser.sources import RAW_DIR, load_sources, write_template
from parser.tagger import tag_tasks, tagging_coverage

logger = logging.getLogger(__name__)


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


# --------------------------------------------------------------------------- #
# Команды
# --------------------------------------------------------------------------- #

def cmd_sources(args: argparse.Namespace) -> None:
    path = write_template()
    logger.info("шаблон источников записан: %s — отредактируй URL и запусти download", path)


def cmd_download(args: argparse.Namespace) -> None:
    pdfs = downloader.download_collection(args.collection)
    logger.info("скачано/готово файлов: %d", len(pdfs))


async def _parse(args: argparse.Namespace) -> None:
    collection = args.collection
    # сопоставим имя файла → источник (для source_label/subject/exam)
    by_name = {s.filename: s for s in load_sources(collection)}
    raw_dir = RAW_DIR / collection
    if not raw_dir.exists():
        logger.error("нет папки %s — сначала download", raw_dir)
        return

    pdf_files = sorted(raw_dir.glob("*.pdf"))
    if not pdf_files:
        logger.error("в %s нет PDF", raw_dir)
        return

    default_subject = Subject[args.subject]
    default_exam = ExamType[args.exam]
    total_created = total_skipped = 0

    async with SessionLocal() as session:
        for pdf in pdf_files:
            src = by_name.get(pdf.name)
            source_label = src.source_label if src else pdf.stem.upper()
            subject = src.subject if src else default_subject
            exam = src.exam_type if src else default_exam

            tasks = fipi_parser.parse_pdf(
                pdf,
                source_label=source_label,
                subject=subject,
                exam_type=exam,
                ocr_images=args.ocr,
            )
            created, skipped = await fipi_parser.persist_tasks(session, tasks)
            total_created += created
            total_skipped += skipped

    logger.info("PARSE итог: создано %d, пропущено (дубли) %d", total_created, total_skipped)


def cmd_parse(args: argparse.Namespace) -> None:
    asyncio.run(_parse(args))


async def _tag(args: argparse.Namespace) -> None:
    async with SessionLocal() as session:
        stats = await tag_tasks(
            session,
            Subject[args.subject],
            ExamType[args.exam],
            batch_size=args.batch_size,
            max_batches=args.max_batches,
        )
    logger.info("TAG итог: %s", stats)


def cmd_tag(args: argparse.Namespace) -> None:
    asyncio.run(_tag(args))


async def _all(args: argparse.Namespace) -> None:
    downloader.download_collection(args.collection)
    await _parse(args)
    await _tag(args)


def cmd_all(args: argparse.Namespace) -> None:
    asyncio.run(_all(args))


async def _stats(args: argparse.Namespace) -> None:
    subject = Subject[args.subject]
    exam = ExamType[args.exam]
    async with SessionLocal() as session:
        total = await session.scalar(
            select(func.count(Task.id)).where(
                Task.subject == subject, Task.exam_type == exam, Task.deleted_at.is_(None)
            )
        )
        by_status = {}
        for st in VerificationStatus:
            cnt = await session.scalar(
                select(func.count(Task.id)).where(
                    Task.subject == subject,
                    Task.exam_type == exam,
                    Task.verification_status == st,
                )
            )
            by_status[st.value] = cnt or 0
        coverage = await tagging_coverage(session, subject, exam)

    print(f"\n=== {subject.value} / {exam.value} ===")
    print(f"Всего задач:        {total or 0}")
    print(f"По статусам:        {by_status}")
    print(f"С тегами (не uncl): {coverage['classified']} ({coverage['pct_classified']}%)")
    print("\nКритерии Спринта 2:")
    print(f"  [{'x' if (total or 0) >= 1500 else ' '}] ≥1500 задач")
    print(f"  [{'x' if coverage['pct_classified'] >= 80 else ' '}] ≥80% с тегами")
    print(
        f"  [{'x' if by_status.get('HUMAN_VERIFIED', 0) >= 500 else ' '}] "
        f"≥500 HUMAN_VERIFIED"
    )


def cmd_stats(args: argparse.Namespace) -> None:
    asyncio.run(_stats(args))


# --------------------------------------------------------------------------- #
# Парсер аргументов
# --------------------------------------------------------------------------- #

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="parser.pipeline", description="FIPI parser pipeline")
    sub = p.add_subparsers(dest="command", required=True)

    def add_subject_exam(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--subject", default="MATH_PROFILE", choices=[s.name for s in Subject])
        sp.add_argument("--exam", default="EGE", choices=[e.name for e in ExamType])

    sp = sub.add_parser("sources", help="записать шаблон sources.json")
    sp.add_argument("--template", action="store_true")
    sp.set_defaults(func=cmd_sources)

    sp = sub.add_parser("download", help="скачать коллекцию PDF")
    sp.add_argument("--collection", default="math_ege_demo")
    sp.set_defaults(func=cmd_download)

    sp = sub.add_parser("parse", help="распарсить PDF в Task")
    sp.add_argument("--collection", default="math_ege_demo")
    sp.add_argument("--ocr", action="store_true", help="OCR формул через pix2tex")
    add_subject_exam(sp)
    sp.set_defaults(func=cmd_parse)

    sp = sub.add_parser("tag", help="тегировать задачи через YandexGPT")
    add_subject_exam(sp)
    sp.add_argument("--batch-size", type=int, default=15)
    sp.add_argument("--max-batches", type=int, default=None)
    sp.set_defaults(func=cmd_tag)

    sp = sub.add_parser("all", help="download + parse + tag")
    sp.add_argument("--collection", default="math_ege_demo")
    sp.add_argument("--ocr", action="store_true")
    add_subject_exam(sp)
    sp.add_argument("--batch-size", type=int, default=15)
    sp.add_argument("--max-batches", type=int, default=None)
    sp.set_defaults(func=cmd_all)

    sp = sub.add_parser("stats", help="статистика и критерии готовности")
    add_subject_exam(sp)
    sp.set_defaults(func=cmd_stats)

    return p


def main() -> None:
    _setup_logging()
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
