import asyncio
import logging
import time

from aiogram.exceptions import TelegramAPIError

from app.services.lis_skins import LisSkinsApiError, LisSkinsClient, SkinOffer
from app.services.message_cleaner import MessageCleaner
from app.storage.models import TrackedSkin
from app.storage.sqlite_storage import SQLiteSkinStorage
from app.utils import format_price


logger = logging.getLogger(__name__)


class PriceChecker:
    def __init__(
        self,
        storage: SQLiteSkinStorage,
        lis_skins_client: LisSkinsClient,
        message_cleaner: MessageCleaner,
        interval_seconds: int,
    ) -> None:
        self._storage = storage
        self._lis_skins_client = lis_skins_client
        self._message_cleaner = message_cleaner
        self._interval_seconds = interval_seconds

    async def run(self) -> None:
        logger.info("Price checker started with interval %s seconds", self._interval_seconds)
        while True:
            try:
                await self.check_once()
            except asyncio.CancelledError:
                logger.info("Price checker stopped")
                raise
            except Exception:
                logger.exception("Unexpected price checker error")

            await asyncio.sleep(self._interval_seconds)

    async def check_once(self) -> None:
        tracked_skins = await self._storage.list_all_skins()
        if not tracked_skins:
            logger.debug("No tracked skins to check")
            return

        logger.info("Starting price check: tracked_skins=%s", len(tracked_skins))
        try:
            price_list = await self._lis_skins_client.fetch_price_list(force_refresh=True)
        except LisSkinsApiError:
            logger.exception("Skipping price check because LIS-SKINS API is unavailable")
            return

        offer_cache: dict[str, SkinOffer | None] = {}
        hot_offers_by_user: dict[int, list[tuple[TrackedSkin, SkinOffer]]] = {}
        for tracked_skin in tracked_skins:
            cache_key = _skin_cache_key(tracked_skin.skin_name)
            if cache_key not in offer_cache:
                offer_cache[cache_key] = self._lis_skins_client.find_skin_in_items(
                    tracked_skin.skin_name,
                    price_list,
                )

            offer = offer_cache[cache_key]
            if offer is None:
                logger.warning(
                    "Tracked skin id=%s was not found in LIS-SKINS price list; last_found_price remains unchanged",
                    tracked_skin.id,
                )
                continue

            await self._storage.update_last_found_price(
                skin_id=tracked_skin.id,
                last_found_price=offer.price,
                url=offer.url,
            )

            if offer.price <= tracked_skin.target_price:
                logger.info(
                    "Hot price: user_id=%s skin_id=%s skin_name=%r current_price=%s target_price=%s",
                    tracked_skin.telegram_user_id,
                    tracked_skin.id,
                    tracked_skin.skin_name,
                    offer.price,
                    tracked_skin.target_price,
                )
                hot_offers_by_user.setdefault(tracked_skin.telegram_user_id, []).append(
                    (tracked_skin, offer)
                )

        await self._send_due_hot_notifications(hot_offers_by_user)

        logger.info(
            "Finished price check: tracked_skins=%s unique_skin_queries=%s",
            len(tracked_skins),
            len(offer_cache),
        )

    async def _send_due_hot_notifications(
        self,
        hot_offers_by_user: dict[int, list[tuple[TrackedSkin, SkinOffer]]],
    ) -> None:
        if not hot_offers_by_user:
            return

        now = time.time()
        settings_by_user = await self._storage.list_notification_settings(
            list(hot_offers_by_user.keys())
        )

        for telegram_user_id, hot_offers in hot_offers_by_user.items():
            settings = settings_by_user[telegram_user_id]
            last_sent_at = settings.last_notification_sent_at
            if (
                last_sent_at is not None
                and now - last_sent_at < settings.notification_interval_seconds
            ):
                logger.info(
                    "Skipping hot price notifications due to user interval: user_id=%s hot_count=%s interval_seconds=%s seconds_left=%s",
                    telegram_user_id,
                    len(hot_offers),
                    settings.notification_interval_seconds,
                    int(settings.notification_interval_seconds - (now - last_sent_at)),
                )
                continue

            sent_any = False
            for tracked_skin, offer in hot_offers:
                sent = await self._send_price_notification(tracked_skin, offer)
                sent_any = sent_any or sent

            if sent_any:
                await self._storage.update_user_last_notification_sent_at(
                    telegram_user_id=telegram_user_id,
                    sent_at=now,
                )

    async def _send_price_notification(self, tracked_skin: TrackedSkin, offer: SkinOffer) -> bool:
        text = (
            "🔥 Горячая цена!\n\n"
            f"Твой скин сейчас стоит {format_price(offer.price)}\n\n"
            f"Name: {offer.name}\n"
            f"Target price: {format_price(tracked_skin.target_price)}\n"
            f"Unlocked price: {format_price(offer.unlocked_price)}\n"
            f"Count: {offer.count}\n"
            f"URL: {offer.url or 'N/A'}\n\n"
            "Чтобы остановить эти уведомления, удали скин через /remove."
        )

        try:
            await self._message_cleaner.send_persistent_message(
                chat_id=tracked_skin.telegram_user_id,
                text=text,
            )
            return True
        except TelegramAPIError:
            logger.exception(
                "Failed to send price notification to user %s for skin id=%s",
                tracked_skin.telegram_user_id,
                tracked_skin.id,
            )
            return False


def _skin_cache_key(skin_name: str) -> str:
    return " ".join(skin_name.casefold().split())
