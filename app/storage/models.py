from dataclasses import dataclass


@dataclass(frozen=True)
class TrackedSkin:
    id: int
    telegram_user_id: int
    skin_name: str
    target_price: float
    last_found_price: float | None
    url: str | None
    created_at: str


@dataclass(frozen=True)
class UserNotificationSettings:
    telegram_user_id: int
    notification_interval_seconds: int
    last_notification_sent_at: float | None
