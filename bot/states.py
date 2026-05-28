from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class HomeworkBuild(StatesGroup):
    """FSM сборки ДЗ — наполним в спринте 2."""

    choosing_subject = State()
    choosing_format = State()
    choosing_topics = State()
    confirming = State()
