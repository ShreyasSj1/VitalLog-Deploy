from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import date

app = Flask(__name__)
DB_NAME = "fitness.db"

DAILY_GOALS = {
    "calories": 2200,
    "protein": 120
}

# =====================================================
# FOOD DATABASE (MID VALUES FROM YOUR LIST)
# =====================================================

FOOD_DATA = {

    "Breakfast": {
        "Idli": {"cal": 45, "protein": 2.0, "fat": 0.2, "sugar": 0},
        "Dosa (Plain)": {"cal": 128, "protein": 3.0, "fat": 4.0, "sugar": 0.5},
        "Masala Dosa": {"cal": 275, "protein": 5.0, "fat": 11.0, "sugar": 2.0},
        "Vada (Medu)": {"cal": 150, "protein": 4.0, "fat": 9.0, "sugar": 0},
        "Bread (White)": {"cal": 68, "protein": 2.0, "fat": 1.0, "sugar": 2.5},
        "Jam": {"cal": 45, "protein": 0.0, "fat": 0.0, "sugar": 9.5},
        "Butter": {"cal": 36, "protein": 0.0, "fat": 4.0, "sugar": 0},
        "Uppitu (Upma)": {"cal": 140, "protein": 3.5, "fat": 5.0, "sugar": 1.0},
        "Poha": {"cal": 165, "protein": 3.0, "fat": 6.0, "sugar": 2.0},
        "Puliogre / Tomato Rice": {"cal": 170, "protein": 3.0, "fat": 7.0, "sugar": 2.0},
        "Bele Bath": {"cal": 170, "protein": 5.0, "fat": 6.0, "sugar": 2.0},
        "Poori": {"cal": 130, "protein": 2.0, "fat": 7.0, "sugar": 0},
        "Potato Sabji (Poori)": {"cal": 130, "protein": 2.0, "fat": 5.0, "sugar": 1.0},
        "Tea / Coffee": {"cal": 90, "protein": 2.5, "fat": 3.0, "sugar": 7.5},
    },

    "Lunch": {
        "Chapati": {"cal": 90, "protein": 3.0, "fat": 3.0, "sugar": 0},
        "Chana Masala": {"cal": 140, "protein": 6.0, "fat": 6.0, "sugar": 1.0},
        "Rajma Masala": {"cal": 130, "protein": 6.0, "fat": 5.0, "sugar": 1.0},
        "Mixed Veg Sabji": {"cal": 110, "protein": 2.5, "fat": 6.0, "sugar": 2.0},
        "Veg Pulao": {"cal": 150, "protein": 3.0, "fat": 5.0, "sugar": 0.5},
        "Sambar (Veg)": {"cal": 90, "protein": 4.0, "fat": 3.0, "sugar": 4.0},
        "Curd Rice": {"cal": 130, "protein": 4.0, "fat": 6.0, "sugar": 1.0},
        "Pickle": {"cal": 28, "protein": 0.2, "fat": 2.5, "sugar": 1.0},
        "Potato Chips": {"cal": 160, "protein": 2.0, "fat": 10.0, "sugar": 0.5},
        "Aloo Paratha": {"cal": 240, "protein": 5.0, "fat": 10.0, "sugar": 1.0},
        "Potato Wedges": {"cal": 300, "protein": 4.0, "fat": 15.0, "sugar": 0.5},
    },

    "Snacks": {
        "Gobi Manchurian": {"cal": 235, "protein": 4.0, "fat": 12.0, "sugar": 5.0},
        "Vada Pav": {"cal": 290, "protein": 7.0, "fat": 12.0, "sugar": 4.0},
        "Veg Puff": {"cal": 275, "protein": 5.0, "fat": 18.0, "sugar": 3.0},
        "Samosa": {"cal": 265, "protein": 4.0, "fat": 16.0, "sugar": 1.0},
        "Veg Burger": {"cal": 400, "protein": 10.0, "fat": 15.0, "sugar": 7.0},
        "Cake Slice": {"cal": 225, "protein": 3.0, "fat": 10.0, "sugar": 21.5},
        "Sandwich (Veg)": {"cal": 235, "protein": 6.0, "fat": 8.0, "sugar": 3.0},
        "Bhel Puri": {"cal": 275, "protein": 6.0, "fat": 10.0, "sugar": 6.5},
        "Masala Puri": {"cal": 325, "protein": 8.0, "fat": 12.0, "sugar": 2.0},
    },

    "Dinner": {
        "Soya Sabji": {"cal": 150, "protein": 12.0, "fat": 6.0, "sugar": 1.0},
        "Paneer Butter Masala": {"cal": 265, "protein": 10.0, "fat": 20.0, "sugar": 3.0},
        "Aloo Sabji": {"cal": 150, "protein": 2.0, "fat": 6.0, "sugar": 1.0},
        "Rice Bath": {"cal": 160, "protein": 3.0, "fat": 6.0, "sugar": 1.0},
        "Plain Rice": {"cal": 130, "protein": 2.7, "fat": 0.3, "sugar": 0},
        "Rasam": {"cal": 50, "protein": 1.0, "fat": 2.0, "sugar": 1.5},
        "Jeera Rice": {"cal": 160, "protein": 3.0, "fat": 5.0, "sugar": 0},
        "Pav Bhaji": {"cal": 425, "protein": 10.0, "fat": 15.0, "sugar": 6.0},
        "Chole Bhature": {"cal": 475, "protein": 12.0, "fat": 22.0, "sugar": 2.0},
    }
}

# =====================================================
# DATABASE
# =====================================================

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

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
    db.commit()
    db.close()

# =====================================================
# ROUTES
# =====================================================

@app.route("/")
def index():
    today = date.today().isoformat()
    db = get_db()

    totals = db.execute("""
        SELECT 
            SUM(calories) AS cal,
            SUM(protein) AS protein,
            SUM(fat) AS fat,
            SUM(sugar) AS sugar
        FROM food_log
        WHERE date=?
    """, (today,)).fetchone()

    db.close()

    return render_template(
        "index.html",
        t=totals,
        goals=DAILY_GOALS
    )


@app.route("/food", methods=["GET", "POST"])
def food():
    today = date.today().isoformat()
    db = get_db()

    if request.method == "POST":
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
            item = FOOD_DATA[meal][food_item]
            name = food_item
            calories = item["cal"] * qty
            protein = item["protein"] * qty
            fat = item["fat"] * qty
            sugar = item["sugar"] * qty

        db.execute("""
            INSERT INTO food_log VALUES (NULL,?,?,?,?,?,?,?,?)
        """, (
            today, meal, name, qty, calories, protein, fat, sugar
        ))
        db.commit()

    # Fetch today's logged foods
    food_logs = db.execute("""
        SELECT id, meal, food, qty, calories, protein, fat, sugar
        FROM food_log
        WHERE date=?
        ORDER BY id DESC
    """, (today,)).fetchall()

    # Fetch totals
    totals = db.execute("""
        SELECT 
            SUM(calories) AS cal,
            SUM(protein) AS protein,
            SUM(fat) AS fat,
            SUM(sugar) AS sugar
        FROM food_log
        WHERE date=?
    """, (today,)).fetchone()

    db.close()

    return render_template(
        "food.html",
        food_data=FOOD_DATA,
        food_logs=food_logs,
        totals=totals
    )

@app.route("/food/delete/<int:id>")
def delete_food(id):
    db = get_db()
    db.execute("DELETE FROM food_log WHERE id=?", (id,))
    db.commit()
    db.close()
    return redirect(url_for("food"))


@app.route("/food/edit/<int:id>", methods=["GET", "POST"])
def edit_food(id):
    db = get_db()

    if request.method == "POST":
        qty = float(request.form["qty"])
        calories = float(request.form["calories"])
        protein = float(request.form["protein"])
        fat = float(request.form["fat"])
        sugar = float(request.form["sugar"])

        db.execute("""
            UPDATE food_log
            SET qty=?, calories=?, protein=?, fat=?, sugar=?
            WHERE id=?
        """, (qty, calories, protein, fat, sugar, id))
        db.commit()
        db.close()
        return redirect(url_for("food"))

    item = db.execute(
        "SELECT * FROM food_log WHERE id=?", (id,)
    ).fetchone()
    db.close()

    return render_template("edit_food.html", item=item)

@app.route("/report")
def report():
    today = date.today().isoformat()
    db = get_db()

    meals = db.execute("""
        SELECT meal,
               SUM(calories) AS cal,
               SUM(protein) AS protein,
               SUM(fat) AS fat,
               SUM(sugar) AS sugar
        FROM food_log
        WHERE date=?
        GROUP BY meal
    """, (today,)).fetchall()

    totals = db.execute("""
        SELECT
            SUM(calories) AS cal,
            SUM(protein) AS protein,
            SUM(fat) AS fat,
            SUM(sugar) AS sugar
        FROM food_log
        WHERE date=?
    """, (today,)).fetchone()

    db.close()

    return render_template(
    "report.html",
    meals=meals,
    totals=totals,
    goals=DAILY_GOALS
)


# =====================================================
# START APP
# =====================================================

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
