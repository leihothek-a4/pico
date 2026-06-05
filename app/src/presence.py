from datetime import datetime, timezone

from db import Locker
from extensions import db


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def locker_payload(locker: Locker) -> dict:
    return {
        "id": locker.id,
        "device_uid": locker.device_uid,
        "locker_id": locker.locker_id,
        "name": locker.name,
        "ip": locker.ip,
        "status": locker.status or "unknown",
        "last_seen_at": locker.last_seen_at.isoformat() + "Z" if locker.last_seen_at else None,
        "last_ping_at": locker.last_ping_at.isoformat() + "Z" if locker.last_ping_at else None,
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


def apply_presence(locker: Locker, online: bool) -> None:
    now = utcnow()
    locker.last_ping_at = now
    if online:
        locker.status = "online"
        locker.last_seen_at = now
    else:
        locker.status = "offline"
