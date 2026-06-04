import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User

from app.storage.sqlite_storage import SQLiteSkinStorage


logger = logging.getLogger(__name__)


class UserTrackerMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        storage = data.get("tracked_skin_storage")

        if isinstance(user, User) and isinstance(storage, SQLiteSkinStorage):
            is_new_user = await storage.ensure_user(user.id)
            if is_new_user:
                logger.info(
                    "New Telegram user: id=%s username=%s",
                    user.id,
                    user.username,
                )

        return await handler(event, data)
