import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.keyboards.main_menu import EDIT_SKIN_CALLBACK
from app.services.message_cleaner import MessageCleaner
from app.storage.models import TrackedSkin
from app.storage.sqlite_storage import SQLiteSkinStorage
from app.utils import format_price, parse_price


logger = logging.getLogger(__name__)
router = Router(name="edit")


class EditSkin(StatesGroup):
    waiting_skin_id = State()
    waiting_target_price = State()


NO_SKINS_TEXT = """У тебя пока нет добавленных скинов.
Добавь первый через /add."""

EDIT_ID_PROMPT = "Напиши ID скина, у которого хочешь изменить target price."
EDIT_PRICE_PROMPT = """Напиши новую цену в долларах.
Например: 750"""
SKIN_NOT_FOUND_TEXT = "Скин с таким ID не найден среди твоих скинов."


@router.message(Command("edit"))
async def edit_command(
    message: Message,
    state: FSMContext,
    tracked_skin_storage: SQLiteSkinStorage,
    message_cleaner: MessageCleaner,
) -> None:
    await start_edit_flow(
        message=message,
        telegram_user_id=message.from_user.id,
        state=state,
        tracked_skin_storage=tracked_skin_storage,
        message_cleaner=message_cleaner,
    )


@router.callback_query(F.data == EDIT_SKIN_CALLBACK)
async def edit_callback(
    callback: CallbackQuery,
    state: FSMContext,
    tracked_skin_storage: SQLiteSkinStorage,
    message_cleaner: MessageCleaner,
) -> None:
    await callback.answer()
    if callback.message:
        await start_edit_flow(
            message=callback.message,
            telegram_user_id=callback.from_user.id,
            state=state,
            tracked_skin_storage=tracked_skin_storage,
            message_cleaner=message_cleaner,
            replace_current=True,
        )


async def start_edit_flow(
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

    await state.update_data(user_skin_ids=[skin.id for skin in skins])
    await state.set_state(EditSkin.waiting_skin_id)
    await _send_clean(
        message,
        _format_edit_skin_list(skins) + f"\n\n{EDIT_ID_PROMPT}",
        message_cleaner,
        replace_current,
    )


@router.message(EditSkin.waiting_skin_id, F.text, ~F.text.startswith("/"))
async def process_edit_id(
    message: Message,
    state: FSMContext,
    message_cleaner: MessageCleaner,
) -> None:
    raw_skin_id = (message.text or "").strip()
    try:
        skin_id = int(raw_skin_id)
    except ValueError:
        logger.info("Invalid edit id from user %s: %r", message.from_user.id, raw_skin_id)
        await message_cleaner.send_answer(message, SKIN_NOT_FOUND_TEXT)
        return

    data = await state.get_data()
    user_skin_ids = data.get("user_skin_ids")
    if not isinstance(user_skin_ids, list) or skin_id not in user_skin_ids:
        logger.info("User %s tried to edit unavailable skin id %s", message.from_user.id, skin_id)
        await message_cleaner.send_answer(message, SKIN_NOT_FOUND_TEXT)
        return

    await state.update_data(edit_skin_id=skin_id)
    await state.set_state(EditSkin.waiting_target_price)
    await message_cleaner.send_answer(message, EDIT_PRICE_PROMPT)


@router.message(EditSkin.waiting_target_price, F.text, ~F.text.startswith("/"))
async def process_edit_target_price(
    message: Message,
    state: FSMContext,
    tracked_skin_storage: SQLiteSkinStorage,
    message_cleaner: MessageCleaner,
) -> None:
    raw_price = (message.text or "").strip()
    try:
        target_price = parse_price(raw_price)
    except ValueError:
        logger.info("Invalid edit target price from user %s: %r", message.from_user.id, raw_price)
        await message_cleaner.send_answer(
            message,
            "Неправильный формат цены. Напиши число в долларах, например: 750",
        )
        return

    data = await state.get_data()
    skin_id = data.get("edit_skin_id")
    if not isinstance(skin_id, int):
        logger.error("Edit FSM data lost for user %s", message.from_user.id)
        await message_cleaner.send_answer(
            message,
            "Не удалось изменить цену. Попробуй заново через /edit.",
        )
        await state.clear()
        return

    updated = await tracked_skin_storage.update_user_skin_target_price(
        telegram_user_id=message.from_user.id,
        skin_id=skin_id,
        target_price=target_price,
    )
    if not updated:
        logger.info("User %s tried to update unavailable skin id %s", message.from_user.id, skin_id)
        await message_cleaner.send_answer(message, SKIN_NOT_FOUND_TEXT)
        await state.clear()
        return

    await state.clear()
    await message_cleaner.send_answer(
        message,
        f"Target price обновлён: {format_price(target_price)}",
    )


def _format_edit_skin_list(skins: list[TrackedSkin]) -> str:
    parts = ["Твои скины:"]
    for skin in skins:
        parts.append(
            f"ID: {skin.id} — {skin.skin_name}, target: {format_price(skin.target_price)}"
        )
    return "\n".join(parts)


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
