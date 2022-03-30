'''
to create table on remote server
quit gunicorn, etc, then run in python shell:

from app import db
db.create_all()

'''
from flask import Flask, render_template, request, redirect, flash
from flask_sqlalchemy import SQLAlchemy
import re
import psycopg2
import os
import simplejson as sjson

psql_pass = os.environ.get('PSQL_PASS')

app = Flask(__name__)
app.secret_key = "mysupersecretkeywashere"
# used in conjunction with flash?

DEV = True

if DEV:
    from flask_cors import CORS
    CORS(app)  # remove when production? CORS will not be an issue?
    app.debug = True

app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:' + psql_pass + '@localhost/iss'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


class ISS(db.Model):
    __tablename__ = 'signup'
    id = db.Column(db.Integer, primary_key=True)
    fname = db.Column(db.String(80), nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    passes = db.Column(db.Integer, nullable=False)
    time = db.Column(db.Integer, nullable=False)
    city = db.Column(db.String(20), nullable=False)

    def __init__(self, fname, phone, passes, time, city):
        self.fname = fname
        self.phone = phone
        self.passes = passes
        self.time = time
        self.city = city


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/data')
def getData():
    connect = psycopg2.connect(
        database='iss',
        user='postgres',
        password=psql_pass
    )
    cursor = connect.cursor()
    cursor.execute("SELECT lat, lon FROM isspos ORDER BY id")
    data = cursor.fetchall()

    cursor.close()
    connect.close()

    return sjson.dumps(data)  # simple json solved the decimal error from coord's (psql numeric type)

    # return ''.join(str(data)) # the issue may be the psql numeric type, is considered Decimal regardless of input?
    # return json.dumps(data)
    # for row in data:
    #     return str(row)


@app.route('/submit', methods=['POST', 'GET'])
def submit():
    if request.method == 'POST':

        fname = request.form['fname']
        phone = request.form['phone']
        passes = request.form['passes']
        time = request.form['time']
        city = request.form['city']

        phoneClean = re.sub('[^0-9]', '', phone)

        found_phone = ISS.query.filter_by(phone=phoneClean).first()

        if found_phone:
            found_phone.passes = request.form['passes']
            found_phone.time = request.form['time']
            found_phone.city = request.form['city']
            db.session.commit()
            flash('your info has been updated!')
            return redirect('/')

        elif fname == '' or phone == '' or len(phoneClean) != 10:
            return render_template('signup.html', message='you might have left something blank, or entered a funky phone number. Try again?')
        else:
            data = ISS(fname, phoneClean, passes, time, city)
            db.session.add(data)
            db.session.commit()
            flash('signup success!')
            return redirect('/')  # return render_template didn't work here, left the "/submit" in place


@app.route('/faq')
def faq():
    return render_template('faq.html')


@app.route('/signup')
def signup():
    return render_template('signup.html')


if __name__ == "__main__":

    app.run()
