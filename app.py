from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3, os, hashlib
from datetime import datetime

app = Flask(__name__)
app.secret_key = "change-this-secret-key"

DB = os.path.join(os.path.dirname(__file__), "hospital.db")

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS patients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        age INTEGER,
        gender TEXT,
        phone TEXT,
        blood_group TEXT,
        address TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS doctors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        specialization TEXT,
        phone TEXT,
        email TEXT
    );
    CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER,
        doctor_id INTEGER,
        appointment_date TEXT,
        status TEXT DEFAULT 'Scheduled',
        notes TEXT,
        FOREIGN KEY(patient_id) REFERENCES patients(id),
        FOREIGN KEY(doctor_id) REFERENCES doctors(id)
    );
    CREATE TABLE IF NOT EXISTS medical_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER,
        summary TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS bills (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER,
        consultation REAL DEFAULT 0,
        room_charges REAL DEFAULT 0,
        lab_charges REAL DEFAULT 0,
        medicine_charges REAL DEFAULT 0,
        total REAL DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)
    if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        pwd = hashlib.sha256("admin123".encode()).hexdigest()
        conn.execute("INSERT INTO users(name,email,password,role) VALUES(?,?,?,?)",
                     ("System Administrator","admin@hospital.local",pwd,"admin"))
    if conn.execute("SELECT COUNT(*) FROM doctors").fetchone()[0] == 0:
        conn.executemany("INSERT INTO doctors(name,specialization,phone,email) VALUES(?,?,?,?)", [
            ("Dr. Raj Sharma","Cardiology","9876543210","raj@hospital.local"),
            ("Dr. Priya Verma","General Medicine","9876543211","priya@hospital.local"),
            ("Dr. Amit Khan","Orthopedics","9876543212","amit@hospital.local")
        ])
    conn.commit()
    conn.close()

def login_required():
    return "user_id" in session

@app.route("/")
def home():
    if login_required():
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip()
        password = hashlib.sha256(request.form["password"].encode()).hexdigest()
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email=? AND password=?", (email,password)).fetchone()
        conn.close()
        if user:
            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["role"] = user["role"]
            return redirect(url_for("dashboard"))
        flash("Invalid email or password.", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/dashboard")
def dashboard():
    if not login_required(): return redirect(url_for("login"))
    conn = get_db()
    stats = {
        "patients": conn.execute("SELECT COUNT(*) FROM patients").fetchone()[0],
        "doctors": conn.execute("SELECT COUNT(*) FROM doctors").fetchone()[0],
        "appointments": conn.execute("SELECT COUNT(*) FROM appointments").fetchone()[0],
        "revenue": conn.execute("SELECT COALESCE(SUM(total),0) FROM bills").fetchone()[0],
    }
    recent = conn.execute("""
        SELECT a.*, p.name patient_name, d.name doctor_name
        FROM appointments a
        LEFT JOIN patients p ON p.id=a.patient_id
        LEFT JOIN doctors d ON d.id=a.doctor_id
        ORDER BY a.id DESC LIMIT 6
    """).fetchall()
    conn.close()
    return render_template("dashboard.html", stats=stats, recent=recent)

@app.route("/patients")
def patients():
    if not login_required(): return redirect(url_for("login"))
    conn = get_db()
    rows = conn.execute("SELECT * FROM patients ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("patients.html", patients=rows)

@app.route("/patients/add", methods=["GET","POST"])
def add_patient():
    if not login_required(): return redirect(url_for("login"))
    if request.method == "POST":
        conn = get_db()
        conn.execute("""INSERT INTO patients(name,age,gender,phone,blood_group,address)
                        VALUES(?,?,?,?,?,?)""",
                     (request.form["name"], request.form["age"] or None,
                      request.form["gender"], request.form["phone"],
                      request.form["blood_group"], request.form["address"]))
        conn.commit(); conn.close()
        flash("Patient registered successfully.", "success")
        return redirect(url_for("patients"))
    return render_template("patient_form.html")

@app.route("/doctors")
def doctors():
    if not login_required(): return redirect(url_for("login"))
    conn=get_db(); rows=conn.execute("SELECT * FROM doctors ORDER BY id DESC").fetchall(); conn.close()
    return render_template("doctors.html", doctors=rows)

@app.route("/appointments", methods=["GET","POST"])
def appointments():
    if not login_required(): return redirect(url_for("login"))
    conn=get_db()
    if request.method == "POST":
        conn.execute("""INSERT INTO appointments(patient_id,doctor_id,appointment_date,status,notes)
                        VALUES(?,?,?,?,?)""",
                     (request.form["patient_id"], request.form["doctor_id"],
                      request.form["appointment_date"], "Scheduled", request.form["notes"]))
        conn.commit()
        flash("Appointment created.", "success")
    rows=conn.execute("""SELECT a.*,p.name patient_name,d.name doctor_name
                         FROM appointments a
                         LEFT JOIN patients p ON p.id=a.patient_id
                         LEFT JOIN doctors d ON d.id=a.doctor_id
                         ORDER BY a.appointment_date DESC""").fetchall()
    pats=conn.execute("SELECT * FROM patients ORDER BY name").fetchall()
    docs=conn.execute("SELECT * FROM doctors ORDER BY name").fetchall()
    conn.close()
    return render_template("appointments.html", appointments=rows, patients=pats, doctors=docs)

@app.route("/billing", methods=["GET","POST"])
def billing():
    if not login_required(): return redirect(url_for("login"))
    conn=get_db()
    if request.method=="POST":
        c=float(request.form.get("consultation") or 0)
        r=float(request.form.get("room_charges") or 0)
        l=float(request.form.get("lab_charges") or 0)
        m=float(request.form.get("medicine_charges") or 0)
        total=c+r+l+m
        conn.execute("""INSERT INTO bills(patient_id,consultation,room_charges,lab_charges,medicine_charges,total)
                        VALUES(?,?,?,?,?,?)""",
                     (request.form["patient_id"],c,r,l,m,total))
        conn.commit(); flash("Bill generated.", "success")
    bills=conn.execute("""SELECT b.*,p.name patient_name FROM bills b
                          LEFT JOIN patients p ON p.id=b.patient_id ORDER BY b.id DESC""").fetchall()
    pats=conn.execute("SELECT * FROM patients ORDER BY name").fetchall()
    conn.close()
    return render_template("billing.html", bills=bills, patients=pats)

@app.route("/ai")
def ai():
    if not login_required(): return redirect(url_for("login"))
    conn=get_db(); pats=conn.execute("SELECT * FROM patients ORDER BY name").fetchall(); conn.close()
    return render_template("ai.html", patients=pats)

@app.route("/ai/summary", methods=["POST"])
def ai_summary():
    if not login_required(): return jsonify({"error":"Unauthorized"}),401
    patient_id=request.json.get("patient_id")
    conn=get_db()
    p=conn.execute("SELECT * FROM patients WHERE id=?", (patient_id,)).fetchone()
    records=conn.execute("SELECT * FROM medical_records WHERE patient_id=? ORDER BY id DESC LIMIT 5",(patient_id,)).fetchall()
    conn.close()
    if not p: return jsonify({"error":"Patient not found"}),404
    record_text = "; ".join([r["summary"] for r in records]) or "No previous medical records entered."
    summary = f"""Patient: {p['name']}
Age: {p['age'] or 'Not recorded'}
Gender: {p['gender'] or 'Not recorded'}
Blood Group: {p['blood_group'] or 'Not recorded'}

Recent record notes:
{record_text}

AI note:
This is an administrative/record summary generated from the hospital database.
It is not a diagnosis or medical advice. A qualified healthcare professional
must review the original records before making clinical decisions."""
    return jsonify({"summary":summary})

@app.context_processor
def inject_globals():
    return {"current_year": datetime.now().year}

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
