import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.keyboards.main_menu import ADD_SKIN_CALLBACK
from app.services.lis_skins import LisSkinsApiError, LisSkinsClient, SkinOffer
from app.services.message_cleaner import MessageCleaner
from app.storage.sqlite_storage import SQLiteSkinStorage
from app.utils import format_price, parse_price


logger = logging.getLogger(__name__)
router = Router(name="add")


class AddSkin(StatesGroup):
    waiting_skin_name = State()
    waiting_target_price = State()


ADD_SKIN_PROMPT = """Напиши полное название скина.
Например:
Flip Knife | Doppler Phase 4 (Factory New)"""

TARGET_PRICE_PROMPT = """Напиши цену в долларах, при которой нужно отправить уведомление.
Например: 750"""

SKIN_NOT_FOUND_TEXT = "Скин не найден. Проверь название, фазу и качество."

ADD_SUCCESS_TEXT = """Готово. Я буду проверять цену примерно каждые 15 минут.
Если цена станет меньше или равна указанной, я напишу тебе.

Важно: если цена уже ниже или равна target price, уведомление будет приходить при каждой проверке, пока ты не удалишь этот скин через /remove."""


@router.message(Command("add"))
async def add_command(
    message: Message,
    state: FSMContext,
    message_cleaner: MessageCleaner,
) -> None:
    await start_add_flow(message, state, message_cleaner)


@router.callback_query(F.data == ADD_SKIN_CALLBACK)
async def add_callback(
    callback: CallbackQuery,
    state: FSMContext,
    message_cleaner: MessageCleaner,
) -> None:
    await callback.answer()
    if callback.message:
        await start_add_flow(
            callback.message,
            state,
            message_cleaner,
            replace_current=True,
        )


async def start_add_flow(
    message: Message,
    state: FSMContext,
    message_cleaner: MessageCleaner,
    replace_current: bool = False,
) -> None:
    await state.clear()
    await state.set_state(AddSkin.waiting_skin_name)
    await _send_clean(message, ADD_SKIN_PROMPT, message_cleaner, replace_current)


@router.message(AddSkin.waiting_skin_name, F.text, ~F.text.startswith("/"))
async def process_skin_name(
    message: Message,
    state: FSMContext,
    lis_skins_client: LisSkinsClient,
    tracked_skin_storage: SQLiteSkinStorage,
    message_cleaner: MessageCleaner,
) -> None:
    skin_name = (message.text or "").strip()
    if not skin_name:
        await message_cleaner.send_answer(message, ADD_SKIN_PROMPT)
        return

    try:
        offer = await lis_skins_client.find_skin(skin_name)
    except LisSkinsApiError:
        logger.exception("Cannot find skin because LIS-SKINS API is unavailable")
        await message_cleaner.send_answer(
            message,
            "LIS-SKINS API сейчас недоступен. Попробуй позже.",
        )
        await state.clear()
        return

    if offer is None:
        await message_cleaner.send_answer(message, SKIN_NOT_FOUND_TEXT)
        await state.clear()
        return

    if await tracked_skin_storage.user_has_skin(message.from_user.id, offer.name):
        await state.set_state(AddSkin.waiting_skin_name)
        await message_cleaner.send_answer(
            message,
            "Этот скин уже добавлен.\n\nНапиши другое полное название скина.",
        )
        return

    await state.update_data(found_skin=_offer_to_state_data(offer))
    await state.set_state(AddSkin.waiting_target_price)

    await message_cleaner.send_answer(
        message,
        "Нашёл скин:\n\n"
        f"Name: {offer.name}\n"
        f"Current price: {format_price(offer.price)}\n"
        f"Unlocked price: {format_price(offer.unlocked_price)}\n"
        f"Count: {offer.count}\n"
        f"URL: {offer.url or 'N/A'}\n\n"
        f"{TARGET_PRICE_PROMPT}"
    )


@router.message(AddSkin.waiting_target_price, F.text, ~F.text.startswith("/"))
async def process_target_price(
    message: Message,
    state: FSMContext,
    tracked_skin_storage: SQLiteSkinStorage,
    message_cleaner: MessageCleaner,
) -> None:
    raw_price = (message.text or "").strip()
    try:
        target_price = parse_price(raw_price)
    except ValueError:
        logger.info("Invalid target price from user %s: %r", message.from_user.id, raw_price)
        await message_cleaner.send_answer(
            message,
            "Неправильный формат цены. Напиши число в долларах, например: 750"
        )
        return

    data = await state.get_data()
    found_skin = data.get("found_skin")
    if not isinstance(found_skin, dict):
        logger.error("FSM data lost for user %s", message.from_user.id)
        await message_cleaner.send_answer(
            message,
            "Не удалось сохранить скин. Попробуй добавить его заново через /add.",
        )
        await state.clear()
        return

    await tracked_skin_storage.add_skin(
        telegram_user_id=message.from_user.id,
        skin_name=str(found_skin["name"]),
        target_price=target_price,
        last_found_price=float(found_skin["price"]),
        url=found_skin.get("url"),
    )
    await state.clear()
    await message_cleaner.send_answer(message, ADD_SUCCESS_TEXT)


def _offer_to_state_data(offer: SkinOffer) -> dict[str, object]:
    return {
        "name": offer.name,
        "price": offer.price,
        "unlocked_price": offer.unlocked_price,
        "count": offer.count,
        "url": offer.url,
    }


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
