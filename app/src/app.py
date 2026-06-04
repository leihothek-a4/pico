from os import environ, path

from api_routes import api_bp
from auth_routes import auth_bp, register_auth_guard
from db import Item, Locker, Part
from extensions import db
from flask import Flask, flash, redirect, render_template, request, url_for

basedir = path.abspath(path.dirname(__file__))
app = Flask(__name__)
app.config["SECRET_KEY"] = environ.get("SECRET_KEY", "default-secret-key")

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + path.join(basedir, "data.sqlite")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)
app.register_blueprint(auth_bp)
register_auth_guard(app)

with app.app_context():
    db.create_all()


def parse_uid(raw: str) -> bytes | None:
    cleaned = raw.strip().replace(" ", "").replace(":", "")
    if not cleaned:
        return None
    return bytes.fromhex(cleaned)


@app.route("/")
def mainpage():
    lockers = db.session.query(Locker).all()
    return render_template("main_page.html", lockers=lockers)


@app.route("/lockers/new", methods=["GET", "POST"])
def new_locker():
    if request.method == "POST":
        ip = request.form.get("ip", "").strip() or None
        locker = Locker()
        locker.ip = ip
        db.session.add(locker)
        db.session.commit()
        flash(f"Locker {locker.id} created.")
        return redirect(url_for("mainpage"))
    return render_template("locker_form.html")


@app.route("/lockers/<int:locker_id>/items/new", methods=["GET", "POST"])
def new_item(locker_id):
    locker = db.session.get(Locker, locker_id)
    if locker is None:
        flash("Locker not found.")
        return redirect(url_for("mainpage"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            return render_template("item_form.html", locker=locker, name="")

        item = Item(locker, name)
        db.session.add(item)
        db.session.flush()

        part_names = [
            n.strip() for n in request.form.getlist("part_names") if n.strip()
        ]
        for part_name in part_names:
            db.session.add(Part(item, part_name, None))

        db.session.commit()
        part_msg = f" with {len(part_names)} part(s)" if part_names else ""
        flash(f'Item "{name}" created{part_msg}.')
        return redirect(url_for("mainpage"))

    return render_template("item_form.html", locker=locker)


@app.route("/items/<int:item_id>/parts/new", methods=["GET", "POST"])
def new_part(item_id):
    item = db.session.get(Item, item_id)
    if item is None:
        flash("Item not found.")
        return redirect(url_for("mainpage"))

    locker = db.session.get(Locker, item.locker)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        uid_raw = request.form.get("uid", "")

        if not name:
            return render_template(
                "part_form.html", item=item, locker=locker, uid=uid_raw
            )

        try:
            uid = parse_uid(uid_raw)
        except ValueError:
            flash("Invalid UID — use hex bytes like A7 A0 C8 01.")
            return render_template(
                "part_form.html",
                item=item,
                locker=locker,
                name=name,
                uid=uid_raw,
            )

        db.session.add(Part(item, name, uid))
        db.session.commit()
        flash(f'Part "{name}" added.')
        return redirect(url_for("mainpage"))

    return render_template("part_form.html", item=item, locker=locker)


if __name__ == "__main__":
    app.run(debug=True)
