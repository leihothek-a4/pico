from flask import Flask, render_template
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

if __name__ == "__main__":
    app.run(debug=True)