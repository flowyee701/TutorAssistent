"""Middleware: на каждое обновление от пользователя — найти или создать User по telegram_id.

Также обрабатывает deep link /start ref_<id> → проставляет referred_by_id один раз.
В handler прокидывает уже привязанную к сессии User-модель через data['user'].
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject, Update
from sqlalchemy import select

from core.db.engine import SessionLocal
from core.db.models import Subscription, SubscriptionPlan, User

logger = logging.getLogger(__name__)

REFERRAL_PREFIX = "ref_"


def _extract_referral(event: TelegramObject) -> int | None:
    """Достаёт ID пригласившего из /start ref_<id>."""
    msg: Message | None = None
    if isinstance(event, Update) and event.message:
        msg = event.message
    elif isinstance(event, Message):
        msg = event
    if msg is None or not msg.text:
        return None
    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[0].startswith("/start"):
        return None
    payload = parts[1].strip()
    if not payload.startswith(REFERRAL_PREFIX):
        return None
    try:
        return int(payload[len(REFERRAL_PREFIX):])
    except ValueError:
        return None


class AuthMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user = data.get("event_from_user")
        if tg_user is None:
            return await handler(event, data)

        referral_id = _extract_referral(event)

        async with SessionLocal() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == tg_user.id)
            )
            user = result.scalar_one_or_none()

            if user is None:
                full_name = " ".join(
                    part for part in [tg_user.first_name, tg_user.last_name] if part
                )
                user = User(
                    telegram_id=tg_user.id,
                    username=tg_user.username,
                    full_name=full_name or None,
                )
                if referral_id and referral_id != tg_user.id:
                    inviter = await session.scalar(
                        select(User).where(User.id == referral_id)
                    )
                    if inviter:
                        user.referred_by_id = inviter.id
                session.add(user)
                await session.flush()

                # При создании пользователя сразу заводим FREE-подписку
                session.add(Subscription(user_id=user.id, plan=SubscriptionPlan.FREE))
                await session.commit()
                logger.info(
                    "registered user tg_id=%s id=%s (ref=%s)",
                    tg_user.id, user.id, user.referred_by_id,
                )
            else:
                # Обновим базовые поля, если изменились (юзернейм/имя)
                changed = False
                if user.username != tg_user.username:
                    user.username = tg_user.username
                    changed = True
                full_name = " ".join(
                    part for part in [tg_user.first_name, tg_user.last_name] if part
                ) or None
                if full_name and user.full_name != full_name:
                    user.full_name = full_name
                    changed = True
                if changed:
                    await session.commit()

            data["user"] = user
            data["db_session"] = session

            return await handler(event, data)
