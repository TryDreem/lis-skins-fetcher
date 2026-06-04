from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.keyboards import main_menu_keyboard
from app.keyboards.main_menu import FOR_ARISTARKH_CALLBACK
from app.services.message_cleaner import MessageCleaner


router = Router(name="for_aristarkh")


class ForAristarkh(StatesGroup):
    waiting_unlock = State()


UNLOCK_CODE = "VladWW"

FOR_ARISTARKH_TEXT = """5 причин не показывать очко Владу
1.Это дефолт
2.Не покупай хуевые скины
3.WW Team мета
4.На это ведуться только лохи (нит)
5.Хуй вам хуй нам как говориться

Чтобы продолжить, напиши VladWW.
Иначе нельзя выйти в другое меню, даже если очистишь чат или нажмешь /start."""


LOCKED_TEXT = "Нельзя выйти в другое меню. Чтобы продолжить, напиши VladWW."


@router.message(ForAristarkh.waiting_unlock)
async def process_locked_message(
    message: Message,
    state: FSMContext,
    message_cleaner: MessageCleaner,
) -> None:
    if (message.text or "").strip() == UNLOCK_CODE:
        await state.clear()
        await message_cleaner.send_answer(
            message,
            "Доступ открыт. Главное меню:",
            reply_markup=main_menu_keyboard(),
        )
        return

    await message_cleaner.send_answer(message, LOCKED_TEXT)


@router.callback_query(ForAristarkh.waiting_unlock)
async def process_locked_callback(
    callback: CallbackQuery,
    message_cleaner: MessageCleaner,
) -> None:
    await callback.answer("Сначала напиши VladWW.", show_alert=True)
    if callback.message:
        await message_cleaner.replace_message(callback.message, LOCKED_TEXT)


@router.message(Command("foraristarkh", ignore_case=True, ignore_mention=True))
async def for_aristarkh_command(
    message: Message,
    state: FSMContext,
    message_cleaner: MessageCleaner,
) -> None:
    await start_for_aristarkh_flow(message, state, message_cleaner)


@router.callback_query(F.data == FOR_ARISTARKH_CALLBACK)
async def for_aristarkh_callback(
    callback: CallbackQuery,
    state: FSMContext,
    message_cleaner: MessageCleaner,
) -> None:
    await callback.answer()
    if callback.message:
        await start_for_aristarkh_flow(
            callback.message,
            state,
            message_cleaner,
            replace_current=True,
        )


async def start_for_aristarkh_flow(
    message: Message,
    state: FSMContext,
    message_cleaner: MessageCleaner,
    replace_current: bool = False,
) -> None:
    await state.clear()
    await state.set_state(ForAristarkh.waiting_unlock)
    if replace_current:
        await message_cleaner.replace_message(message, FOR_ARISTARKH_TEXT)
        return

    await message_cleaner.send_answer(message, FOR_ARISTARKH_TEXT)
