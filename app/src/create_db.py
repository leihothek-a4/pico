from app import app, db
from db import Item, Locker, Part

with app.app_context():
    db.create_all()

    locker = Locker()

    db.session.add(locker)
    db.session.commit()
    miniTableTennisSet = Item(locker, "mini table tennis set")

    db.session.add(miniTableTennisSet)
    db.session.commit()

    batton0 = Part(miniTableTennisSet, "batton", bytes([0xA7, 0xA0, 0xC8, 0x01]))
    batton1 = Part(miniTableTennisSet, "batton", bytes([0xB5, 0x4C, 0xB6, 0x02]))
    net = Part(miniTableTennisSet, "net", None)

    db.session.add_all([batton0, batton1, net])
    db.session.commit()
