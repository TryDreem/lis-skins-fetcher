import logging
from pathlib import Path

import aiosqlite

from app.storage.models import TrackedSkin, UserNotificationSettings
from app.utils import normalize_skin_name


logger = logging.getLogger(__name__)


class SQLiteSkinStorage:
    def __init__(self, database_path: str) -> None:
        self._database_path = Path(database_path)
        self._connection: aiosqlite.Connection | None = None

    async def init(self) -> None:
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = await aiosqlite.connect(self._database_path)
        self._connection.row_factory = aiosqlite.Row
        await self._connection.execute("PRAGMA journal_mode=WAL")
        await self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS telegram_users (
                telegram_user_id INTEGER PRIMARY KEY,
                notification_interval_seconds INTEGER NOT NULL DEFAULT 900,
                last_notification_sent_at REAL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        await self._ensure_telegram_users_columns()
        await self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS tracked_skins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_user_id INTEGER NOT NULL,
                skin_name TEXT NOT NULL,
                skin_name_key TEXT NOT NULL DEFAULT '',
                target_price REAL NOT NULL,
                last_found_price REAL,
                url TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        await self._ensure_tracked_skins_columns()
        await self._connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_tracked_skins_user_id
            ON tracked_skins (telegram_user_id)
            """
        )
        await self._connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_tracked_skins_user_skin_key
            ON tracked_skins (telegram_user_id, skin_name_key)
            """
        )
        await self._connection.commit()
        logger.info("SQLite storage initialized at %s", self._database_path)

    async def close(self) -> None:
        if self._connection is not None:
            await self._connection.close()
            self._connection = None

    @property
    def connection(self) -> aiosqlite.Connection:
        if self._connection is None:
            raise RuntimeError("SQLite storage is not initialized")
        return self._connection

    async def ensure_user(self, telegram_user_id: int) -> bool:
        cursor = await self.connection.execute(
            """
            INSERT OR IGNORE INTO telegram_users (telegram_user_id)
            VALUES (?)
            """,
            (telegram_user_id,),
        )
        await self.connection.commit()
        return cursor.rowcount > 0

    async def get_user_notification_settings(
        self,
        telegram_user_id: int,
    ) -> UserNotificationSettings:
        await self.ensure_user(telegram_user_id)
        cursor = await self.connection.execute(
            """
            SELECT telegram_user_id, notification_interval_seconds, last_notification_sent_at
            FROM telegram_users
            WHERE telegram_user_id = ?
            """,
            (telegram_user_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            raise RuntimeError("Failed to load user notification settings")

        return self._row_to_user_notification_settings(row)

    async def list_notification_settings(
        self,
        telegram_user_ids: list[int],
    ) -> dict[int, UserNotificationSettings]:
        if not telegram_user_ids:
            return {}

        unique_user_ids = sorted(set(telegram_user_ids))
        for telegram_user_id in unique_user_ids:
            await self.ensure_user(telegram_user_id)

        placeholders = ", ".join("?" for _ in unique_user_ids)
        cursor = await self.connection.execute(
            f"""
            SELECT telegram_user_id, notification_interval_seconds, last_notification_sent_at
            FROM telegram_users
            WHERE telegram_user_id IN ({placeholders})
            """,
            unique_user_ids,
        )
        rows = await cursor.fetchall()
        return {
            row["telegram_user_id"]: self._row_to_user_notification_settings(row)
            for row in rows
        }

    async def update_user_notification_interval(
        self,
        telegram_user_id: int,
        interval_seconds: int,
    ) -> None:
        await self.ensure_user(telegram_user_id)
        await self.connection.execute(
            """
            UPDATE telegram_users
            SET notification_interval_seconds = ?
            WHERE telegram_user_id = ?
            """,
            (interval_seconds, telegram_user_id),
        )
        await self.connection.commit()

    async def update_user_last_notification_sent_at(
        self,
        telegram_user_id: int,
        sent_at: float,
    ) -> None:
        await self.ensure_user(telegram_user_id)
        await self.connection.execute(
            """
            UPDATE telegram_users
            SET last_notification_sent_at = ?
            WHERE telegram_user_id = ?
            """,
            (sent_at, telegram_user_id),
        )
        await self.connection.commit()

    async def add_skin(
        self,
        telegram_user_id: int,
        skin_name: str,
        target_price: float,
        last_found_price: float | None,
        url: str | None,
    ) -> TrackedSkin:
        skin_name_key = normalize_skin_name(skin_name)
        cursor = await self.connection.execute(
            """
            INSERT INTO tracked_skins (
                telegram_user_id,
                skin_name,
                skin_name_key,
                target_price,
                last_found_price,
                url
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (telegram_user_id, skin_name, skin_name_key, target_price, last_found_price, url),
        )
        await self.connection.commit()

        skin = await self.get_skin_by_id(cursor.lastrowid)
        if skin is None:
            raise RuntimeError("Failed to load inserted skin")

        return skin

    async def user_has_skin(self, telegram_user_id: int, skin_name: str) -> bool:
        cursor = await self.connection.execute(
            """
            SELECT 1
            FROM tracked_skins
            WHERE telegram_user_id = ? AND skin_name_key = ?
            LIMIT 1
            """,
            (telegram_user_id, normalize_skin_name(skin_name)),
        )
        row = await cursor.fetchone()
        return row is not None

    async def get_skin_by_id(self, skin_id: int) -> TrackedSkin | None:
        cursor = await self.connection.execute(
            """
            SELECT id, telegram_user_id, skin_name, target_price, last_found_price, url, created_at
            FROM tracked_skins
            WHERE id = ?
            """,
            (skin_id,),
        )
        row = await cursor.fetchone()
        return self._row_to_skin(row) if row else None

    async def list_user_skins(self, telegram_user_id: int) -> list[TrackedSkin]:
        cursor = await self.connection.execute(
            """
            SELECT id, telegram_user_id, skin_name, target_price, last_found_price, url, created_at
            FROM tracked_skins
            WHERE telegram_user_id = ?
            ORDER BY id
            """,
            (telegram_user_id,),
        )
        rows = await cursor.fetchall()
        return [self._row_to_skin(row) for row in rows]

    async def list_all_skins(self) -> list[TrackedSkin]:
        cursor = await self.connection.execute(
            """
            SELECT id, telegram_user_id, skin_name, target_price, last_found_price, url, created_at
            FROM tracked_skins
            ORDER BY id
            """
        )
        rows = await cursor.fetchall()
        return [self._row_to_skin(row) for row in rows]

    async def update_last_found_price(
        self,
        skin_id: int,
        last_found_price: float,
        url: str | None,
    ) -> None:
        await self.connection.execute(
            """
            UPDATE tracked_skins
            SET last_found_price = ?, url = ?
            WHERE id = ?
            """,
            (last_found_price, url, skin_id),
        )
        await self.connection.commit()

    async def update_user_skin_target_price(
        self,
        telegram_user_id: int,
        skin_id: int,
        target_price: float,
    ) -> bool:
        cursor = await self.connection.execute(
            """
            UPDATE tracked_skins
            SET target_price = ?
            WHERE telegram_user_id = ? AND id = ?
            """,
            (target_price, telegram_user_id, skin_id),
        )
        await self.connection.commit()
        return cursor.rowcount > 0

    async def delete_user_skin(self, telegram_user_id: int, skin_id: int) -> bool:
        cursor = await self.connection.execute(
            """
            DELETE FROM tracked_skins
            WHERE telegram_user_id = ? AND id = ?
            """,
            (telegram_user_id, skin_id),
        )
        await self.connection.commit()
        return cursor.rowcount > 0

    async def delete_all_user_skins(self, telegram_user_id: int) -> int:
        cursor = await self.connection.execute(
            """
            DELETE FROM tracked_skins
            WHERE telegram_user_id = ?
            """,
            (telegram_user_id,),
        )
        await self.connection.commit()
        return cursor.rowcount

    @staticmethod
    def _row_to_skin(row: aiosqlite.Row) -> TrackedSkin:
        return TrackedSkin(
            id=row["id"],
            telegram_user_id=row["telegram_user_id"],
            skin_name=row["skin_name"],
            target_price=row["target_price"],
            last_found_price=row["last_found_price"],
            url=row["url"],
            created_at=row["created_at"],
        )

    @staticmethod
    def _row_to_user_notification_settings(row: aiosqlite.Row) -> UserNotificationSettings:
        return UserNotificationSettings(
            telegram_user_id=row["telegram_user_id"],
            notification_interval_seconds=row["notification_interval_seconds"],
            last_notification_sent_at=row["last_notification_sent_at"],
        )

    async def _ensure_telegram_users_columns(self) -> None:
        cursor = await self.connection.execute("PRAGMA table_info(telegram_users)")
        columns = {row["name"] for row in await cursor.fetchall()}

        if "notification_interval_seconds" not in columns:
            await self.connection.execute(
                """
                ALTER TABLE telegram_users
                ADD COLUMN notification_interval_seconds INTEGER NOT NULL DEFAULT 900
                """
            )

        if "last_notification_sent_at" not in columns:
            await self.connection.execute(
                """
                ALTER TABLE telegram_users
                ADD COLUMN last_notification_sent_at REAL
                """
            )

    async def _ensure_tracked_skins_columns(self) -> None:
        cursor = await self.connection.execute("PRAGMA table_info(tracked_skins)")
        columns = {row["name"] for row in await cursor.fetchall()}

        if "skin_name_key" not in columns:
            await self.connection.execute(
                """
                ALTER TABLE tracked_skins
                ADD COLUMN skin_name_key TEXT NOT NULL DEFAULT ''
                """
            )

        cursor = await self.connection.execute(
            """
            SELECT id, skin_name
            FROM tracked_skins
            WHERE skin_name_key = ''
            """
        )
        rows = await cursor.fetchall()
        for row in rows:
            await self.connection.execute(
                """
                UPDATE tracked_skins
                SET skin_name_key = ?
                WHERE id = ?
                """,
                (normalize_skin_name(row["skin_name"]), row["id"]),
            )
