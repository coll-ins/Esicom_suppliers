import re

PHONE_HELP = "Kenyan number starting 07, 01 or +254, for example 0712 345 678."


def normalize_ke_phone(raw: str) -> str:
    """Return +2547XXXXXXXX / +2541XXXXXXXX, or raise ValueError with a plain reason."""
    digits = re.sub(r"[\s\-().]", "", raw or "")
    m = re.fullmatch(r"(?:\+254|254|0)([17]\d{8})", digits)
    if not m:
        raise ValueError(f"Not a callable Kenyan number. Use {PHONE_HELP}")
    return "+254" + m.group(1)


def display_ke_phone(stored: str) -> str:
    """+254712345678 -> 0712 345 678"""
    if not stored or not stored.startswith("+254") or len(stored) != 13:
        return stored or ""
    local = "0" + stored[4:]
    return f"{local[:4]} {local[4:7]} {local[7:]}"


def clean_text(raw, field: str, *, min_len: int = 0, max_len: int) -> str:
    """Trim; reject too short, too long, or text with no letters or digits (gibberish like '!!!')."""
    value = re.sub(r"\s+", " ", str(raw or "")).strip()
    if len(value) < min_len:
        raise ValueError(f"{field} is required." if min_len <= 1 else f"{field} must be at least {min_len} characters.")
    if len(value) > max_len:
        raise ValueError(f"{field} must be {max_len} characters or fewer.")
    if value and not re.search(r"[A-Za-z0-9]", value):
        raise ValueError(f"{field} must contain letters or numbers.")
    return value


def whole_kes(raw, field: str, *, minimum: int = 0, maximum: int = 100_000_000) -> int:
    """Whole shillings only: '1,500' or 1500. Cents are rejected, not rounded."""
    if isinstance(raw, bool):
        raise ValueError(f"{field} must be a whole number of shillings, for example 1500.")
    if isinstance(raw, int):
        value = raw
    else:
        text = str(raw if raw is not None else "").replace(",", "").strip()
        if not re.fullmatch(r"\d+", text):
            raise ValueError(f"{field} must be a whole number of shillings, for example 1500. No cents.")
        value = int(text)
    if value < minimum:
        raise ValueError(f"{field} must be at least {minimum:,}.")
    if value > maximum:
        raise ValueError(f"{field} is too large.")
    return value


def whole_qty(raw, field: str = "Quantity", *, minimum: int = 1, maximum: int = 1_000_000) -> int:
    if isinstance(raw, bool):
        raise ValueError(f"{field} must be a whole number, for example 5.")
    text = str(raw if raw is not None else "").replace(",", "").strip()
    if not re.fullmatch(r"\d+", text):
        raise ValueError(f"{field} must be a whole number, for example 5.")
    value = int(text)
    if value < minimum:
        raise ValueError(f"{field} must be at least {minimum}.")
    if value > maximum:
        raise ValueError(f"{field} is too large.")
    return value
