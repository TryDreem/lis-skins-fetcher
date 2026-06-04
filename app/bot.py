import asyncio
import logging
from contextlib import suppress

import aiohttp
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.bot_commands import setup_bot_commands
from app.config import load_settings
from app.handlers import routers
from app.logging_config import setup_logging
from app.middlewares import UserTrackerMiddleware
from app.scheduler.price_checker import PriceChecker
from app.services.lis_skins import LisSkinsClient
from app.services.message_cleaner import MessageCleaner
from app.storage.sqlite_storage import SQLiteSkinStorage


logger = logging.getLogger(__name__)


async def run_bot() -> None:
    settings = load_settings()
    setup_logging(settings.log_level)

    storage = SQLiteSkinStorage(settings.database_path)
    await storage.init()

    bot = Bot(token=settings.bot_token)
    message_cleaner = MessageCleaner(bot)
    dp = Dispatcher(storage=MemoryStorage())

    timeout = aiohttp.ClientTimeout(total=settings.lis_skins_timeout_seconds)
    async with aiohttp.ClientSession(timeout=timeout) as http_session:
        lis_skins_client = LisSkinsClient(http_session)

        dp["tracked_skin_storage"] = storage
        dp["lis_skins_client"] = lis_skins_client
        dp["message_cleaner"] = message_cleaner

        user_tracker_middleware = UserTrackerMiddleware()
        dp.message.middleware(user_tracker_middleware)
        dp.callback_query.middleware(user_tracker_middleware)

        for router in routers:
            dp.include_router(router)

        price_checker = PriceChecker(
            storage=storage,
            lis_skins_client=lis_skins_client,
            message_cleaner=message_cleaner,
            interval_seconds=settings.check_interval_seconds,
        )
        scheduler_task = asyncio.create_task(price_checker.run(), name="price-checker")

        try:
            await setup_bot_commands(bot)
            logger.info("Starting bot polling")
            await dp.start_polling(bot, close_bot_session=False)
        finally:
            scheduler_task.cancel()
            with suppress(asyncio.CancelledError):
                await scheduler_task

            await bot.session.close()
            await storage.close()
            logger.info("Bot stopped")
