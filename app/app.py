from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from db import *
from os import path

basedir = path.abspath(path.dirname(__file__))
app = Flask(__name__)
app.config['SECRET_KEY'] = 'Ini0w91JO0209hcnol'

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + path.join(basedir, 'data.sqlite')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


@app.route("/")
def mainpage():
    with app.app_context():
        lockers = db.session.query(Locker).all()
        return render_template("main_page.html", lockers=lockers)

@app.route("/contents", methods=["POST"])
def contents():
    data = request.get_json()
    contents = data["contents"]

    with app.app_context():
        id = data["locker"]
        locker = db.session.get(Locker, id)
        if locker is not None:

            locker.contents = [LockerContents(locker, bytes.fromhex(i)) for i in contents]
            db.session.add(locker)
            db.session.commit()

            intendedItems = [uid for uid in contents if uid in locker.getContentUids()]
            response = {
                "volledig": len(intendedItems) == 2,
                "gedeeltelijk": len(contents) > 0
            }

            return jsonify(response)
    return jsonify({
        "volledig": False,
        "gedeeltelijk": False
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)