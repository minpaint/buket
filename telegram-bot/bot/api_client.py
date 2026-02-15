from __future__ import annotations

from io import BytesIO
from typing import Any

import aiohttp
from aiogram import Bot


class ApiClient:
    def __init__(self, base_url: str, bot_secret: str):
        self.base_url = base_url.rstrip("/")
        self.bot_secret = bot_secret

    @property
    def _headers(self) -> dict[str, str]:
        return {"X-Bot-Token": self.bot_secret}

    async def auth_manager(self, telegram_id: int) -> dict[str, Any] | None:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/api/v1/auth/bot-token/",
                headers=self._headers,
                json={"telegram_id": telegram_id},
            ) as response:
                if response.status == 200:
                    return await response.json()
                return None

    async def create_product(
        self,
        bot: Bot,
        telegram_id: int,
        store_id: int,
        photo_file_id: str,
        price: str,
        title: str,
    ) -> tuple[bool, str]:
        file_meta = await bot.get_file(photo_file_id)
        file_bytes = BytesIO()
        await bot.download_file(file_meta.file_path, destination=file_bytes)
        file_bytes.seek(0)

        form = aiohttp.FormData()
        form.add_field("telegram_id", str(telegram_id))
        form.add_field("store_id", str(store_id))
        form.add_field("price", price)
        form.add_field("title", title)
        form.add_field("uploaded_image", file_bytes, filename="bouquet.jpg", content_type="image/jpeg")

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/api/v1/products/from-bot/",
                data=form,
                headers=self._headers,
            ) as response:
                if response.status in (200, 201):
                    return True, "ok"
                text = await response.text()
                return False, text
