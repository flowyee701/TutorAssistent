"""Сидинг дерева тегов из JSON-файлов в таблицу task_tags.

Запуск:
    python -m core.db.seed                 # все файлы из core/db/tags/
    python -m core.db.seed tags_math_ege.json
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.engine import SessionLocal
from core.db.models import ExamType, Subject, TaskTag

logger = logging.getLogger(__name__)

TAGS_DIR = Path(__file__).parent / "tags"


async def _upsert_node(
    session: AsyncSession,
    *,
    code: str,
    path: str,
    name: str,
    subject: Subject,
    exam_type: ExamType,
    parent_id: int | None,
    depth: int,
    sort_order: int,
) -> TaskTag:
    """Создаёт или обновляет тег по уникальному path."""
    result = await session.execute(select(TaskTag).where(TaskTag.path == path))
    tag = result.scalar_one_or_none()
    if tag is None:
        tag = TaskTag(
            code=code,
            path=path,
            name=name,
            subject=subject,
            exam_type=exam_type,
            parent_id=parent_id,
            depth=depth,
            sort_order=sort_order,
        )
        session.add(tag)
        await session.flush()
        logger.info("created tag %s (%s)", path, name)
    else:
        tag.name = name
        tag.parent_id = parent_id
        tag.depth = depth
        tag.sort_order = sort_order
    return tag


async def _walk(
    session: AsyncSession,
    node: dict,
    *,
    subject: Subject,
    exam_type: ExamType,
    parent_path: str | None,
    parent_id: int | None,
    depth: int,
    sort_order: int,
) -> None:
    code = node["code"]
    name = node["name"]
    path = f"{parent_path}.{code}" if parent_path else code

    # Уникальный per-subject/exam: префиксуем кодом предмета на верхнем уровне
    unique_code = f"{subject.value}.{exam_type.value}.{path}"

    tag = await _upsert_node(
        session,
        code=unique_code,
        path=path,
        name=name,
        subject=subject,
        exam_type=exam_type,
        parent_id=parent_id,
        depth=depth,
        sort_order=sort_order,
    )

    children = node.get("children", [])
    for i, child in enumerate(children):
        await _walk(
            session,
            child,
            subject=subject,
            exam_type=exam_type,
            parent_path=path,
            parent_id=tag.id,
            depth=depth + 1,
            sort_order=i,
        )


async def seed_from_file(session: AsyncSession, file_path: Path) -> None:
    raw = json.loads(file_path.read_text(encoding="utf-8"))  # noqa: ASYNC240 — разовый CLI-сидинг
    subject = Subject(raw["subject"])
    exam_type = ExamType(raw["examType"])
    tree = raw["tree"]

    logger.info("seeding %s / %s from %s", subject.value, exam_type.value, file_path.name)
    await _walk(
        session,
        tree,
        subject=subject,
        exam_type=exam_type,
        parent_path=None,
        parent_id=None,
        depth=0,
        sort_order=0,
    )


async def main(filenames: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if filenames:
        files = [TAGS_DIR / name for name in filenames]
    else:
        files = sorted(TAGS_DIR.glob("tags_*.json"))

    if not files:
        logger.warning("no tag files found in %s", TAGS_DIR)
        return

    async with SessionLocal() as session:
        for f in files:
            if not f.exists():
                logger.warning("skip missing %s", f)
                continue
            await seed_from_file(session, f)
        await session.commit()
    logger.info("seed complete")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:] or None))
