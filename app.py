from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import date, datetime, timedelta

app = Flask(__name__)
DB_NAME = "fitness.db"

# ================= DAILY GOALS =================
DAILY_GOALS = {
    "calories": 2200,
    "protein": 120
}

# ================= FOOD DATA =================
# (calories, protein, fat, sugar) per unit
FOOD_DATA = {
    "Breakfast": {
        "Idli": (45, 2, 0.2, 0),
        "Dosa (Plain)": (130, 3, 4, 0.5),
        "Masala Dosa": (275, 5, 11, 2),
        "Upma": (140, 3.5, 5, 1),
        "Poha": (165, 3, 6, 2),
        "Tea / Coffee": (90, 2.5, 3, 7)
    },
    "Lunch": {
        "Chapati": (90, 3, 3, 0),
        "Veg Pulao": (150, 3, 5, 0.5),
        "Curd Rice": (130, 4, 6, 1),
        "Aloo Paratha": (240, 5, 10, 1),
        "Chicken Curry": (300, 25, 15, 1)
    },
    "Snacks": {
        "Samosa": (265, 4, 16, 1),
        "Veg Puff": (275, 5, 18, 3),
        "Veg Burger": (400, 10, 15, 7),
        "Bhel Puri": (275, 6, 10, 6)
    },
    "Dinner": {
        "Plain Rice": (130, 2.7, 0.3, 0),
        "Paneer Butter Masala": (265, 10, 20, 3),
        "Rasam": (50, 1, 2, 1.5),
        "Jeera Rice": (160, 3, 5, 0)
    }
}

# ================= DB HELPERS =================
def get_db():
    db = sqlite3.connect(DB_NAME)
    db.row_factory = sqlite3.Row
    return db

def init_db():
    db = get_db()

    db.execute("""
        CREATE TABLE IF NOT EXISTS food_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            meal TEXT,
            food TEXT,
            qty REAL,
            calories REAL,
            protein REAL,
            fat REAL,
            sugar REAL
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS sleep_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT UNIQUE,
            hours REAL,
            quality INTEGER,
            notes TEXT
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS wellbeing_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            activity TEXT,
            minutes INTEGER
        )
    """)

    db.commit()
    db.close()

# ================= UTIL =================
def get_week_dates(selected_date):
    d = datetime.strptime(selected_date, "%Y-%m-%d")
    start = d - timedelta(days=6)
    return [(start + timedelta(days=i)).date().isoformat() for i in range(7)]

# ================= DASHBOARD =================
@app.route("/")
def index():
    selected_date = request.args.get("date", date.today().isoformat())
    week = get_week_dates(selected_date)

    db = get_db()

    totals = db.execute("""
        SELECT 
            COALESCE(SUM(calories),0) cal,
            COALESCE(SUM(protein),0) protein,
            COALESCE(SUM(fat),0) fat,
            COALESCE(SUM(sugar),0) sugar
        FROM food_log WHERE date=?
    """, (selected_date,)).fetchone()

    weekly_cal = []
    weekly_sleep = []
    weekly_wellbeing = []

    for d in week:
        c = db.execute(
            "SELECT COALESCE(SUM(calories),0) FROM food_log WHERE date=?",
            (d,)
        ).fetchone()[0]
        s = db.execute(
            "SELECT hours FROM sleep_log WHERE date=?",
            (d,)
        ).fetchone()
        w = db.execute(
            "SELECT COALESCE(SUM(minutes),0) FROM wellbeing_log WHERE date=?",
            (d,)
        ).fetchone()[0]

        weekly_cal.append(c)
        weekly_sleep.append(s["hours"] if s else 0)
        weekly_wellbeing.append(w)

    db.close()

    return render_template(
        "index.html",
        t=totals,
        goals=DAILY_GOALS,
        selected_date=selected_date,
        week=week,
        weekly_cal=weekly_cal,
        weekly_sleep=weekly_sleep,
        weekly_wellbeing=weekly_wellbeing
    )

# ================= FOOD =================
@app.route("/food", methods=["GET", "POST"])
def food():
    db = get_db()

    selected_date = request.args.get(
        "date",
        request.form.get("date", date.today().isoformat())
    )

    if request.method == "POST":
        meal = request.form["meal"]
        food_item = request.form["food"]
        qty = float(request.form.get("qty", 1))

        cal, pro, fat_, sug = FOOD_DATA[meal][food_item]

        db.execute("""
            INSERT INTO food_log
            (date, meal, food, qty, calories, protein, fat, sugar)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            selected_date,
            meal,
            food_item,
            qty,
            cal * qty,
            pro * qty,
            fat_ * qty,
            sug * qty
        ))

        db.commit()
        return redirect(url_for("food", date=selected_date))

    food_logs = db.execute("""
        SELECT * FROM food_log
        WHERE date = ?
        ORDER BY id DESC
    """, (selected_date,)).fetchall()

    db.close()

    return render_template(
        "food.html",
        food_logs=food_logs,
        food_data=FOOD_DATA,
        selected_date=selected_date
    )


@app.route("/food/delete/<int:id>")
def delete_food(id):
    selected_date = request.args.get("date", date.today().isoformat())
    db = get_db()
    db.execute("DELETE FROM food_log WHERE id=?", (id,))
    db.commit()
    db.close()
    return redirect(url_for("food", date=selected_date))

@app.route("/food/edit/<int:id>", methods=["GET", "POST"])
def edit_food(id):
    db = get_db()
    food = db.execute("SELECT * FROM food_log WHERE id=?", (id,)).fetchone()

    if request.method == "POST":
        db.execute("""
            UPDATE food_log
            SET qty=?, calories=?, protein=?, fat=?, sugar=?
            WHERE id=?
        """, (
            request.form["qty"],
            request.form["calories"],
            request.form["protein"],
            request.form["fat"],
            request.form["sugar"],
            id
        ))
        db.commit()
        db.close()
        return redirect(url_for("food", date=food["date"]))

    db.close()
    return render_template("edit_food.html", f=food)

# ================= SLEEP =================
@app.route("/sleep", methods=["GET", "POST"])
def sleep():
    selected_date = request.args.get("date", date.today().isoformat())
    db = get_db()

    if request.method == "POST":
        db.execute("""
            INSERT INTO sleep_log (date, hours, quality, notes)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET
                hours=excluded.hours,
                quality=excluded.quality,
                notes=excluded.notes
        """, (
            request.form["date"],
            float(request.form["hours"]),
            int(request.form["quality"]),
            request.form.get("notes", "")
        ))

        db.commit()
        db.close()
        return redirect(url_for("sleep", date=request.form["date"]))

    sleep_data = db.execute(
        "SELECT * FROM sleep_log WHERE date=?",
        (selected_date,)
    ).fetchone()

    db.close()

    return render_template(
        "sleep.html",
        sleep=sleep_data,
        selected_date=selected_date
    )

@app.route("/sleep/delete")
def delete_sleep():
    selected_date = request.args.get("date", date.today().isoformat())
    db = get_db()
    db.execute("DELETE FROM sleep_log WHERE date=?", (selected_date,))
    db.commit()
    db.close()
    return redirect(url_for("sleep", date=selected_date))

# ================= WELL-BEING =================
@app.route("/wellbeing", methods=["GET", "POST"])
def wellbeing():
    selected_date = request.args.get("date", date.today().isoformat())
    db = get_db()

    if request.method == "POST":
        db.execute("""
            INSERT INTO wellbeing_log (date, activity, minutes)
            VALUES (?, ?, ?)
        """, (
            request.form["date"],
            request.form["activity"],
            int(request.form["minutes"])
        ))

        db.commit()
        return redirect(url_for("wellbeing", date=request.form["date"]))

    logs = db.execute("""
        SELECT * FROM wellbeing_log
        WHERE date=?
        ORDER BY id DESC
    """, (selected_date,)).fetchall()

    db.close()

    return render_template(
        "wellbeing.html",
        wellbeing_logs=logs,
        selected_date=selected_date
    )

@app.route("/wellbeing/delete/<int:id>")
def delete_wellbeing(id):
    selected_date = request.args.get("date", date.today().isoformat())
    db = get_db()
    db.execute("DELETE FROM wellbeing_log WHERE id=?", (id,))
    db.commit()
    db.close()
    return redirect(url_for("wellbeing", date=selected_date))

# ================= REPORT =================
@app.route("/report")
def report():
    selected_date = request.args.get("date", date.today().isoformat())
    week = get_week_dates(selected_date)

    db = get_db()

    meals = db.execute("""
        SELECT meal,
               SUM(calories) cal,
               SUM(protein) protein,
               SUM(fat) fat,
               SUM(sugar) sugar
        FROM food_log
        WHERE date=?
        GROUP BY meal
    """, (selected_date,)).fetchall()

    weekly_cal, weekly_sleep, weekly_wellbeing = [], [], []

    for d in week:
        weekly_cal.append(
            db.execute("SELECT COALESCE(SUM(calories),0) FROM food_log WHERE date=?", (d,)).fetchone()[0]
        )
        s = db.execute("SELECT hours FROM sleep_log WHERE date=?", (d,)).fetchone()
        weekly_sleep.append(s["hours"] if s else 0)
        weekly_wellbeing.append(
            db.execute("SELECT COALESCE(SUM(minutes),0) FROM wellbeing_log WHERE date=?", (d,)).fetchone()[0]
        )

    db.close()

    return render_template(
        "report.html",
        meals=meals,
        selected_date=selected_date,
        week=week,
        weekly_cal=weekly_cal,
        weekly_sleep=weekly_sleep,
        weekly_wellbeing=weekly_wellbeing
    )

# ================= RUN =================
if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5001)
