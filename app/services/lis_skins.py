import asyncio
import logging
import re
import time
from dataclasses import dataclass
from typing import Any

import aiohttp

from app.utils import normalize_skin_name


logger = logging.getLogger(__name__)


class LisSkinsApiError(Exception):
    """Raised when LIS-SKINS price list cannot be fetched or parsed."""


@dataclass(frozen=True)
class SkinOffer:
    name: str
    price: float
    unlocked_price: float | None
    count: int
    url: str | None

    @classmethod
    def from_api_item(cls, item: dict[str, Any]) -> "SkinOffer":
        name = str(item["name"])
        price = float(item["price"])
        unlocked_raw = item.get("unlocked_price")
        unlocked_price = float(unlocked_raw) if unlocked_raw is not None else None
        count = int(item.get("count") or 0)
        url = item.get("url")

        if price <= 0:
            raise ValueError("price must be positive")

        return cls(
            name=name,
            price=price,
            unlocked_price=unlocked_price,
            count=count,
            url=str(url) if url else None,
        )


class LisSkinsClient:
    API_URL = "https://lis-skins.com/market_export_json/csgo.json"
    CACHE_TTL_SECONDS = 5.0

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session
        self._fetch_lock = asyncio.Lock()
        self._cached_price_list: list[dict[str, Any]] | None = None
        self._cache_expires_at = 0.0

    async def fetch_price_list(self, force_refresh: bool = False) -> list[dict[str, Any]]:
        if not force_refresh and self._is_cache_valid():
            logger.debug("Using cached LIS-SKINS price list")
            return self._cached_price_list or []

        async with self._fetch_lock:
            if not force_refresh and self._is_cache_valid():
                logger.debug("Using cached LIS-SKINS price list after waiting for fetch lock")
                return self._cached_price_list or []

            price_list = await self._fetch_price_list_from_api()
            self._cached_price_list = price_list
            self._cache_expires_at = time.monotonic() + self.CACHE_TTL_SECONDS
            return price_list

    async def _fetch_price_list_from_api(self) -> list[dict[str, Any]]:
        logger.info("Fetching LIS-SKINS price list: %s", self.API_URL)
        try:
            async with self._session.get(self.API_URL) as response:
                response.raise_for_status()
                data = await response.json(content_type=None)
        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            logger.exception("Failed to fetch LIS-SKINS price list")
            raise LisSkinsApiError("LIS-SKINS API is unavailable") from exc
        except ValueError as exc:
            logger.exception("Failed to parse LIS-SKINS price list JSON")
            raise LisSkinsApiError("Invalid LIS-SKINS API response") from exc

        if not isinstance(data, list) or not data:
            logger.error("LIS-SKINS returned empty or invalid price list: %r", data)
            raise LisSkinsApiError("Empty LIS-SKINS API response")

        logger.info("Fetched LIS-SKINS price list: items=%s", len(data))
        return data

    async def find_skin(self, skin_name: str) -> SkinOffer | None:
        price_list = await self.fetch_price_list()
        return self.find_skin_in_items(skin_name, price_list)

    def find_skin_in_items(
        self,
        skin_name: str,
        price_list: list[dict[str, Any]],
    ) -> SkinOffer | None:
        search_terms = _build_search_terms(skin_name)
        if not search_terms:
            return None

        matches: list[SkinOffer] = []
        for item in price_list:
            if not isinstance(item, dict):
                continue

            raw_name = item.get("name")
            if not raw_name:
                continue

            normalized_name = normalize_skin_name(str(raw_name))
            if "stattrak" in normalized_name:
                continue

            if not all(term in normalized_name for term in search_terms):
                continue

            try:
                matches.append(SkinOffer.from_api_item(item))
            except (KeyError, TypeError, ValueError):
                logger.exception("Skipping invalid LIS-SKINS item: %r", item)

        if not matches:
            return None

        return min(matches, key=lambda offer: offer.price)

    def _is_cache_valid(self) -> bool:
        return self._cached_price_list is not None and time.monotonic() < self._cache_expires_at


def _build_search_terms(skin_name: str) -> list[str]:
    raw_parts = re.split(r"[|()]+", skin_name)
    terms = [normalize_skin_name(part) for part in raw_parts]
    return [term for term in terms if term]
