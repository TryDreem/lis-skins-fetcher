from decimal import Decimal, InvalidOperation


def parse_price(raw_value: str) -> float:
    cleaned = raw_value.strip().replace("$", "").replace(" ", "").replace(",", ".")
    try:
        value = Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValueError("Invalid price format") from exc

    if not value.is_finite() or value <= 0:
        raise ValueError("Price must be a positive number")

    return float(value)


def format_price(value: float | int | None) -> str:
    if value is None:
        return "N/A"

    decimal_value = Decimal(str(value)).quantize(Decimal("0.01"))
    text = f"{decimal_value:.2f}".rstrip("0").rstrip(".")
    return f"${text}"
