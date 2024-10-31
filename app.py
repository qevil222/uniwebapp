from io import BytesIO
from flask import Flask, render_template, request, url_for, redirect, session, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_session import Session
from cachelib.file import FileSystemCache
from authlib.integrations.flask_client import OAuth
import json
import os
import time as t
from datetime import datetime as dt
from csv_read import programmes as JUPAS_PROGRAMMES
import collections

# Setup
app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config["SESSION_TYPE"] = "cachelib"
app.config["SESSION_SERIALIZATION_FORMAT"] = "json"
app.config["SESSION_CACHELIB"] = FileSystemCache(cache_dir="/sessions")
Session(app)

oauth = OAuth(app)
GOOGLE_CLIENT_ID = ""
GOOGLE_CLIENT_SECRET = ""
CONF_URL = "https://accounts.google.com/.well-known/openid-configuration"
with open("oauth_client_secrets.json") as f:
    oauth_json: dict = json.load(f)["web"]
    GOOGLE_CLIENT_ID = oauth_json["client_id"]
    GOOGLE_CLIENT_SECRET = oauth_json["client_secret"]
oauth.register(
    name="google",
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url=CONF_URL,
    client_kwargs={
        'verify': False,
        'scope': 'openid email profile'
    }
)
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1" # Waive SSL requirement
app.config["SQLALCHEMY_DATABASE_URI"] = f"mysql+pymysql://uniwebapp:[bBwWpDHnaeiP8]]@localhost/uniwebapp"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
# DB username: uniwebapp
# DB pwd: [bBwWpDHnaeiP8]]
# DB host: localhost
# DB name: uniwebapp


# Database model - students profile
class Students(db.Model):
    id = db.Column(db.String(8), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    cls = db.Column(db.String(4), nullable=False)
    c_num = db.Column(db.Integer, nullable=False)
    curriculum = db.Column(db.String(3), nullable=True)
    info_sent = db.Column(db.Boolean, default=False, nullable=False)
    notes = db.Column(db.String(500), nullable=True)

    def __init__(self, id, name, cls, c_num, curriculum, info_sent, notes):
        self.id = id
        self.name = name
        self.cls = cls
        self.c_num = c_num
        self.curriculum = curriculum
        self.info_sent = info_sent
        self.notes = notes

# Database model - survey results
class sResults(db.Model):
    __tablename__ = "s_results"
    student_id = db.Column(db.String(8), nullable=False)
    time = db.Column(db.Integer, nullable=False)
    sub1 = db.Column(db.String(200), nullable=False)
    sub2 = db.Column(db.String(200) , nullable=True)
    sub3 = db.Column(db.String(200), nullable=True)
    country = db.Column(db.String(50), nullable=True)
    __table_args__ = (db.PrimaryKeyConstraint(student_id, time),)

    def __init__(self, student_id, time, sub1, sub2, sub3, country):
        self.student_id = student_id
        self.time = time
        self.sub1 = sub1
        self.sub2 = sub2
        self.sub3 = sub3
        self.country = country

# Database model - Jupas courses
class Jupas(db.Model):
    course_id = db.Column(db.String(6), primary_key=True)
    course_name = db.Column(db.String(200), nullable=False)
    uni = db.Column(db.String(200), nullable=False)
    country = db.Column(db.String(50), nullable=False)

    def __init__(self, course_id, course_name, uni, country):
        self.course_id = course_id
        self.course_name = course_name
        self.uni = uni
        self.country = country

# Database model - staff
class Staff(db.Model):    
    email = db.Column(db.String(100), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    is_superuser = db.Column(db.Boolean, nullable=False)

    def __init__(self, email, name, is_superuser):
        self.email = email
        self.name = name
        self.is_superuser = is_superuser

# Database model - pg
class Pg(db.Model):
    id = db.Column(db.String(8), primary_key = True)
    filename = db.Column(db.String(50))
    data = db.Column(db.LargeBinary)

    def __init__(self, id, filename, data):
        self.id = id
        self.filename = filename
        self.data = data

# Database model - recommendation
class Recommendation(db.Model):
    id = db.Column(db.String(8), primary_key = True)
    filename = db.Column(db.String(50))
    data = db.Column(db.LargeBinary)

    def __init__(self, id, filename, data):
        self.id = id
        self.filename = filename
        self.data = data   

# Database model - certificates
class Certificates(db.Model):
    id = db.Column(db.String(8), primary_key = True)
    filename = db.Column(db.String(50))
    data = db.Column(db.LargeBinary)

    def __init__(self, id, filename, data):
        self.id = id
        self.filename = filename
        self.data = data 

# Database model - transcripts
class Transcripts(db.Model):
    id = db.Column(db.String(8), primary_key = True)
    filename = db.Column(db.String(50))
    data = db.Column(db.LargeBinary)

    def __init__(self, id, filename, data):
        self.id = id
        self.filename = filename
        self.data = data     

# Database model - others
class Others(db.Model):
    id = db.Column(db.String(8), primary_key = True)
    filename = db.Column(db.String(50))
    data = db.Column(db.LargeBinary)

    def __init__(self, id, filename, data):
        self.id = id
        self.filename = filename
        self.data = data                       


# Webpages
@app.route("/")
def first():
    return "You are logged out. <a href='/login'>Login?</a>"

@app.route("/login")
def login():
    return oauth.google.authorize_redirect("http://localhost:5000/login_callback")

@app.route("/login_callback")
def callback():
    EMAIL_ADMINS = []
    EMAIL_SUPERUSERS = ["pwyeung@logosacademy.edu.hk"]
    token = oauth.google.authorize_access_token()
    user = token["userinfo"]
    session["is_teacher"] = not "elearn" in user["hd"] 
    session["email"] = user["email"]
    session["name"] = user["name"]
    session["picture"] = user["picture"]
    if session["is_teacher"]:
        if session["email"] in EMAIL_SUPERUSERS:
            session["staff_level"] = 2
        elif session["email"] in EMAIL_ADMINS:
            session["staff_level"] = 1
        else:
            session["staff_level"] = 0
    session["is_teacher"] = True        # OVERRIDE
    session["staff_level"] = 2          # OVERRIDE
    return redirect('/home')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')
"""
'userinfo': {
'email': 's1401010@elearn.logosacademy.edu.hk', 
'name': 'MS3V01 陳愷翹 CHAN Hoi Kiu Trinity [s]',
'picture': 'https://lh3.googleusercontent.com/a/ACg8ocJNz0wmZFnRWMWLHaHlJUkN5MgizK2rCmgixyI3u6gy-GPkAfNH=s96-c',
'given_name': 'MS3V01 陳愷翹 CHAN Hoi Kiu Trinity',
'family_name': '[s]',
"""

@app.route("/home", methods=['GET', 'POST'])
def home():
    if not session["is_teacher"]:
        student_id = session["email"].split("@")[0].lower()
        if request.method == "GET":
            files = (
                Pg.query.get(student_id),
                Recommendation.query.get(student_id),
                Certificates.query.get(student_id),
                Transcripts.query.get(student_id),
                Others.query.get(student_id)
            )
            student = Students.query.get(student_id)
            info_sent = bool(Students.query.get(student_id).info_sent)
            return render_template("profile.html", files=files, info_sent=info_sent, student=student)
        if request.method == 'POST':
            file_type = request.form["type"]
            if file_type == "Pg":
                file = request.files['Pg']
                upload = Pg(id=student_id, filename=file.filename, data=file.read()) 
                db.session.add(upload)
                db.session.commit()
                return redirect("/home")
            elif file_type == "recommendation":
                file = request.files['recommendation']
                upload = Recommendation(id=student_id, filename=file.filename, data=file.read()) 
                db.session.add(upload)
                db.session.commit()
                return redirect("/home")
            elif file_type == "certificates":
                file = request.files['certificates'] 
                upload = Certificates(id=student_id, filename=file.filename, data=file.read()) 
                db.session.add(upload)
                db.session.commit()  
                return redirect("/home")
            elif file_type == "transcripts":
                file = request.files['transcripts']
                upload = Transcripts(id=student_id, filename=file.filename, data=file.read()) 
                db.session.add(upload)
                db.session.commit()    
                return redirect("/home")
            elif file_type == "others":
                file = request.files['others']
                upload = Others(id=student_id, filename=file.filename, data=file.read()) 
                db.session.add(upload)
                db.session.commit()
                return redirect("/home")
    return redirect("/unis")
    
@app.route('/pg_download/<upload_id>')
def download_Pg(upload_id):
    upload = Pg.query.get(upload_id)
    return send_file(BytesIO(upload.data), download_name=upload.filename, as_attachment=True)

@app.route('/recommendation_download/<upload_id>')
def download_recommendation(upload_id):
    upload = Recommendation.query.get(upload_id)
    return send_file(BytesIO(upload.data), download_name=upload.filename, as_attachment=True)

@app.route('/certificates_download/<upload_id>')
def download_certificates(upload_id):
    upload = Certificates.query.get(upload_id)
    return send_file(BytesIO(upload.data), download_name=upload.filename, as_attachment=True)

@app.route('/transcripts_download/<upload_id>')
def download_transcripts(upload_id):
    upload = Transcripts.query.get(upload_id)
    return send_file(BytesIO(upload.data), download_name=upload.filename, as_attachment=True)

@app.route('/others_download/<upload_id>')
def download_others(upload_id):
    if session["is_teacher"]:
        if session["staff_level"] < 1:
            return redirect("/home")
    if session["email"].split("@")[0].lower() != upload_id:
        return redirect("/home")
    upload = Others.query.get(upload_id)
    return send_file(BytesIO(upload.data), download_name=upload.filename, as_attachment=True)

@app.route("/unis")
def unis():
    if not session:
        return redirect("/")
    return render_template("unis.html", programmes=JUPAS_PROGRAMMES)

@app.route("/students")
def students():
    if not session:
        return redirect("/")
    if not session["is_teacher"]:
        return redirect("/home")
    students = Students.query.all()
    return render_template("students.html", students=students)

@app.route("/view_student/<id>")
def view_student(id):
    if not session:
        return redirect("/")
    if not session["is_teacher"]:
        return redirect("/home")
    if session["staff_level"] < 1:
        return redirect("/home")
    id = id.lower()
    student = Students.query.get(id)
    if request.method == "GET":
        if session["staff_level"] != 0:
            files = (
                Pg.query.get(id),
                Recommendation.query.get(id),
                Certificates.query.get(id),
                Transcripts.query.get(id),
                Others.query.get(id)
            )
            info_sent = bool(student.info_sent)
            s_results = sResults.query.filter_by(student_id=id).all()
            return render_template("profile.html", files=files, info_sent=info_sent, student=student, s_results=s_results)

@app.route("/edit_student/<id>", methods=["GET", "POST"])
def edit_student(id):
    if request.method == "GET":
        student = Students.query.get(id)
        return render_template("students_edit.html", session=session, student=student)
    if request.method == "POST":
        form = request.form
        student = Students.query.get(form["id"])
        student.name = form["name"]
        student.cls = form["cls"]
        student.c_num = form["c_num"]
        student.curriculum = form["curriculum"] if form["curriculum"] in ("DSE", "IB") else None
        student.info_sent = form["info_sent"] == "1"
        student.notes = form["notes"]
        db.session.commit()
        return redirect(f"/view_student/{id}")

@app.route("/admins")
def admins():
    if not session:
        return redirect("/")
    if session["is_teacher"]:
        if session["staff_level"] == 2:
            admins = Staff.query.all()
            return render_template("admins.html", session=session, admins=admins)
    return redirect("/home")

@app.route("/edit_admin/<email>", methods=["GET", "POST"])
def edit_admin(email):
    if not session:
        return redirect("/")
    if not session["is_teacher"]:
        return redirect("/home")
    if session["is_teacher"]:
        if session["staff_level"] <= 1:
            return redirect("/home")
    if request.method == "GET":
        admin = Staff.query.get(email)
        return render_template("admins_edit.html", session=session, admin=admin)
    if request.method == "POST":
        form = request.form
        admin = Staff.query.get(form["email"])
        admin.name = form["name"]
        admin.is_superuser = form["is_superuser"] == 1
        db.session.commit()
        return redirect("/admins")

@app.route("/survey", methods=["GET", "POST"])
def survey():
    if not session:
        return redirect("/")
    if session["is_teacher"]:
        return redirect("/home")
    if request.method == "GET":
        return render_template("survey.html", session=session, programmes=JUPAS_PROGRAMMES)
    elif request.method == "POST":
        form = request.form
        entry = sResults(
            session["email"].split("@")[0].lower(), 
            int(t.time()),
            form["subject-1"],
            form["subject-2"],
            form["subject-3"],
            form["ideal-location"]
        )
        db.session.add(entry)
        db.session.commit()
        return redirect("/home")

@app.route("/sresults")
def sresults():
    
    if not session["is_teacher"]:
        return redirect("/home")
    
    # Fetch all rows and count no. of overseas choices
    sResults_all = sResults.query.all()
    subj1 = []
    subj2 = []
    subj3 = []
    for result in sResults_all:
        subj1.append(result.sub1)
        subj2.append(result.sub2)
        subj3.append(result.sub3)
    def count(subj: list) -> int: return len(subj) - sum((n[:2] == "JS" and n[4:].isdigit()) or not n for n in subj)
    count_overseas_subj1 = count(subj1)
    count_overseas_subj2 = count(subj2)
    count_overseas_subj3 = count(subj3)
    subj1 = collections.Counter(subj1)
    subj2 = collections.Counter(subj2)
    subj3 = collections.Counter(subj3)

    # Get printout of sResults table (with name, class, class no.)
    printouts = sResults.query\
                        .join(Students, sResults.student_id==Students.id)\
                        .add_columns(Students.name, Students.cls, Students.c_num, sResults.time, 
                                     sResults.sub1, sResults.sub2, sResults.sub3, sResults.country)\
                        .filter(sResults.student_id == Students.id)\
                        .order_by(sResults.time.desc())
    def format_time(unix_time: int) -> str: return dt.fromtimestamp(unix_time).strftime("%Y-%m-%d %H:%M:%S")

    return render_template(
        "sresults.html", session=session, programmes=JUPAS_PROGRAMMES, subj1=subj1, subj2=subj2, subj3=subj3, 
        overseas=(count_overseas_subj1, count_overseas_subj2, count_overseas_subj3), 
        printouts=printouts, format_time=format_time
    )

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
