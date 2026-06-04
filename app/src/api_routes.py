import os
from secrets import compare_digest

from flask import Blueprint, jsonify, request
from sqlalchemy import inspect, text

from db import Item, Locker, Part
from extensions import db

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


@api_bp.before_request
def check_authentication():
    if not API_KEY:
        return jsonify({"error": "Unauthorized"}), 401

    token = request.headers.get("Authorization", "")
    expected = f"Bearer {API_KEY}"
    if not compare_digest(token, expected):
        return jsonify({"error": "Unauthorized"}), 401


def uid_to_hex(uid: bytes | None) -> str | None:
    if not uid:
        return None
    return uid.hex().upper()


@api_bp.route("/connected")
def connected_ips():
    lockers = db.session.query(Locker).filter(Locker.ip.isnot(None)).all()
    ips = [locker.ip for locker in lockers if locker.ip and locker.ip.strip()]

    return jsonify({"ips": ips})


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
                    "uid_hex": uid_to_hex(part.uid),
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
