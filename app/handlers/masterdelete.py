import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.keyboards import main_menu_keyboard
from app.keyboards.main_menu import MASTER_DELETE_CALLBACK
from app.services.message_cleaner import MessageCleaner
from app.storage.sqlite_storage import SQLiteSkinStorage


logger = logging.getLogger(__name__)
router = Router(name="masterdelete")


class MasterDelete(StatesGroup):
    waiting_confirmation = State()


CONFIRM_TEXT = """Напиши WW, чтобы удалить все свои скины.

Если напишешь что-то другое, удаление отменится."""


@router.message(Command("masterdelete"))
async def masterdelete_command(
    message: Message,
    state: FSMContext,
    message_cleaner: MessageCleaner,
) -> None:
    await start_masterdelete_flow(message, state, message_cleaner)


@router.callback_query(F.data == MASTER_DELETE_CALLBACK)
async def masterdelete_callback(
    callback: CallbackQuery,
    state: FSMContext,
    message_cleaner: MessageCleaner,
) -> None:
    await callback.answer()
    if callback.message:
        await start_masterdelete_flow(
            callback.message,
            state,
            message_cleaner,
            replace_current=True,
        )


async def start_masterdelete_flow(
    message: Message,
    state: FSMContext,
    message_cleaner: MessageCleaner,
    replace_current: bool = False,
) -> None:
    await state.clear()
    await state.set_state(MasterDelete.waiting_confirmation)
    if replace_current:
        await message_cleaner.replace_message(message, CONFIRM_TEXT)
        return

    await message_cleaner.send_answer(message, CONFIRM_TEXT)


@router.message(MasterDelete.waiting_confirmation, F.text, ~F.text.startswith("/"))
async def process_masterdelete_confirmation(
    message: Message,
    state: FSMContext,
    tracked_skin_storage: SQLiteSkinStorage,
    message_cleaner: MessageCleaner,
) -> None:
    confirmation = (message.text or "").strip()
    await state.clear()

    if confirmation != "WW":
        logger.info("User %s cancelled masterdelete", message.from_user.id)
        await message_cleaner.send_answer(
            message,
            "Удаление отменено. Главное меню:",
            reply_markup=main_menu_keyboard(),
        )
        return

    deleted_count = await tracked_skin_storage.delete_all_user_skins(message.from_user.id)
    logger.info(
        "User %s deleted all tracked skins: count=%s",
        message.from_user.id,
        deleted_count,
    )
    await message_cleaner.send_answer(
        message,
        f"Удалено скинов: {deleted_count}.\n\nГлавное меню:",
        reply_markup=main_menu_keyboard(),
    )
