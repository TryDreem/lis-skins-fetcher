import re


def normalize_skin_name(value: str) -> str:
    normalized = value.casefold().replace("★", "").replace("™", "")
    normalized = re.sub(r"[^\w]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()
