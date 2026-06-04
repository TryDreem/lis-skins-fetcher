from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.keyboards.main_menu import MY_SKINS_CALLBACK
from app.services.message_cleaner import MessageCleaner
from app.storage.sqlite_storage import SQLiteSkinStorage
from app.utils import format_price


router = Router(name="skins")


NO_SKINS_TEXT = """У тебя пока нет добавленных скинов.
Добавь первый через /add."""


@router.message(Command("skins"))
async def skins_command(
    message: Message,
    state: FSMContext,
    tracked_skin_storage: SQLiteSkinStorage,
    message_cleaner: MessageCleaner,
) -> None:
    await state.clear()
    await send_user_skins(
        message=message,
        telegram_user_id=message.from_user.id,
        tracked_skin_storage=tracked_skin_storage,
        message_cleaner=message_cleaner,
    )


@router.callback_query(F.data == MY_SKINS_CALLBACK)
async def skins_callback(
    callback: CallbackQuery,
    state: FSMContext,
    tracked_skin_storage: SQLiteSkinStorage,
    message_cleaner: MessageCleaner,
) -> None:
    await state.clear()
    await callback.answer()
    if callback.message:
        await send_user_skins(
            message=callback.message,
            telegram_user_id=callback.from_user.id,
            tracked_skin_storage=tracked_skin_storage,
            message_cleaner=message_cleaner,
            replace_current=True,
        )


async def send_user_skins(
    message: Message,
    telegram_user_id: int,
    tracked_skin_storage: SQLiteSkinStorage,
    message_cleaner: MessageCleaner,
    replace_current: bool = False,
) -> None:
    skins = await tracked_skin_storage.list_user_skins(telegram_user_id)
    if not skins:
        await _send_clean(message, NO_SKINS_TEXT, message_cleaner, replace_current)
        return

    parts = ["Твои скины:"]
    for skin in skins:
        parts.append(
            "\n"
            f"ID: {skin.id}\n"
            f"Name: {skin.skin_name}\n"
            f"Target price: {format_price(skin.target_price)}\n"
            f"Last found price: {format_price(skin.last_found_price)}\n"
            f"URL: {skin.url or 'N/A'}\n"
            f"Created at: {skin.created_at}"
        )

    await _send_clean(message, "\n".join(parts), message_cleaner, replace_current)


async def _send_clean(
    message: Message,
    text: str,
    message_cleaner: MessageCleaner,
    replace_current: bool,
) -> None:
    if replace_current:
        await message_cleaner.replace_message(message, text)
        return

    await message_cleaner.send_answer(message, text)
