from __future__ import annotations

import json
import sys
from io import BytesIO
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.fsm.state import State
from aiogram.fsm.storage.base import BaseStorage, StateType, StorageKey
from aiogram.fsm.storage.memory import SimpleEventIsolation
from aiogram.types import Update
from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files.uploadedfile import SimpleUploadedFile

from .models import StoreManager, TelegramBotSession
from .serializers import BotProductCreateSerializer, StoreManagerSerializer


def ensure_telegram_bot_path() -> Path:
    bot_root = Path(__file__).resolve().parent.parent.parent / 'telegram-bot'
    if not bot_root.exists():
        raise ImproperlyConfigured(f'Telegram bot directory was not found: {bot_root}')

    bot_root_str = str(bot_root)
    if bot_root_str not in sys.path:
        sys.path.insert(0, bot_root_str)

    return bot_root


class DjangoFSMStorage(BaseStorage):
    @staticmethod
    def _make_storage_key(key: StorageKey) -> str:
        parts = [
            str(key.bot_id),
            str(key.chat_id),
            str(key.user_id),
            str(key.thread_id or ''),
            str(key.business_connection_id or ''),
            key.destiny,
        ]
        return ':'.join(parts)

    @sync_to_async(thread_sensitive=True)
    def _write(self, key: StorageKey, state: str | None = None, data: dict | None = None) -> None:
        storage_key = self._make_storage_key(key)
        record = TelegramBotSession.objects.filter(storage_key=storage_key).first()

        if record is None and not (state or data):
            return

        if record is None:
            record = TelegramBotSession(storage_key=storage_key)

        record.bot_id = key.bot_id
        record.chat_id = key.chat_id
        record.user_id = key.user_id
        record.thread_id = key.thread_id
        record.business_connection_id = key.business_connection_id or ''
        record.destiny = key.destiny

        if state is not None:
            record.state = state or ''
        if data is not None:
            record.data = dict(data or {})

        if not record.state and not record.data:
            if record.pk:
                record.delete()
            return

        record.save()

    @sync_to_async(thread_sensitive=True)
    def _read(self, key: StorageKey) -> TelegramBotSession | None:
        storage_key = self._make_storage_key(key)
        return TelegramBotSession.objects.filter(storage_key=storage_key).first()

    async def set_state(self, key: StorageKey, state: StateType = None) -> None:
        state_value = state.state if isinstance(state, State) else state
        await self._write(key=key, state=state_value)

    async def get_state(self, key: StorageKey) -> str | None:
        record = await self._read(key)
        return record.state or None if record else None

    async def set_data(self, key: StorageKey, data: dict) -> None:
        await self._write(key=key, data=data)

    async def get_data(self, key: StorageKey) -> dict:
        record = await self._read(key)
        return dict(record.data or {}) if record else {}

    async def close(self) -> None:
        return None


class DjangoBotApiClient:
    async def auth_manager(self, telegram_id: int) -> dict | None:
        return await self._auth_manager(telegram_id)

    @sync_to_async(thread_sensitive=True)
    def _auth_manager(self, telegram_id: int) -> dict | None:
        manager = StoreManager.objects.filter(telegram_id=telegram_id, is_active=True).first()
        if not manager:
            return None
        return StoreManagerSerializer(manager).data

    async def create_product(
        self,
        bot: Bot,
        telegram_id: int,
        store_id: int,
        photo_file_id: str,
        price: str,
        title: str,
    ) -> tuple[bool, str]:
        try:
            file_meta = await bot.get_file(photo_file_id)
            file_bytes = BytesIO()
            await bot.download_file(file_meta.file_path, destination=file_bytes)
            return await self._create_product_sync(
                telegram_id=telegram_id,
                store_id=store_id,
                image_bytes=file_bytes.getvalue(),
                price=price,
                title=title,
            )
        except Exception as exc:
            return False, str(exc)

    @sync_to_async(thread_sensitive=True)
    def _create_product_sync(
        self,
        telegram_id: int,
        store_id: int,
        image_bytes: bytes,
        price: str,
        title: str,
    ) -> tuple[bool, str]:
        uploaded_image = SimpleUploadedFile(
            'bouquet.jpg',
            image_bytes,
            content_type='image/jpeg',
        )
        serializer = BotProductCreateSerializer(
            data={
                'telegram_id': telegram_id,
                'store_id': store_id,
                'uploaded_image': uploaded_image,
                'price': price,
                'title': title,
            }
        )
        if not serializer.is_valid():
            return False, json.dumps(serializer.errors, ensure_ascii=False)

        instance = serializer.save()
        update_fields: list[str] = []

        if instance.uploaded_image:
            instance.image = instance.uploaded_image.url
            update_fields.append('image')

        if not instance.article:
            first_store = instance.stores.order_by('id').first()
            store_slug = first_store.subdomain if first_store else 'main'
            instance.article = f'{store_slug}-{instance.id}'[:64]
            update_fields.append('article')

        if update_fields:
            instance.save(update_fields=update_fields)

        return True, 'ok'


_dispatcher: Dispatcher | None = None


def get_dispatcher() -> Dispatcher:
    global _dispatcher
    if _dispatcher is not None:
        return _dispatcher

    ensure_telegram_bot_path()
    from bot import main as bot_main

    bot_main.api_client = DjangoBotApiClient()

    dispatcher = Dispatcher(
        storage=DjangoFSMStorage(),
        events_isolation=SimpleEventIsolation(),
    )
    dispatcher.include_router(bot_main.router)
    _dispatcher = dispatcher
    return dispatcher


async def process_telegram_update(update_data: dict) -> None:
    bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '').strip()
    if not bot_token:
        raise ImproperlyConfigured('BOT_TOKEN is not configured for Telegram webhook mode.')

    bot = Bot(token=bot_token)
    try:
        dispatcher = get_dispatcher()
        update = Update.model_validate(update_data, context={'bot': bot})
        await dispatcher.feed_update(bot, update)
    finally:
        await bot.session.close()

