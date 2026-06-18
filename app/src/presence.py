import os
from datetime import datetime, timezone

from db import Locker
from extensions import db

DEFAULT_PRESENCE_TIMEOUT_SECONDS = 150


def presence_timeout_seconds() -> int:
    raw = os.environ.get("PRESENCE_TIMEOUT_SECONDS", "").strip()
    if not raw:
        return DEFAULT_PRESENCE_TIMEOUT_SECONDS
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_PRESENCE_TIMEOUT_SECONDS
    return max(30, value)


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def seconds_since(last_seen_at: datetime | None) -> int | None:
    if last_seen_at is None:
        return None
    return max(0, int((utcnow() - last_seen_at).total_seconds()))


def effective_status(locker: Locker, timeout_s: int | None = None) -> str:
    timeout = timeout_s if timeout_s is not None else presence_timeout_seconds()
    if locker.last_seen_at is None:
        stored = locker.status or "unknown"
        return stored if stored in {"offline", "unknown"} else "unknown"
    age = seconds_since(locker.last_seen_at)
    if age is not None and age <= timeout:
        return "online"
    return "offline"


def locker_payload(locker: Locker, *, timeout_s: int | None = None) -> dict:
    status = effective_status(locker, timeout_s)
    age = seconds_since(locker.last_seen_at)
    return {
        "id": locker.id,
        "device_uid": locker.device_uid,
        "locker_id": locker.locker_id,
        "name": locker.name,
        "ip": locker.ip,
        "status": status,
        "online": status == "online",
        "last_seen_at": locker.last_seen_at.isoformat() + "Z" if locker.last_seen_at else None,
        "last_ping_at": locker.last_ping_at.isoformat() + "Z" if locker.last_ping_at else None,
        "seconds_since_seen": age,
    }


def find_locker(*, ip: str | None = None, locker_id: str | None = None, device_uid: str | None = None) -> Locker | None:
    if locker_id:
        locker = db.session.query(Locker).filter_by(locker_id=locker_id).first()
        if locker is not None:
            return locker
    if device_uid:
        locker = db.session.query(Locker).filter_by(device_uid=device_uid).first()
        if locker is not None:
            return locker
    if ip:
        return db.session.query(Locker).filter_by(ip=ip).first()
    return None


def record_checkin(locker: Locker) -> None:
    """Mark a locker online when the Pico calls an authenticated API (e.g. inventory)."""
    now = utcnow()
    locker.status = "online"
    locker.last_seen_at = now


def apply_presence(locker: Locker, online: bool) -> None:
    """Legacy ping-based presence (optional n8n ICMP workflow)."""
    now = utcnow()
    locker.last_ping_at = now
    if online:
        locker.status = "online"
        locker.last_seen_at = now
    else:
        locker.status = "offline"


def refresh_stale_lockers(timeout_s: int | None = None) -> int:
    """Persist offline status for lockers that missed the check-in window."""
    timeout = timeout_s if timeout_s is not None else presence_timeout_seconds()
    changed = 0
    lockers = db.session.query(Locker).all()
    for locker in lockers:
        if locker.last_seen_at is None:
            continue
        if effective_status(locker, timeout) == "offline" and locker.status != "offline":
            locker.status = "offline"
            changed += 1
    return changed


def presence_summary(lockers: list[Locker], timeout_s: int | None = None) -> dict:
    timeout = timeout_s if timeout_s is not None else presence_timeout_seconds()
    payloads = [locker_payload(locker, timeout_s=timeout) for locker in lockers]
    summary = {"online": 0, "offline": 0, "unknown": 0, "total": len(payloads)}
    for entry in payloads:
        key = entry["status"] if entry["status"] in summary else "unknown"
        summary[key] += 1
    return {
        "presence_timeout_seconds": timeout,
        "checked_at": utcnow().isoformat() + "Z",
        "summary": summary,
        "lockers": payloads,
    }
