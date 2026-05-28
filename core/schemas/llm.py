"""Pydantic-схемы для структурированных ответов LLM."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SearchParams(BaseModel):
    """Результат parse_query — параметры поиска по банку задач (prompts.md §1)."""

    subject: str | None = None
    exam_type: str | None = None
    topics: list[str] = Field(default_factory=list)
    difficulty_min: int | None = None
    difficulty_max: int | None = None
    count: int | None = None
    format: str | None = None
    error: str | None = None


class TagResult(BaseModel):
    """Результат тегирования одной задачи (prompts.md §2)."""

    primary_tags: list[str] = Field(default_factory=list)
    secondary_tags: list[str] = Field(default_factory=list)
    difficulty: int | None = None
    task_number: int | None = None
    confidence: str = "low"  # high | medium | low


class TagResultBatchItem(TagResult):
    """Элемент батч-ответа: добавляем индекс задачи в батче."""

    index: int
