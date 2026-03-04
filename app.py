from flask import Flask, render_template, request, redirect, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
with app.app_context():
    init_db()
app.secret_key = "secret123"


# ------------------ DATABASE CONNECTION ------------------
def get_db_connection():
    conn = sqlite3.connect("db.sqlite")
    conn.row_factory = sqlite3.Row
    return conn


# ------------------ CREATE TABLES AUTOMATICALLY ------------------
def init_db():
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'user'
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            date TEXT,
            venue TEXT,
            price REAL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            event_id INTEGER,
            payment_status TEXT DEFAULT 'Pending',
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(event_id) REFERENCES events(id)
        )
    """)

    conn.commit()
    conn.close()


init_db()


# ------------------ HOME ------------------
@app.route("/")
def home():
    return redirect("/events")


# ------------------ REGISTER ------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = generate_password_hash(request.form["password"])

        conn = get_db_connection()
        conn.execute(
            "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
            (name, email, password)
        )
        conn.commit()
        conn.close()

        return redirect("/login")

    return render_template("register.html")


# ------------------ LOGIN ------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE email=?",
            (email,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["role"] = user["role"]
            return redirect("/events")

    return render_template("login.html")


# ------------------ LOGOUT ------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# ------------------ EVENTS ------------------
@app.route("/events")
def events():
    conn = get_db_connection()
    events = conn.execute("SELECT * FROM events").fetchall()
    conn.close()
    return render_template("events.html", events=events)


# ------------------ CREATE EVENT (ADMIN ONLY) ------------------
@app.route("/create-event", methods=["GET", "POST"])
def create_event():
    if session.get("role") != "admin":
        return redirect("/login")

    if request.method == "POST":
        title = request.form["title"]
        description = request.form["description"]
        date = request.form["date"]
        venue = request.form["venue"]
        price = request.form["price"]

        conn = get_db_connection()
        conn.execute(
            "INSERT INTO events (title, description, date, venue, price) VALUES (?, ?, ?, ?, ?)",
            (title, description, date, venue, price)
        )
        conn.commit()
        conn.close()

        return redirect("/events")

    return render_template("create_event.html")


# ------------------ BOOK EVENT ------------------
@app.route("/confirm-booking/<int:event_id>")
def confirm_booking(event_id):
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()
    conn.execute(
        "INSERT INTO bookings (user_id, event_id, payment_status) VALUES (?, ?, ?)",
        (session["user_id"], event_id, "Paid")
    )
    conn.commit()
    conn.close()

    return redirect("/my-bookings")


# ------------------ MY BOOKINGS ------------------
@app.route("/my-bookings")
def my_bookings():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()
    bookings = conn.execute("""
        SELECT events.title, events.date, events.venue
        FROM bookings
        JOIN events ON bookings.event_id = events.id
        WHERE bookings.user_id = ?
    """, (session["user_id"],)).fetchall()
    conn.close()

    return render_template("my_bookings.html", bookings=bookings)


# ------------------ ADMIN VIEW BOOKINGS ------------------
@app.route("/admin/bookings")
def admin_bookings():
    if session.get("role") != "admin":
        return redirect("/login")

    conn = get_db_connection()
    bookings = conn.execute("""
        SELECT users.name, events.title, bookings.payment_status
        FROM bookings
        JOIN users ON bookings.user_id = users.id
        JOIN events ON bookings.event_id = events.id
    """).fetchall()
    conn.close()

    return render_template("admin_bookings.html", bookings=bookings)


# ------------------ MAIN ------------------
if __name__ == "__main__":

    app.run(host="0.0.0.0", port=5000)
