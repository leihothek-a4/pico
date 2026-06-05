from sqlalchemy import inspect, text

from extensions import db


def ensure_part_uid_hex_column():
    inspector = inspect(db.engine)
    if "part" not in inspector.get_table_names():
        return

    existing = {c["name"] for c in inspector.get_columns("part")}
    with db.engine.begin() as conn:
        if "uid_hex" not in existing:
            conn.execute(text("ALTER TABLE part ADD COLUMN uid_hex VARCHAR(32)"))

        if "uid" in existing:
            rows = conn.execute(text("SELECT id, uid FROM part WHERE uid IS NOT NULL AND uid != ''")).fetchall()
            for row in rows:
                raw_uid = row[1]
                if raw_uid is None:
                    continue
                if isinstance(raw_uid, memoryview):
                    raw_uid = raw_uid.tobytes()
                if isinstance(raw_uid, bytes) and raw_uid:
                    hex_value = raw_uid.hex().lower()
                    conn.execute(
                        text("UPDATE part SET uid_hex = :uid_hex WHERE id = :id AND (uid_hex IS NULL OR uid_hex = '')"),
                        {"uid_hex": hex_value, "id": row[0]},
                    )
