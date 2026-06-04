from aiogram import Bot
from aiogram.types import BotCommand


async def setup_bot_commands(bot: Bot) -> None:
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Главное меню"),
            BotCommand(command="add", description="Добавить скин"),
            BotCommand(command="skins", description="Мои скины"),
            BotCommand(command="edit", description="Изменить target price"),
            BotCommand(command="remove", description="Удалить скин по ID"),
            BotCommand(command="masterdelete", description="Удалить все мои скины"),
            BotCommand(command="time", description="Частота уведомлений"),
            BotCommand(command="foraristarkh", description="For Aristarkh"),
            BotCommand(command="docs", description="Как работает бот"),
        ]
    )
