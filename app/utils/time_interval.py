import re


MIN_NOTIFICATION_INTERVAL_SECONDS = 15 * 60
MAX_NOTIFICATION_INTERVAL_SECONDS = 24 * 60 * 60


def parse_notification_interval(raw_value: str) -> int:
    value = re.sub(r"\s+", "", raw_value.casefold().strip())
    match = re.fullmatch(r"(\d+)(min|mins|minute|minutes|m|h|hour|hours)", value)
    if match is None:
        raise ValueError("Invalid interval format")

    amount = int(match.group(1))
    unit = match.group(2)

    if unit in {"h", "hour", "hours"}:
        seconds = amount * 60 * 60
    else:
        seconds = amount * 60

    if seconds < MIN_NOTIFICATION_INTERVAL_SECONDS:
        raise ValueError("Interval must be at least 15 minutes")

    if seconds > MAX_NOTIFICATION_INTERVAL_SECONDS:
        raise ValueError("Interval must be at most 24 hours")

    return seconds


def format_notification_interval(seconds: int) -> str:
    if seconds % 3600 == 0:
        hours = seconds // 3600
        return f"{hours}h"

    minutes = seconds // 60
    return f"{minutes}min"
