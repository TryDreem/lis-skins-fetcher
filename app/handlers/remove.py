import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.keyboards.main_menu import REMOVE_SKIN_CALLBACK
from app.services.message_cleaner import MessageCleaner
from app.storage.sqlite_storage import SQLiteSkinStorage
from app.utils import format_price


logger = logging.getLogger(__name__)
router = Router(name="remove")


class RemoveSkin(StatesGroup):
    waiting_skin_id = State()


NO_SKINS_TEXT = """У тебя пока нет добавленных скинов.
Добавь первый через /add."""

REMOVE_PROMPT = "Напиши ID скина, который хочешь удалить."
SKIN_NOT_FOUND_TEXT = "Скин с таким ID не найден среди твоих скинов."


@router.message(Command("remove"))
async def remove_command(
    message: Message,
    state: FSMContext,
    tracked_skin_storage: SQLiteSkinStorage,
    message_cleaner: MessageCleaner,
) -> None:
    await start_remove_flow(
        message=message,
        telegram_user_id=message.from_user.id,
        state=state,
        tracked_skin_storage=tracked_skin_storage,
        message_cleaner=message_cleaner,
    )


@router.callback_query(F.data == REMOVE_SKIN_CALLBACK)
async def remove_callback(
    callback: CallbackQuery,
    state: FSMContext,
    tracked_skin_storage: SQLiteSkinStorage,
    message_cleaner: MessageCleaner,
) -> None:
    await callback.answer()
    if callback.message:
        await start_remove_flow(
            message=callback.message,
            telegram_user_id=callback.from_user.id,
            state=state,
            tracked_skin_storage=tracked_skin_storage,
            message_cleaner=message_cleaner,
            replace_current=True,
        )


async def start_remove_flow(
    message: Message,
    telegram_user_id: int,
    state: FSMContext,
    tracked_skin_storage: SQLiteSkinStorage,
    message_cleaner: MessageCleaner,
    replace_current: bool = False,
) -> None:
    await state.clear()
    skins = await tracked_skin_storage.list_user_skins(telegram_user_id)

    if not skins:
        await _send_clean(message, NO_SKINS_TEXT, message_cleaner, replace_current)
        return

    parts = ["Твои скины:"]
    for skin in skins:
        parts.append(
            f"ID: {skin.id} — {skin.skin_name}, target: {format_price(skin.target_price)}"
        )

    await state.set_state(RemoveSkin.waiting_skin_id)
    await _send_clean(
        message,
        "\n".join(parts) + f"\n\n{REMOVE_PROMPT}",
        message_cleaner,
        replace_current,
    )


@router.message(RemoveSkin.waiting_skin_id, F.text, ~F.text.startswith("/"))
async def process_remove_id(
    message: Message,
    state: FSMContext,
    tracked_skin_storage: SQLiteSkinStorage,
    message_cleaner: MessageCleaner,
) -> None:
    raw_skin_id = (message.text or "").strip()
    try:
        skin_id = int(raw_skin_id)
    except ValueError:
        logger.info("Invalid remove id from user %s: %r", message.from_user.id, raw_skin_id)
        await message_cleaner.send_answer(message, SKIN_NOT_FOUND_TEXT)
        return

    deleted = await tracked_skin_storage.delete_user_skin(
        telegram_user_id=message.from_user.id,
        skin_id=skin_id,
    )
    if not deleted:
        logger.info("User %s tried to delete unavailable skin id %s", message.from_user.id, skin_id)
        await message_cleaner.send_answer(message, SKIN_NOT_FOUND_TEXT)
        return

    await state.clear()
    await message_cleaner.send_answer(
        message,
        "Скин удалён. Уведомления по нему больше приходить не будут.",
    )


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
