from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def stores_keyboard(stores: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for store in stores:
        kb.button(text=store["name"], callback_data=f"store:{store['id']}")
    kb.adjust(2)
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
