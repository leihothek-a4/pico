from db import *
from app import app, db

with app.app_context():
    db.create_all()

    locker = Locker()

    db.session.add(locker)
    db.session.commit()
    miniTableTennisSet = Item(locker, "mini table tennis set")

    db.session.add(miniTableTennisSet)
    db.session.commit()

    batton0 = Part(miniTableTennisSet, "batton", bytes([0xa7, 0xa0, 0xc8, 0x01]))
    batton1 = Part(miniTableTennisSet, "batton", bytes([0xb5, 0x4c, 0xb6, 0x02]))
    net = Part(miniTableTennisSet, "net", None)

    db.session.add_all([batton0, batton1, net])
    db.session.commit()