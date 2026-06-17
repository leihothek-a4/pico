import logging
import os
from secrets import compare_digest

from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)
from sqlalchemy import inspect, text

from db import Item, Locker, Part
from extensions import db
from presence import apply_presence, find_locker, locker_payload

API_KEY = os.environ.get("API_KEY")

api_bp = Blueprint("api", __name__, url_prefix="/api")


def ensure_locker_columns():
    """Add device_uid / locker_id / name columns to existing SQLite DBs."""
    inspector = inspect(db.engine)
    if "locker" not in inspector.get_table_names():
        return
    existing = {c["name"] for c in inspector.get_columns("locker")}
    with db.engine.begin() as conn:
        if "device_uid" not in existing:
            conn.execute(text("ALTER TABLE locker ADD COLUMN device_uid VARCHAR(64)"))
        if "locker_id" not in existing:
            conn.execute(text("ALTER TABLE locker ADD COLUMN locker_id VARCHAR(64)"))
        if "name" not in existing:
            conn.execute(text("ALTER TABLE locker ADD COLUMN name VARCHAR(120)"))
        if "status" not in existing:
            conn.execute(
                text("ALTER TABLE locker ADD COLUMN status VARCHAR(16) NOT NULL DEFAULT 'unknown'")
            )
        if "last_seen_at" not in existing:
            conn.execute(text("ALTER TABLE locker ADD COLUMN last_seen_at DATETIME"))
        if "last_ping_at" not in existing:
            conn.execute(text("ALTER TABLE locker ADD COLUMN last_ping_at DATETIME"))


def auth_failure_payload(token: str) -> dict:
    bearer_value = token[7:] if token.startswith("Bearer ") else ""
    return {
        "error": "Unauthorized",
        "hint": "Send header: Authorization: Bearer <API_KEY>",
        "auth": {
            "header_present": bool(token),
            "header_length": len(token),
            "starts_with_bearer": token.startswith("Bearer "),
            "bearer_value_length": len(bearer_value),
            "expected_bearer_length": len(API_KEY) if API_KEY else 0,
            "server_api_key_configured": bool(API_KEY),
        },
    }


@api_bp.before_request
def check_authentication():
    if not API_KEY:
        payload = {
            "error": "Unauthorized",
            "hint": "Server API_KEY is not configured",
            "auth": {"server_api_key_configured": False},
        }
        logger.warning("API auth rejected: %s %s — API_KEY not set", request.method, request.path)
        return jsonify(payload), 401

    token = request.headers.get("Authorization", "")
    expected = f"Bearer {API_KEY}"
    if not compare_digest(token, expected):
        payload = auth_failure_payload(token)
        logger.warning(
            "API auth failed: %s %s from %s — %s",
            request.method,
            request.path,
            request.remote_addr,
            payload["auth"],
        )
        return jsonify(payload), 401


def uid_to_hex(uid_hex: str | None) -> str | None:
    if not uid_hex:
        return None
    return uid_hex.upper()


def parse_presence_entry(entry: dict) -> tuple[str | None, str | None, str | None, bool | None]:
    ip = (entry.get("ip") or "").strip() or None
    locker_id = (entry.get("locker_id") or "").strip() or None
    device_uid = (entry.get("device_uid") or "").strip() or None
    online = entry.get("online")
    if online is not None and not isinstance(online, bool):
        if str(online).lower() in {"1", "true", "yes", "online"}:
            online = True
        elif str(online).lower() in {"0", "false", "no", "offline"}:
            online = False
        else:
            online = None
    return ip, locker_id, device_uid, online


@api_bp.route("/health")
def health():
    return jsonify({"ok": True, "features": ["uid_hex", "inline_part_edit", "presence"]})


@api_bp.route("/connected")
def connected_ips():
    lockers = db.session.query(Locker).filter(Locker.ip.isnot(None)).all()
    ips = [locker.ip for locker in lockers if locker.ip and locker.ip.strip()]

    return jsonify({"ips": ips})


@api_bp.route("/lockers", methods=["GET"])
def list_lockers():
    lockers = db.session.query(Locker).order_by(Locker.id.asc()).all()
    return jsonify({"lockers": [locker_payload(locker) for locker in lockers]})


@api_bp.route("/lockers/status", methods=["GET"])
def locker_status():
    return list_lockers()


@api_bp.route("/lockers/presence", methods=["POST"])
def update_presence():
    data = request.get_json(silent=True) or {}
    ip, locker_id, device_uid, online = parse_presence_entry(data)

    if online is None:
        return jsonify({"error": "online is required (boolean)"}), 400
    if not any([ip, locker_id, device_uid]):
        return jsonify({"error": "ip, locker_id, or device_uid is required"}), 400

    locker = find_locker(ip=ip, locker_id=locker_id, device_uid=device_uid)
    if locker is None:
        return jsonify({"error": "locker not found"}), 404

    apply_presence(locker, online)
    db.session.commit()

    return jsonify(locker_payload(locker))


@api_bp.route("/lockers/presence/batch", methods=["POST"])
def update_presence_batch():
    data = request.get_json(silent=True) or {}
    results = data.get("results")
    if not isinstance(results, list) or not results:
        return jsonify({"error": "results must be a non-empty array"}), 400

    updated = []
    missing = []
    invalid = []

    for index, entry in enumerate(results):
        if not isinstance(entry, dict):
            invalid.append({"index": index, "error": "entry must be an object"})
            continue

        ip, locker_id, device_uid, online = parse_presence_entry(entry)
        if online is None:
            invalid.append({"index": index, "error": "online is required (boolean)"})
            continue
        if not any([ip, locker_id, device_uid]):
            invalid.append({"index": index, "error": "ip, locker_id, or device_uid is required"})
            continue

        locker = find_locker(ip=ip, locker_id=locker_id, device_uid=device_uid)
        if locker is None:
            missing.append({"index": index, "ip": ip, "locker_id": locker_id, "device_uid": device_uid})
            continue

        apply_presence(locker, online)
        updated.append(locker_payload(locker))

    db.session.commit()

    return jsonify(
        {
            "updated": updated,
            "updated_count": len(updated),
            "missing": missing,
            "missing_count": len(missing),
            "invalid": invalid,
            "invalid_count": len(invalid),
        }
    )


@api_bp.route("/lockers", methods=["POST"])
def create_locker():
    data = request.get_json(silent=True) or {}
    ip = (data.get("ip") or request.form.get("ip", "")).strip()
    if not ip:
        return jsonify({"error": "ip is required"}), 400

    locker = Locker()
    locker.ip = ip
    db.session.add(locker)
    db.session.commit()

    return jsonify({"id": locker.id, "ip": locker.ip}), 201


@api_bp.route("/lockers/sync", methods=["POST"])
def sync_locker():
    data = request.get_json(silent=True) or {}
    device_uid = (data.get("device_uid") or "").strip()
    locker_id = (data.get("locker_id") or "").strip()
    ip = (data.get("ip") or data.get("ip_address") or "").strip() or None
    name = (data.get("name") or "").strip() or None

    if not device_uid:
        return jsonify({"error": "device_uid is required"}), 400
    if not locker_id:
        return jsonify({"error": "locker_id is required"}), 400

    locker = db.session.query(Locker).filter_by(device_uid=device_uid).first()
    if locker is None:
        locker = db.session.query(Locker).filter_by(locker_id=locker_id).first()

    if locker is None:
        locker = Locker()
        db.session.add(locker)

    locker.device_uid = device_uid
    locker.locker_id = locker_id
    if ip:
        locker.ip = ip
    if name:
        locker.name = name

    db.session.commit()

    return jsonify(
        {
            "id": locker.id,
            "device_uid": locker.device_uid,
            "locker_id": locker.locker_id,
            "ip": locker.ip,
            "name": locker.name,
        }
    )


@api_bp.route("/inventory")
def inventory():
    locker_id = (request.args.get("locker_id") or "").strip()
    device_uid = (request.args.get("device_uid") or "").strip()

    if not locker_id or not device_uid:
        return jsonify({"error": "locker_id and device_uid are required"}), 400

    locker = (
        db.session.query(Locker)
        .filter_by(locker_id=locker_id, device_uid=device_uid)
        .first()
    )
    if locker is None:
        return jsonify({"error": "locker not found"}), 404

    items_out = []
    for item in locker.intended_items:
        parts_out = []
        for part in item.parts:
            parts_out.append(
                {
                    "id": part.id,
                    "name": part.name,
                    "uid_hex": uid_to_hex(part.uid_hex),
                }
            )
        items_out.append(
            {
                "id": item.id,
                "name": item.name,
                "parts": parts_out,
            }
        )

    return jsonify(
        {
            "locker_id": locker.locker_id,
            "device_uid": locker.device_uid,
            "items": items_out,
        }
    )
