from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.keyboards.main_menu import DOCS_CALLBACK
from app.services.message_cleaner import MessageCleaner


router = Router(name="docs")


DOCS_TEXT = """Что умеет бот:

- добавлять скины для отслеживания;
- показывать список твоих скинов;
- менять target price через /edit;
- менять частоту hot price уведомлений через /time;
- удалять скины;
- удалять все свои скины через /masterdelete с подтверждением WW;
- проверять цены примерно каждые 15 минут;
- присылать уведомление, если цена стала меньше или равна target price.

Через /time можно выбрать, как часто получать hot price уведомления.
Время должно быть не меньше 15 минут и не больше 24 часов.
Это не меняет общий fetch LIS-SKINS: он всё равно идёт примерно каждые 15 минут.

Уведомления будут приходить каждый раз при проверке, пока цена подходит под условие.
Чтобы остановить уведомления, удали скин через /remove.

Пример формата названия:
Flip Knife | Doppler Phase 4 (Factory New)

Важно:
- нужно указывать полное название скина;
- нужно указывать фазу, если она есть;
- нужно указывать качество, например Factory New;
- StatTrak пока не учитываем."""


@router.message(Command("docs"))
async def docs_command(
    message: Message,
    state: FSMContext,
    message_cleaner: MessageCleaner,
) -> None:
    await state.clear()
    await message_cleaner.send_answer(message, DOCS_TEXT)


@router.callback_query(F.data == DOCS_CALLBACK)
async def docs_callback(
    callback: CallbackQuery,
    state: FSMContext,
    message_cleaner: MessageCleaner,
) -> None:
    await state.clear()
    await callback.answer()
    if callback.message:
        await message_cleaner.replace_message(callback.message, DOCS_TEXT)
