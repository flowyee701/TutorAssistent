"""Автотегирование задач через YandexGPT Lite (см. files/prompts.md §2).

Берёт задачи без тегов, батчами по 10–20 шлёт в LLM, проставляет TaskTagLink,
обновляет difficulty/task_number. confidence == "low" → тег `unclassified`.
Каждый вызов логируется в LlmCallLog.
"""

from __future__ import annotations

import json
import logging
import time

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.models import ExamType, Subject, Task, TaskTag, TaskTagLink
from core.schemas.llm import TagResultBatchItem
from core.services.llm import LlmResponse, _strip_md, get_provider, log_llm_call

logger = logging.getLogger(__name__)

UNCLASSIFIED_PATH = "unclassified"

BATCH_SYSTEM = """Ты — эксперт по школьной математике (физике, информатике). \
Для каждой задачи из списка определи, к каким темам она относится.

Верни ТОЛЬКО JSON-массив без markdown, без пояснений. Каждый элемент:
- index: номер задачи из входного списка (целое)
- primary_tags: массив path (1-3 тега, точно относящиеся)
- secondary_tags: массив path (0-2 дополнительных)
- difficulty: 1-5 (оценка сложности)
- task_number: предполагаемый № задания ЕГЭ или null
- confidence: "high" | "medium" | "low"

Правила:
1. Не более 3 primary-тегов на задачу.
2. Теги бери ТОЛЬКО из предоставленного списка. Если ничего не подходит — \
primary_tags: [], confidence: "low".
3. Никаких новых тегов не придумывай.
4. Верни ровно столько элементов массива, сколько задач во входе."""


async def load_tag_index(
    session: AsyncSession, subject: Subject, exam: ExamType
) -> tuple[dict[str, TaskTag], TaskTag | None, list[dict]]:
    """Возвращает (path→tag, unclassified-tag, минимальный список для промпта)."""
    rows = (
        await session.scalars(
            select(TaskTag).where(TaskTag.subject == subject, TaskTag.exam_type == exam)
        )
    ).all()
    by_path = {t.path: t for t in rows}
    unclassified = by_path.get(UNCLASSIFIED_PATH)
    tags_min = [
        {"path": t.path, "name": t.name}
        for t in rows
        if t.path != UNCLASSIFIED_PATH
    ]
    return by_path, unclassified, tags_min


async def fetch_untagged(
    session: AsyncSession, subject: Subject, exam: ExamType, limit: int
) -> list[Task]:
    """Задачи без единого TaskTagLink."""
    has_link = select(TaskTagLink.id).where(TaskTagLink.task_id == Task.id).exists()
    stmt = (
        select(Task)
        .where(
            Task.subject == subject,
            Task.exam_type == exam,
            Task.deleted_at.is_(None),
            ~has_link,
        )
        .order_by(Task.id)
        .limit(limit)
    )
    return list((await session.scalars(stmt)).all())


def build_user_prompt(tasks: list[Task], tags_min: list[dict]) -> str:
    lines = [f"Список тегов:\n{json.dumps(tags_min, ensure_ascii=False)}", "", "Задачи:"]
    for i, t in enumerate(tasks):
        statement = t.statement_latex[:800]
        lines.append(f"[{i}] {statement}")
        if t.answer:
            lines.append(f"Ответ: {t.answer[:120]}")
    return "\n".join(lines)


def _parse_batch(raw: str, expected: int) -> list[TagResultBatchItem]:
    data = json.loads(_strip_md(raw))
    if isinstance(data, dict) and "items" in data:
        data = data["items"]
    if not isinstance(data, list):
        raise ValueError("ожидался JSON-массив")
    out: list[TagResultBatchItem] = []
    for i, row in enumerate(data):
        if "index" not in row:
            row["index"] = i
        out.append(TagResultBatchItem.model_validate(row))
    return out


async def _apply_result(
    session: AsyncSession,
    task: Task,
    result: TagResultBatchItem,
    by_path: dict[str, TaskTag],
    unclassified: TaskTag | None,
) -> None:
    paths = list(dict.fromkeys([*result.primary_tags, *result.secondary_tags]))
    resolved = [by_path[p] for p in paths if p in by_path]

    if (result.confidence == "low" or not resolved) and unclassified:
        resolved = [unclassified]

    for tag in resolved:
        session.add(TaskTagLink(task_id=task.id, tag_id=tag.id))

    if result.difficulty and 1 <= result.difficulty <= 5:
        task.difficulty = result.difficulty
    if result.task_number and task.task_number is None:
        task.task_number = result.task_number


async def tag_tasks(
    session: AsyncSession,
    subject: Subject,
    exam: ExamType,
    *,
    batch_size: int = 15,
    max_batches: int | None = None,
) -> dict[str, int]:
    """Тегирует все задачи без тегов. Возвращает статистику."""
    by_path, unclassified, tags_min = await load_tag_index(session, subject, exam)
    if not by_path:
        logger.error("нет тегов для %s/%s — сначала запусти seed", subject.value, exam.value)
        return {"tagged": 0, "batches": 0, "errors": 0}

    provider = get_provider()
    stats = {"tagged": 0, "batches": 0, "errors": 0, "unclassified": 0}

    while max_batches is None or stats["batches"] < max_batches:
        tasks = await fetch_untagged(session, subject, exam, batch_size)
        if not tasks:
            break

        user = build_user_prompt(tasks, tags_min)
        t0 = time.monotonic()
        response: LlmResponse | None = None
        success = False
        try:
            response = await provider.complete(
                BATCH_SYSTEM, user, temperature=0.2, max_tokens=min(2000, 130 * len(tasks))
            )
            results = _parse_batch(response.text, len(tasks))
            by_index = {r.index: r for r in results}
            for i, task in enumerate(tasks):
                res = by_index.get(i)
                if res is None:
                    if unclassified:
                        session.add(TaskTagLink(task_id=task.id, tag_id=unclassified.id))
                        stats["unclassified"] += 1
                    continue
                await _apply_result(session, task, res, by_path, unclassified)
                if res.confidence == "low" or not res.primary_tags:
                    stats["unclassified"] += 1
                stats["tagged"] += 1
            await session.commit()
            success = True
        except Exception:  # noqa: BLE001
            await session.rollback()
            stats["errors"] += 1
            logger.exception("батч %d упал", stats["batches"])
            # Чтобы не зациклиться на «ядовитом» батче — помечаем unclassified
            if unclassified:
                for task in tasks:
                    session.add(TaskTagLink(task_id=task.id, tag_id=unclassified.id))
                    stats["unclassified"] += 1
                await session.commit()
        finally:
            latency_ms = int((time.monotonic() - t0) * 1000)
            await log_llm_call(
                purpose="tag_task",
                response=response,
                latency_ms=latency_ms,
                success=success,
            )

        stats["batches"] += 1
        logger.info(
            "батч %d: всего тегировано %d (unclassified %d, ошибок %d)",
            stats["batches"], stats["tagged"], stats["unclassified"], stats["errors"],
        )

    return stats


async def tagging_coverage(session: AsyncSession, subject: Subject, exam: ExamType) -> dict:
    """Доля задач с «настоящими» тегами (не unclassified) — для критерия готовности."""
    total = await session.scalar(
        select(func.count(Task.id)).where(
            Task.subject == subject, Task.exam_type == exam, Task.deleted_at.is_(None)
        )
    )
    unclassified = await session.scalar(
        select(TaskTag.id).where(
            TaskTag.subject == subject,
            TaskTag.exam_type == exam,
            TaskTag.path == UNCLASSIFIED_PATH,
        )
    )
    classified = 0
    if total and unclassified:
        # задачи, у которых есть хотя бы один тег, отличный от unclassified
        good = select(func.count(func.distinct(TaskTagLink.task_id))).where(
            TaskTagLink.tag_id != unclassified,
            TaskTagLink.task_id.in_(
                select(Task.id).where(Task.subject == subject, Task.exam_type == exam)
            ),
        )
        classified = await session.scalar(good) or 0
    pct = round(classified / total * 100, 1) if total else 0.0
    return {"total": total or 0, "classified": classified, "pct_classified": pct}
