from os import environ, path

from api_routes import api_bp
from auth_routes import auth_bp, register_auth_guard
from db import Item, Locker, Part
from extensions import db
from flask import Flask, flash, redirect, render_template, request, url_for
<<<<<<< Updated upstream
=======
from schema_migrations import ensure_part_uid_hex_column
from uid_utils import format_uid_hex, normalize_uid_hex, parse_uid
>>>>>>> Stashed changes

basedir = path.abspath(path.dirname(__file__))
app = Flask(__name__)
app.config["SECRET_KEY"] = environ.get("SECRET_KEY", "default-secret-key")

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + path.join(basedir, "data.sqlite")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)
app.register_blueprint(api_bp)
app.register_blueprint(auth_bp)
register_auth_guard(app)

with app.app_context():
    db.create_all()
    from api_routes import ensure_locker_columns

    ensure_locker_columns()
    ensure_part_uid_hex_column()


def parse_uid(raw: str) -> bytes | None:
    cleaned = raw.strip().replace(" ", "").replace(":", "")
    if not cleaned:
        return None
    return bytes.fromhex(cleaned)


@app.route("/")
def mainpage():
    lockers = db.session.query(Locker).all()
<<<<<<< Updated upstream
    return render_template("main_page.html", lockers=lockers)
=======
    return render_template(
        "main_page.html",
        lockers=lockers,
        format_timestamp=format_timestamp,
        format_uid_hex=format_uid_hex,
    )


@app.route("/status")
def status_dashboard():
    lockers = db.session.query(Locker).order_by(Locker.id.asc()).all()
    online_count = sum(1 for locker in lockers if locker.status == "online")
    offline_count = sum(1 for locker in lockers if locker.status == "offline")
    unknown_count = sum(1 for locker in lockers if (locker.status or "unknown") == "unknown")
    return render_template(
        "status_page.html",
        lockers=lockers,
        online_count=online_count,
        offline_count=offline_count,
        unknown_count=unknown_count,
        format_timestamp=format_timestamp,
    )
>>>>>>> Stashed changes


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

<<<<<<< Updated upstream
        part_names = [
            n.strip() for n in request.form.getlist("part_names") if n.strip()
        ]
        for part_name in part_names:
            db.session.add(Part(item, part_name, None))
=======
        part_names = request.form.getlist("part_names")
        part_uids = request.form.getlist("part_uids")
        part_errors = []

        for index, raw_name in enumerate(part_names):
            part_name = raw_name.strip()
            if not part_name:
                continue

            uid_raw = part_uids[index].strip() if index < len(part_uids) else ""
            try:
                uid_hex = normalize_uid_hex(uid_raw)
            except ValueError as exc:
                part_errors.append(f"{part_name}: {exc}")
                continue

            db.session.add(Part(item, part_name, uid_hex))

        if part_errors:
            for message in part_errors:
                flash(message)
            return render_template(
                "item_form.html",
                locker=locker,
                name=name,
                part_rows=list(zip(part_names, part_uids)),
            )
>>>>>>> Stashed changes

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
            flash("Part name is required.")
            return render_template(
                "part_form.html",
                item=item,
                locker=locker,
                uid=uid_raw,
                submit_label="Add",
            )

        try:
<<<<<<< Updated upstream
            uid = parse_uid(uid_raw)
        except ValueError:
            flash("Invalid UID — use hex bytes like A7 A0 C8 01.")
=======
            uid_hex = normalize_uid_hex(uid_raw)
        except ValueError as exc:
            flash(str(exc))
>>>>>>> Stashed changes
            return render_template(
                "part_form.html",
                item=item,
                locker=locker,
                name=name,
                uid=uid_raw,
            )

        db.session.add(Part(item, name, uid_hex))
        db.session.commit()
        flash(f'Part "{name}" added.')
        return redirect(url_for("mainpage"))

<<<<<<< Updated upstream
    return render_template("part_form.html", item=item, locker=locker)
=======
    return render_template(
        "part_form.html",
        item=item,
        locker=locker,
        submit_label="Add",
    )


@app.route("/parts/<int:part_id>/edit", methods=["GET", "POST"])
def edit_part(part_id):
    part = db.session.get(Part, part_id)
    if part is None:
        flash("Part not found.")
        return redirect(url_for("mainpage"))

    item = db.session.get(Item, part.item)
    locker = db.session.get(Locker, item.locker) if item else None

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        uid_raw = request.form.get("uid", "")

        if not name:
            return render_template(
                "part_form.html",
                item=item,
                locker=locker,
                part=part,
                name=name,
                uid=uid_raw,
                submit_label="Save",
            )

        try:
            uid_hex = normalize_uid_hex(uid_raw)
        except ValueError as exc:
            flash(str(exc))
            return render_template(
                "part_form.html",
                item=item,
                locker=locker,
                part=part,
                name=name,
                uid=uid_raw,
                submit_label="Save",
            )

        part.name = name
        part.uid_hex = uid_hex
        db.session.commit()
        flash(
            f'Part "{name}" updated.'
            + (f' RFID UID: {format_uid_hex(uid_hex)}' if uid_hex else " RFID UID cleared.")
        )
        return redirect(url_for("mainpage"))

    return render_template(
        "part_form.html",
        item=item,
        locker=locker,
        part=part,
        name=part.name,
        uid=format_uid_hex(part.uid_hex),
        submit_label="Save",
    )
>>>>>>> Stashed changes


if __name__ == "__main__":
    app.run(debug=True)
