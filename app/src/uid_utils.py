import re

UID_MIN_BYTES = 4
UID_MAX_BYTES = 10


def extract_uid_hex_digits(raw: str) -> str:
    cleaned = raw.strip().lower()
    cleaned = re.sub(r"0x", "", cleaned)
    cleaned = re.sub(r"[^0-9a-f]", "", cleaned)
    return cleaned


def parse_uid(raw: str) -> bytes | None:
    cleaned = extract_uid_hex_digits(raw)
    if not cleaned:
        return None
    if len(cleaned) % 2 != 0:
        raise ValueError("UID must have an even number of hex digits")
    uid = bytes.fromhex(cleaned)
    if len(uid) < UID_MIN_BYTES or len(uid) > UID_MAX_BYTES:
        raise ValueError(
            f"UID must be {UID_MIN_BYTES}-{UID_MAX_BYTES} bytes "
            f"({UID_MIN_BYTES * 2}-{UID_MAX_BYTES * 2} hex digits)"
        )
    return uid


def normalize_uid_hex(raw: str) -> str | None:
    uid = parse_uid(raw)
    if uid is None:
        return None
    return uid.hex().lower()


def format_uid_hex(stored: str | None) -> str:
    if not stored:
        return ""
    digits = extract_uid_hex_digits(stored)
    return " ".join(digits[i : i + 2].upper() for i in range(0, len(digits), 2))
