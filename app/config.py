import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    bot_token: str
    database_path: str
    check_interval_seconds: int
    lis_skins_timeout_seconds: int
    log_level: str


def _read_int_env(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    try:
        value = int(raw_value)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc

    if value <= 0:
        raise RuntimeError(f"{name} must be greater than 0")

    return value


def load_settings() -> Settings:
    load_dotenv()

    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        raise RuntimeError("BOT_TOKEN is not set. Create .env from .env.example")

    return Settings(
        bot_token=bot_token,
        database_path=os.getenv("DATABASE_PATH", "data/skins.db"),
        check_interval_seconds=_read_int_env("CHECK_INTERVAL_SECONDS", 900),
        lis_skins_timeout_seconds=_read_int_env("LIS_SKINS_TIMEOUT_SECONDS", 30),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )
