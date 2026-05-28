from __future__ import annotations

import logging

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from bot import texts
from bot.keyboards.start import main_menu
from core.config import settings
from core.db.models import User

router = Router(name="start")
logger = logging.getLogger(__name__)


@router.message(CommandStart())
async def handle_start(message: Message, user: User) -> None:
    greeting = texts.START_GREETING.format(
        name=user.full_name or user.username or "репетитор"
    )
    if user.referred_by_id:
        greeting = f"{greeting}\n\n{texts.START_REFERRAL_BONUS}"
    await message.answer(
        greeting,
        reply_markup=main_menu(settings.mini_app_url or None),
    )


@router.message(Command("help"))
async def handle_help(message: Message) -> None:
    await message.answer(texts.HELP)
