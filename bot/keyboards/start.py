from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    WebAppInfo,
)

from bot import texts


def main_menu(mini_app_url: str | None = None) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if mini_app_url:
        rows.append([
            InlineKeyboardButton(
                text=texts.BTN_OPEN_MINIAPP,
                web_app=WebAppInfo(url=mini_app_url),
            )
        ])
    rows.append([InlineKeyboardButton(text=texts.BTN_BUILD_HOMEWORK, callback_data="hw:start")])
    rows.append([
        InlineKeyboardButton(text=texts.BTN_STUDENTS, callback_data="students:list"),
        InlineKeyboardButton(text=texts.BTN_BILLING, callback_data="billing:plans"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)
