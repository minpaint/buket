from __future__ import annotations

import asyncio
from decimal import Decimal, InvalidOperation

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import BotCommand, CallbackQuery, Message

from .api_client import ApiClient
from .config import get_settings
from .keyboards import confirm_keyboard, main_keyboard, stores_keyboard
from .states import ProductForm

router = Router()
settings = get_settings()
api_client = ApiClient(settings.django_api_url, settings.bot_secret)
BOT_COMMANDS = [
    BotCommand(command="start", description="Запустить бота"),
    BotCommand(command="add", description="Добавить букет в витрину"),
    BotCommand(command="cancel", description="Отменить действие"),
]


def parse_price(raw: str) -> str | None:
    try:
        value = Decimal(raw.replace(",", "."))
        if value <= 0 or value > 999999:
            return None
        return f"{value:.2f}"
    except (InvalidOperation, ValueError):
        return None


@router.message(Command("start"))
async def start_handler(message: Message):
    manager = await api_client.auth_manager(message.from_user.id)
    if not manager:
        await message.answer("Нет доступа. Обратитесь к администратору.")
        return
    await message.answer(
        "Доступ подтверждён. Нажмите кнопку ниже, чтобы добавить букет.",
        reply_markup=main_keyboard(),
    )


@router.message(F.text == "🏠 Старт")
async def btn_start_handler(message: Message):
    await start_handler(message)


@router.message(F.text == "➕ Добавить букет")
async def btn_add_handler(message: Message, state: FSMContext):
    await add_handler(message, state)


@router.message(Command("add"))
async def add_handler(message: Message, state: FSMContext):
    manager = await api_client.auth_manager(message.from_user.id)
    if not manager:
        await message.answer("Нет доступа.")
        return

    stores = manager.get("stores", [])
    if not stores:
        await message.answer("Для вас не назначены магазины.")
        return

    await state.clear()
    await state.update_data(stores=stores)
    await state.set_state(ProductForm.choosing_store)
    await message.answer("Выберите магазин:", reply_markup=stores_keyboard(stores))


@router.callback_query(ProductForm.choosing_store, F.data.startswith("store:"))
async def choose_store_handler(callback: CallbackQuery, state: FSMContext):
    store_id = int(callback.data.split(":")[1])
    data = await state.get_data()
    selected = next((s for s in data.get("stores", []) if s["id"] == store_id), None)
    if not selected:
        await callback.message.answer("Магазин не найден.")
        await callback.answer()
        return

    await state.update_data(store_id=selected["id"], store_name=selected["name"])
    await state.set_state(ProductForm.waiting_photo)
    await callback.message.answer(f"Магазин: {selected['name']}\nОтправьте фото букета.")
    await callback.answer()


@router.message(ProductForm.waiting_photo, F.photo)
async def photo_handler(message: Message, state: FSMContext):
    photo = message.photo[-1]
    await state.update_data(photo_file_id=photo.file_id)
    await state.set_state(ProductForm.waiting_price)
    await message.answer("Введите цену (например 45.50)")


@router.message(ProductForm.waiting_price, F.text)
async def price_handler(message: Message, state: FSMContext):
    price = parse_price(message.text.strip())
    if not price:
        await message.answer("Некорректная цена. Пример: 45.50")
        return
    await state.update_data(price=price)
    await state.set_state(ProductForm.waiting_title)
    await message.answer("Введите название букета или /skip")


@router.message(ProductForm.waiting_title, Command("skip"))
async def skip_title_handler(message: Message, state: FSMContext):
    await state.update_data(title="Букет")
    await state.set_state(ProductForm.confirmation)
    data = await state.get_data()
    await message.answer(
        f"Проверьте данные:\nМагазин: {data['store_name']}\nЦена: {data['price']} BYN\nНазвание: Букет",
        reply_markup=confirm_keyboard(),
    )


@router.message(ProductForm.waiting_title, F.text)
async def title_handler(message: Message, state: FSMContext):
    title = message.text.strip() or "Букет"
    await state.update_data(title=title)
    await state.set_state(ProductForm.confirmation)
    data = await state.get_data()
    await message.answer(
        f"Проверьте данные:\nМагазин: {data['store_name']}\nЦена: {data['price']} BYN\nНазвание: {title}",
        reply_markup=confirm_keyboard(),
    )


@router.callback_query(ProductForm.confirmation, F.data == "cancel")
async def cancel_handler(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("Отменено.")
    await callback.answer()


@router.callback_query(ProductForm.confirmation, F.data == "publish")
async def publish_handler(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    ok, error = await api_client.create_product(
        bot=bot,
        telegram_id=callback.from_user.id,
        store_id=data["store_id"],
        photo_file_id=data["photo_file_id"],
        price=data["price"],
        title=data.get("title", "Букет"),
    )
    await state.clear()
    if ok:
        await callback.message.answer("Опубликовано в онлайн витрине.")
    else:
        short_error = error[:200] if error else "неизвестная ошибка"
        await callback.message.answer(f"Ошибка публикации: {short_error}")
    await callback.answer()


@router.message(Command("cancel"))
async def cancel_command_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Действие отменено.")


async def main():
    if not settings.bot_token or not settings.bot_secret:
        raise RuntimeError("BOT_TOKEN и BOT_SECRET обязательны.")
    bot = Bot(token=settings.bot_token)
    await bot.set_my_commands(BOT_COMMANDS)
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
