"""Парсинг PDF ФИПИ в записи Task.

PyMuPDF (fitz) даёт текст и встроенные изображения. Задачи режем по
нумерации (regex по началу строки). Для каждой задачи:
  - statement_text  — plain (для full-text поиска),
  - statement_latex — начальный LaTeX (= текст; формулы из картинок дораспознаются
    через latex_ocr при ocr_images=True),
  - image_pngs      — PNG-байты встроенных картинок,
  - answer          — если найден маркер «Ответ» в задаче или в блоке ответов.

Дедупликация — по content_hash (SHA-256 нормализованного текста).

ВНИМАНИЕ: разметка PDF у ФИПИ нестабильна. Регэкспы — отправная точка,
их почти наверняка придётся подстраивать под конкретные файлы.
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

import fitz  # PyMuPDF
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.models import ExamType, Subject, Task, VerificationStatus
from core.services.storage import get_storage

logger = logging.getLogger(__name__)

# Заголовок задачи в начале строки: «12.» / «12)» / «Задание 12.»
TASK_HEADER_RE = re.compile(r"(?m)^[ \t]*(?:Задание[ \t]+)?(\d{1,2})[.)][ \t]+")
# Маркер ответа внутри задачи
ANSWER_INLINE_RE = re.compile(r"Ответ[:.]?\s*([^\n]+)", re.IGNORECASE)
# Блок ответов в конце варианта: «1) 5», «2. -3» ...
ANSWER_BLOCK_LINE_RE = re.compile(r"(?m)^\s*(\d{1,2})[.)]\s+([^\n]+)")
# Мусорные строки (колонтитулы, копирайт, нумерация страниц)
JUNK_LINE_RE = re.compile(
    r"^\s*(©.*ФИПИ|.*Единый государственный экзамен.*|Стр\.?\s*\d+|\d+\s*из\s*\d+)\s*$",
    re.IGNORECASE,
)
MIN_STATEMENT_LEN = 20


@dataclass(slots=True)
class ParsedTask:
    statement_text: str
    statement_latex: str
    source_label: str
    subject: Subject
    exam_type: ExamType
    page_no: int
    task_number: int | None = None
    answer: str | None = None
    image_pngs: list[bytes] = field(default_factory=list)

    @property
    def content_hash(self) -> str:
        return hashlib.sha256(normalize(self.statement_text).encode("utf-8")).hexdigest()


def normalize(text: str) -> str:
    """Схлопывает пробелы/переводы строк для устойчивого хэша и поиска."""
    return re.sub(r"\s+", " ", text).strip()


def _strip_junk(text: str) -> str:
    return "\n".join(line for line in text.splitlines() if not JUNK_LINE_RE.match(line))


def _page_text(page: fitz.Page) -> str:
    return _strip_junk(page.get_text("text"))


def _page_images(doc: fitz.Document, page: fitz.Page) -> list[bytes]:
    """PNG-байты встроенных растровых изображений страницы."""
    out: list[bytes] = []
    for img in page.get_images(full=True):
        xref = img[0]
        try:
            pix = fitz.Pixmap(doc, xref)
            if pix.n - pix.alpha >= 4:  # CMYK → RGB
                pix = fitz.Pixmap(fitz.csRGB, pix)
            out.append(pix.tobytes("png"))
        except Exception as exc:  # noqa: BLE001
            logger.debug("image xref=%s skip: %s", xref, exc)
    return out


def split_into_tasks(text: str) -> list[tuple[int | None, str]]:
    """Режет текст по заголовкам задач. Возвращает [(номер, текст), ...]."""
    matches = list(TASK_HEADER_RE.finditer(text))
    if not matches:
        return []

    chunks: list[tuple[int | None, str]] = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        number = int(m.group(1))
        body = text[start:end].strip()
        if len(normalize(body)) >= MIN_STATEMENT_LEN:
            chunks.append((number, body))
    return chunks


def parse_answers_block(text: str) -> dict[int, str]:
    """Ищет блок «Ответы …» в хвосте текста, мапит номер → ответ."""
    idx = None
    for m in re.finditer(r"(?im)^\s*(ответы|правильные ответы)\s*$", text):
        idx = m.end()
    if idx is None:
        return {}
    tail = text[idx:]
    return {int(n): ans.strip() for n, ans in ANSWER_BLOCK_LINE_RE.findall(tail)}


def parse_pdf(
    path: Path,
    *,
    source_label: str,
    subject: Subject = Subject.MATH_PROFILE,
    exam_type: ExamType = ExamType.EGE,
    ocr_images: bool = False,
) -> list[ParsedTask]:
    """Извлекает задачи из одного PDF.

    ocr_images=True — прогоняет встроенные картинки через pix2tex и дописывает
    распознанные формулы в statement_latex (нужна группа зависимостей [parser]).
    """
    doc = fitz.open(path)
    full_text_parts: list[str] = []
    page_images: dict[int, list[bytes]] = {}

    for page_no, page in enumerate(doc):
        full_text_parts.append(f"\n<<<PAGE {page_no}>>>\n{_page_text(page)}")
        imgs = _page_images(doc, page)
        if imgs:
            page_images[page_no] = imgs

    full_text = "".join(full_text_parts)
    # Уберём страничные маркеры для разбивки, но запомним границы для картинок
    clean_text = re.sub(r"\n<<<PAGE \d+>>>\n", "\n", full_text)

    answers = parse_answers_block(clean_text)
    tasks: list[ParsedTask] = []

    for number, body in split_into_tasks(clean_text):
        inline = ANSWER_INLINE_RE.search(body)
        answer = inline.group(1).strip() if inline else answers.get(number or -1)

        # На какой странице началась задача — приблизим по позиции в full_text
        page_no = _guess_page(full_text, body)
        imgs = page_images.get(page_no, [])

        statement_latex = body.strip()
        if ocr_images and imgs:
            statement_latex = _append_ocr_formulas(statement_latex, imgs)

        tasks.append(
            ParsedTask(
                statement_text=normalize(body),
                statement_latex=statement_latex,
                source_label=source_label,
                subject=subject,
                exam_type=exam_type,
                page_no=page_no,
                task_number=number,
                answer=answer,
                image_pngs=imgs,
            )
        )

    doc.close()
    logger.info("%s: распарсено %d задач", path.name, len(tasks))
    return tasks


def _append_ocr_formulas(statement_latex: str, images: list[bytes]) -> str:
    """Распознаёт формулы с картинок и дописывает их блоками \\[ ... \\]."""
    from parser.latex_ocr import get_ocr

    ocr = get_ocr()
    blocks: list[str] = []
    for png in images:
        res = ocr.image_to_latex(png)
        if res.latex and res.confidence != "low":
            blocks.append(f"\\[{res.latex}\\]")
    if blocks:
        return statement_latex + "\n" + "\n".join(blocks)
    return statement_latex


def _guess_page(full_text: str, body: str) -> int:
    snippet = body[:40]
    pos = full_text.find(snippet)
    if pos < 0:
        return 0
    page_markers = [m for m in re.finditer(r"<<<PAGE (\d+)>>>", full_text) if m.start() < pos]
    return int(page_markers[-1].group(1)) if page_markers else 0


async def persist_tasks(session: AsyncSession, tasks: list[ParsedTask]) -> tuple[int, int]:
    """Пишет задачи в БД. Возвращает (создано, пропущено-как-дубль)."""
    storage = get_storage()
    created = skipped = 0

    for pt in tasks:
        h = pt.content_hash
        exists = await session.scalar(select(Task.id).where(Task.content_hash == h))
        if exists:
            skipped += 1
            continue

        image_urls: list[str] = []
        for i, png in enumerate(pt.image_pngs):
            key = f"tasks/{pt.source_label.lower()}/{h[:16]}_p{pt.page_no}_i{i}.png"
            try:
                image_urls.append(storage.save_png(png, key))
            except Exception:  # noqa: BLE001
                logger.exception("не удалось сохранить изображение %s", key)

        session.add(
            Task(
                subject=pt.subject,
                exam_type=pt.exam_type,
                task_number=pt.task_number,
                difficulty=3,
                source=pt.source_label,
                source_metadata={"page": pt.page_no},
                statement_latex=pt.statement_latex,
                statement_text=pt.statement_text,
                image_urls=image_urls,
                answer=pt.answer,
                content_hash=h,
                verification_status=VerificationStatus.AUTO_PARSED,
            )
        )
        created += 1

    await session.commit()
    logger.info("persist: создано %d, пропущено (дубли) %d", created, skipped)
    return created, skipped
