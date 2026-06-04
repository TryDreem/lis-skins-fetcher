import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.keyboards.main_menu import TIME_CALLBACK
from app.services.message_cleaner import MessageCleaner
from app.storage.sqlite_storage import SQLiteSkinStorage
from app.utils import format_notification_interval, parse_notification_interval


logger = logging.getLogger(__name__)
router = Router(name="time_settings")


class TimeSettings(StatesGroup):
    waiting_interval = State()


TIME_PROMPT = """Напиши, как часто отправлять уведомления.

Формат:
15min
1h
24h

Время должно быть не меньше 15 минут и не больше 24 часов.

Важно: общий fetch LIS-SKINS всё равно остаётся примерно раз в 15 минут."""


@router.message(Command("time"))
async def time_command(
    message: Message,
    state: FSMContext,
    tracked_skin_storage: SQLiteSkinStorage,
    message_cleaner: MessageCleaner,
) -> None:
    await start_time_flow(
        message=message,
        telegram_user_id=message.from_user.id,
        state=state,
        tracked_skin_storage=tracked_skin_storage,
        message_cleaner=message_cleaner,
    )


@router.callback_query(F.data == TIME_CALLBACK)
async def time_callback(
    callback: CallbackQuery,
    state: FSMContext,
    tracked_skin_storage: SQLiteSkinStorage,
    message_cleaner: MessageCleaner,
) -> None:
    await callback.answer()
    if callback.message:
        await start_time_flow(
            message=callback.message,
            telegram_user_id=callback.from_user.id,
            state=state,
            tracked_skin_storage=tracked_skin_storage,
            message_cleaner=message_cleaner,
            replace_current=True,
        )


async def start_time_flow(
    message: Message,
    telegram_user_id: int,
    state: FSMContext,
    tracked_skin_storage: SQLiteSkinStorage,
    message_cleaner: MessageCleaner,
    replace_current: bool = False,
) -> None:
    await state.clear()
    settings = await tracked_skin_storage.get_user_notification_settings(telegram_user_id)
    await state.set_state(TimeSettings.waiting_interval)

    text = (
        f"Текущий интервал уведомлений: "
        f"{format_notification_interval(settings.notification_interval_seconds)}\n\n"
        f"{TIME_PROMPT}"
    )
    await _send_clean(message, text, message_cleaner, replace_current)


@router.message(TimeSettings.waiting_interval, F.text, ~F.text.startswith("/"))
async def process_time_interval(
    message: Message,
    state: FSMContext,
    tracked_skin_storage: SQLiteSkinStorage,
    message_cleaner: MessageCleaner,
) -> None:
    raw_interval = (message.text or "").strip()
    try:
        interval_seconds = parse_notification_interval(raw_interval)
    except ValueError:
        logger.info(
            "Invalid notification interval from user %s: %r",
            message.from_user.id,
            raw_interval,
        )
        await message_cleaner.send_answer(
            message,
            "Неправильный формат. Примеры: 15min, 30min, 1h, 24h. "
            "Время должно быть не меньше 15 минут и не больше 24 часов.",
        )
        return

    await tracked_skin_storage.update_user_notification_interval(
        telegram_user_id=message.from_user.id,
        interval_seconds=interval_seconds,
    )
    await state.clear()
    await message_cleaner.send_answer(
        message,
        f"Готово. Теперь hot price уведомления будут приходить раз в "
        f"{format_notification_interval(interval_seconds)}.",
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
