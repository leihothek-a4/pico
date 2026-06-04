from extensions import db


class Locker(db.Model):
    __tablename__ = "locker"

    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(50), nullable=True, index=True)
    device_uid = db.Column(db.String(64), nullable=True, unique=True, index=True)
    locker_id = db.Column(db.String(64), nullable=True, unique=True, index=True)
    name = db.Column(db.String(120), nullable=True)
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
    uid = db.Column(db.LargeBinary(4), nullable=True)

    def __init__(self, item: Item | int, name: str, uid: bytes | None):
        self.name = name
        self.uid = uid
        if isinstance(item, Item):
            self.item = item.id
        else:
            self.item = item
