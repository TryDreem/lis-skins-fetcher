import time

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.keyboards import main_menu_keyboard
from app.services.message_cleaner import MessageCleaner


router = Router(name="start")
START_DEBOUNCE_SECONDS = 2.0
_last_start_by_chat_user: dict[tuple[int, int], float] = {}


START_TEXT = (
    "Привет! Я умею отслеживать цены на CS2-скины с LIS-SKINS и присылать "
    "уведомления, когда цена станет подходящей."
)


@router.message(CommandStart())
async def start_command(
    message: Message,
    state: FSMContext,
    message_cleaner: MessageCleaner,
) -> None:
    key = (message.chat.id, message.from_user.id)
    now = time.monotonic()
    last_start_at = _last_start_by_chat_user.get(key)
    if last_start_at is not None and now - last_start_at < START_DEBOUNCE_SECONDS:
        await message_cleaner.delete_message(message)
        return

    _last_start_by_chat_user[key] = now
    await state.clear()
    await message_cleaner.send_answer(
        message,
        START_TEXT,
        reply_markup=main_menu_keyboard(),
        delete_incoming=False,
    )
