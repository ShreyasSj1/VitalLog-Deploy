from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import date

app = Flask(__name__)
DB_NAME = "fitness.db"

# ================= DAILY GOALS =================
DAILY_GOALS = {
    "calories": 2200,
    "protein": 120
}

# ================= FOOD DATA =================
FOOD_DATA = {
    "Breakfast": {
        "Idli": (45, 2, 0.2, 0),
        "Dosa (Plain)": (130, 3, 4, 0.5),
        "Masala Dosa": (275, 5, 11, 2),
        "Vada (Medu)": (150, 4, 9, 0),
        "Bread (White)": (68, 2, 1, 2.5),
        "Jam": (45, 0, 0, 9.5),
        "Butter": (36, 0, 4, 0),
        "Upma": (140, 3.5, 5, 1),
        "Poha": (165, 3, 6, 2),
        "Tea / Coffee": (90, 2.5, 3, 7)
    },
    "Lunch": {
        "Chapati": (90, 3, 3, 0),
        "Chana Masala": (140, 6, 6, 1),
        "Rajma Masala": (130, 6, 5, 1),
        "Veg Pulao": (150, 3, 5, 0.5),
        "Curd Rice": (130, 4, 6, 1),
        "Aloo Paratha": (240, 5, 10, 1)
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


def get_weekly_data(selected_date):
    db = get_db()

    weekly = db.execute("""
        WITH dates AS (
            SELECT date(?) AS d
            UNION ALL SELECT date(d, '-1 day') FROM dates LIMIT 7
        )
        SELECT
            dates.d AS date,
            COALESCE(SUM(food_log.calories), 0) AS calories,
            COALESCE(sleep_log.hours, 0) AS sleep,
            COALESCE(SUM(wellbeing_log.minutes), 0) AS wellbeing
        FROM dates
        LEFT JOIN food_log ON food_log.date = dates.d
        LEFT JOIN sleep_log ON sleep_log.date = dates.d
        LEFT JOIN wellbeing_log ON wellbeing_log.date = dates.d
        GROUP BY dates.d
        ORDER BY dates.d
    """, (selected_date,)).fetchall()

    db.close()
    return weekly


# ================= DASHBOARD =================
@app.route("/")
def index():
    selected_date = request.args.get("date", date.today().isoformat())
    db = get_db()

    # ---- Food totals ----
    food_totals = db.execute("""
        SELECT
            COALESCE(SUM(calories), 0) AS cal,
            COALESCE(SUM(protein), 0) AS protein,
            COALESCE(SUM(fat), 0) AS fat,
            COALESCE(SUM(sugar), 0) AS sugar
        FROM food_log
        WHERE date=?
    """, (selected_date,)).fetchone()

    # ---- Sleep ----
    sleep = db.execute("""
        SELECT hours, quality
        FROM sleep_log
        WHERE date=?
    """, (selected_date,)).fetchone()

    # ---- Well-being ----
    wellbeing = db.execute("""
        SELECT COALESCE(SUM(minutes), 0) AS minutes
        FROM wellbeing_log
        WHERE date=?
    """, (selected_date,)).fetchone()

    weekly = get_weekly_data(selected_date)

    db.close()

    return render_template(
        "index.html",
        t=food_totals,
        sleep=sleep,
        wellbeing=wellbeing,
        weekly=weekly,
        goals=DAILY_GOALS,
        selected_date=selected_date
    )


# ================= FOOD =================
@app.route("/food", methods=["GET", "POST"])
def food():
    selected_date = request.args.get("date", date.today().isoformat())
    db = get_db()

    if request.method == "POST":
        log_date = request.form["date"]
        meal = request.form["meal"]
        food_item = request.form["food"]
        qty = float(request.form.get("qty", 1))

        if food_item == "OTHERS":
            name = request.form["other_name"]
            calories = float(request.form["other_cal"])
            protein = float(request.form["other_protein"])
            fat = float(request.form["other_fat"])
            sugar = float(request.form["other_sugar"])
        else:
            cal, pro, fat_, sug = FOOD_DATA[meal][food_item]
            name = food_item
            calories = cal * qty
            protein = pro * qty
            fat = fat_ * qty
            sugar = sug * qty

        db.execute("""
            INSERT INTO food_log
            (date, meal, food, qty, calories, protein, fat, sugar)
            VALUES (?,?,?,?,?,?,?,?)
        """, (log_date, meal, name, qty, calories, protein, fat, sugar))

        db.commit()
        db.close()
        return redirect(url_for("food", date=log_date))

    food_logs = db.execute("""
        SELECT * FROM food_log
        WHERE date=?
        ORDER BY id DESC
    """, (selected_date,)).fetchall()

    db.close()
    return render_template(
        "food.html",
        food_logs=food_logs,
        food_data=FOOD_DATA,
        selected_date=selected_date
    )

# ================= DELETE FOOD =================
@app.route("/food/delete/<int:id>")
def delete_food(id):
    selected_date = request.args.get("date", date.today().isoformat())
    db = get_db()
    db.execute("DELETE FROM food_log WHERE id=?", (id,))
    db.commit()
    db.close()
    return redirect(url_for("food", date=selected_date))

# ================= EDIT FOOD =================
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
            float(request.form["qty"]),
            float(request.form["calories"]),
            float(request.form["protein"]),
            float(request.form["fat"]),
            float(request.form["sugar"]),
            id
        ))
        db.commit()
        db.close()
        return redirect(url_for("food", date=food["date"]))

    db.close()
    return render_template("edit_food.html", f=food)

# ================= REPORT =================
@app.route("/report")
def report():
    selected_date = request.args.get("date", date.today().isoformat())
    db = get_db()

    meals = db.execute("""
        SELECT 
            meal,
            SUM(calories) AS cal,
            SUM(protein) AS protein,
            SUM(fat) AS fat,
            SUM(sugar) AS sugar
        FROM food_log
        WHERE date = ?
        GROUP BY meal
        ORDER BY meal
    """, (selected_date,)).fetchall()

    sleep = db.execute("""
        SELECT hours, quality, notes
        FROM sleep_log
        WHERE date=?
    """, (selected_date,)).fetchone()

    wellbeing_logs = db.execute("""
        SELECT activity, minutes
        FROM wellbeing_log
        WHERE date=?
    """, (selected_date,)).fetchall()

    total_wellbeing = sum(w["minutes"] for w in wellbeing_logs)

    weekly = get_weekly_data(selected_date)

    db.close()

    return render_template(
        "report.html",
        meals=meals,
        sleep=sleep,
        wellbeing_logs=wellbeing_logs,
        total_wellbeing=total_wellbeing,
        weekly=weekly,
        selected_date=selected_date
)



# ================= SLEEP =================
@app.route("/sleep", methods=["GET", "POST"])
def sleep():
    selected_date = request.args.get("date", date.today().isoformat())
    db = get_db()

    if request.method == "POST":
        sleep_date = request.form["date"]
        hours = float(request.form["hours"])
        quality = int(request.form["quality"])
        notes = request.form.get("notes", "")

        db.execute("""
            INSERT INTO sleep_log (date, hours, quality, notes)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET
                hours=excluded.hours,
                quality=excluded.quality,
                notes=excluded.notes
        """, (sleep_date, hours, quality, notes))

        db.commit()
        db.close()
        return redirect(url_for("sleep", date=sleep_date))

    sleep_data = db.execute("""
        SELECT * FROM sleep_log WHERE date=?
    """, (selected_date,)).fetchone()

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

# ================= WELLBEING =================
@app.route("/wellbeing", methods=["GET", "POST"])
def wellbeing():
    selected_date = request.args.get("date", date.today().isoformat())
    db = get_db()

    if request.method == "POST":
        log_date = request.form["date"]
        activity = request.form["activity"]
        minutes = int(request.form["minutes"])

        if activity == "OTHERS":
            activity = request.form["other_activity"]

        db.execute("""
            INSERT INTO wellbeing_log (date, activity, minutes)
            VALUES (?, ?, ?)
        """, (log_date, activity, minutes))

        db.commit()
        db.close()
        return redirect(url_for("wellbeing", date=log_date))

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

# ================= START =================

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5001, debug=True)
