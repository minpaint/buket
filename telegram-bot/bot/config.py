import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    bot_token: str
    django_api_url: str
    bot_secret: str


def get_settings() -> Settings:
    load_dotenv()
    return Settings(
        bot_token=os.getenv("BOT_TOKEN", "").strip(),
        django_api_url=os.getenv("DJANGO_API_URL", "http://127.0.0.1:3002").rstrip("/"),
        bot_secret=os.getenv("BOT_SECRET", "").strip(),
    )
