from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[
            KeyboardButton(text="🏠 Старт"),
            KeyboardButton(text="➕ Добавить букет"),
        ]],
        resize_keyboard=True,
        persistent=True,
    )


def stores_keyboard(stores: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for store in stores:
        name = store["name"].replace("Магазин ", "").replace("магазин ", "").strip()
        kb.button(text=name, callback_data=f"store:{store['id']}")
    kb.adjust(1)
    return kb.as_markup()


def confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Опубликовать", callback_data="publish"),
                InlineKeyboardButton(text="Отмена", callback_data="cancel"),
            ]
        ]
    )
