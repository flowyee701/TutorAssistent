"""Юнит-тесты чистых функций парсера (без БД и сети)."""

from __future__ import annotations

from core.db.models import ExamType, Subject
from parser.fipi_parser import (
    ParsedTask,
    normalize,
    parse_answers_block,
    split_into_tasks,
)


def test_normalize_collapses_whitespace():
    assert normalize("  a\n\n b\t c ") == "a b c"


def test_split_into_tasks_basic():
    text = (
        "1. Решите уравнение x + 2 = 5 и запишите корень.\n"
        "2) Найдите площадь круга радиуса 2 в задаче.\n"
        "Задание 3. Вычислите производную функции f(x)=x^2.\n"
    )
    chunks = split_into_tasks(text)
    numbers = [n for n, _ in chunks]
    assert numbers == [1, 2, 3]


def test_split_ignores_too_short():
    # короткий хвост не должен стать задачей
    text = "1. Это полноценное условие задачи достаточной длины.\n2. ok\n"
    chunks = split_into_tasks(text)
    assert [n for n, _ in chunks] == [1]


def test_parse_answers_block():
    text = "1. cond one long enough text here\nОтветы\n1) 3\n2. -5\n"
    assert parse_answers_block(text) == {1: "3", 2: "-5"}


def test_content_hash_is_stable_and_dedupes():
    a = ParsedTask(
        statement_text="Решите   уравнение",
        statement_latex="...",
        source_label="T",
        subject=Subject.MATH_PROFILE,
        exam_type=ExamType.EGE,
        page_no=0,
    )
    b = ParsedTask(
        statement_text="Решите уравнение",  # отличается пробелами
        statement_latex="...",
        source_label="T",
        subject=Subject.MATH_PROFILE,
        exam_type=ExamType.EGE,
        page_no=1,
    )
    assert a.content_hash == b.content_hash
    assert len(a.content_hash) == 64
