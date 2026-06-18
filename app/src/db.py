import uuid

from extensions import db


class Locker(db.Model):
    __tablename__ = "locker"

    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(50), nullable=True, index=True)
    device_uid = db.Column(db.String(64), nullable=True, unique=True, index=True)
    locker_id = db.Column(db.String(64), nullable=True, unique=True, index=True)
    name = db.Column(db.String(120), nullable=True)
    status = db.Column(db.String(16), nullable=False, default="unknown", index=True)
    last_seen_at = db.Column(db.DateTime, nullable=True)
    last_ping_at = db.Column(db.DateTime, nullable=True)
    intended_items = db.relationship(
        "Item", backref="locker_ref", lazy="dynamic", cascade="all, delete-orphan"
    )


class Item(db.Model):
    __tablename__ = "item"

    id = db.Column(db.Integer, primary_key=True)
    locker = db.Column(db.Integer, db.ForeignKey("locker.id"), nullable=True)
    name = db.Column(db.Text)
    parts = db.relationship(
        "Part", backref="item_ref", lazy="dynamic", cascade="all, delete-orphan"
    )

    def __init__(self, locker: Locker | int | None = None, name: str = "Locker"):
        self.name = name
        if locker is None:
            return

        if isinstance(locker, Locker):
            self.locker = locker.id
        else:
            self.locker = locker


class Part(db.Model):
    __tablename__ = "part"

    id = db.Column(db.Integer, primary_key=True)
    item = db.Column(db.Integer, db.ForeignKey("item.id"))
    name = db.Column(db.Text)
    uid_hex = db.Column(db.String(32), nullable=True)

    def __init__(self, item: Item | int, name: str, uid_hex: str | None = None):
        self.name = name
        self.uid_hex = uid_hex
        if isinstance(item, Item):
            self.item = item.id
        else:
            self.item = item


class ScannedPart(db.Model):
    __tablename__ = "scanned_part"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    locker_id = db.Column(db.Integer, db.ForeignKey("locker.id"))
    part_id = db.Column(db.Integer, db.ForeignKey("part.id"))

    def __init__(self, locker_id: str, part: Part | int):
        self.locker_id = locker_id
        if isinstance(part, Part):
            self.part_id = part.id
        else:
            self.part_id = part
