UID_MIN_BYTES = 4
UID_MAX_BYTES = 10


def parse_uid(raw: str) -> bytes | None:
    cleaned = raw.strip().replace(" ", "").replace(":", "").replace("-", "")
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


def format_uid(uid: bytes | None) -> str:
    if not uid:
        return ""
    return " ".join(f"{b:02X}" for b in uid)
