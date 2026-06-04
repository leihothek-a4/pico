import os
from secrets import compare_digest

from flask import Blueprint, jsonify, request

from db import Locker
from extensions import db

API_KEY = os.environ.get("API_KEY")

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.before_request
def check_authentication():
    if not API_KEY:
        return jsonify({"error": "Unauthorized"}), 401

    token = request.headers.get("Authorization", "")
    expected = f"Bearer {API_KEY}"
    if not compare_digest(token, expected):
        return jsonify({"error": "Unauthorized"}), 401


@api_bp.route("/connected")
def connected_ips():
    lockers = db.session.query(Locker).filter(Locker.ip.isnot(None)).all()
    ips = [locker.ip for locker in lockers if locker.ip and locker.ip.strip()]

    return jsonify({"ips": ips})
