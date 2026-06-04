import logging
from typing import Any

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import Message


logger = logging.getLogger(__name__)


class MessageCleaner:
    def __init__(self, bot: Bot) -> None:
        self._bot = bot
        self._last_bot_message_by_chat: dict[int, int] = {}

    async def send_message(
        self,
        chat_id: int,
        text: str,
        reply_markup: Any | None = None,
        **kwargs: Any,
    ) -> Message:
        await self.delete_last_bot_message(chat_id)
        sent_message = await self._bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=reply_markup,
            **kwargs,
        )
        self._last_bot_message_by_chat[chat_id] = sent_message.message_id
        return sent_message

    async def send_persistent_message(
        self,
        chat_id: int,
        text: str,
        reply_markup: Any | None = None,
        **kwargs: Any,
    ) -> Message:
        return await self._bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=reply_markup,
            **kwargs,
        )

    async def send_answer(
        self,
        message: Message,
        text: str,
        reply_markup: Any | None = None,
        delete_incoming: bool = True,
        **kwargs: Any,
    ) -> Message:
        if delete_incoming:
            await self.delete_message(message)

        return await self.send_message(
            chat_id=message.chat.id,
            text=text,
            reply_markup=reply_markup,
            **kwargs,
        )

    async def replace_message(
        self,
        message: Message,
        text: str,
        reply_markup: Any | None = None,
        **kwargs: Any,
    ) -> Message:
        try:
            edited_message = await message.edit_text(
                text=text,
                reply_markup=reply_markup,
                **kwargs,
            )
            if isinstance(edited_message, Message):
                self._last_bot_message_by_chat[message.chat.id] = edited_message.message_id
                return edited_message

            self._last_bot_message_by_chat[message.chat.id] = message.message_id
            return message
        except TelegramAPIError:
            logger.debug(
                "Could not edit message chat_id=%s message_id=%s; falling back to delete/send",
                message.chat.id,
                message.message_id,
                exc_info=True,
            )

        self.forget_message(message.chat.id, message.message_id)
        await self.delete_message(message)
        return await self.send_message(
            chat_id=message.chat.id,
            text=text,
            reply_markup=reply_markup,
            **kwargs,
        )

    async def delete_last_bot_message(self, chat_id: int) -> None:
        message_id = self._last_bot_message_by_chat.pop(chat_id, None)
        if message_id is None:
            return

        try:
            await self._bot.delete_message(chat_id=chat_id, message_id=message_id)
        except TelegramAPIError:
            logger.debug(
                "Could not delete previous bot message chat_id=%s message_id=%s",
                chat_id,
                message_id,
                exc_info=True,
            )

    async def delete_message(self, message: Message) -> None:
        try:
            await message.delete()
        except TelegramAPIError:
            logger.debug(
                "Could not delete incoming message chat_id=%s message_id=%s",
                message.chat.id,
                message.message_id,
                exc_info=True,
            )

    def forget_message(self, chat_id: int, message_id: int) -> None:
        if self._last_bot_message_by_chat.get(chat_id) == message_id:
            self._last_bot_message_by_chat.pop(chat_id, None)
