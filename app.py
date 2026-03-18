from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import date, datetime, timedelta

app = Flask(__name__)
DB_NAME = "fitness.db"

# ================= DAILY GOALS =================
GOALS = {
    "calories": 1500,
    "protein": 80,
    "fat": 40,
    "sugar": 20
}

# ================= FOOD DATA =================
# (calories, protein, fat, sugar) per unit/serving
FOOD_DATA = {
    "Breakfast": {
        "Idli": (45, 2, 0.2, 0),
        "Dosa (Plain)": (130, 3, 4, 0.5),
        "Masala Dosa": (275, 5, 11, 2),
        "Upma": (140, 3.5, 5, 1),
        "Poha": (165, 3, 6, 2),
        "Pongal": (180, 6, 7, 1),
        "Vada (Medu)": (150, 4, 9, 0),
        "Bread (White)": (68, 2, 1, 2.5),
        "Butter": (36, 0, 4, 0),
        "Jam": (45, 0, 0, 9.5),
        "Omelette": (120, 6, 9, 1),
        "Boiled Eggs": (78, 6, 5, 0),
        "Milk (200ml)": (120, 6, 6, 10),
        "Tea / Coffee": (90, 2.5, 3, 7)
    },
    "Lunch": {
        "Chapati": (90, 3, 3, 0),
        "Rice (Cooked)": (130, 2.7, 0.3, 0),
        "Veg Pulao": (150, 3, 5, 0.5),
        "Curd Rice": (130, 4, 6, 1),
        "Aloo Paratha": (240, 5, 10, 1),
        "Dal Tadka": (180, 9, 6, 1),
        "Rajma Masala": (130, 6, 5, 1),
        "Chana Masala": (140, 6, 6, 1),
        "Paneer Curry": (260, 12, 18, 2),
        "Chicken Curry": (300, 25, 15, 1),
        "Chicken Biryani": (350, 20, 12, 2),
        "Fish Curry": (220, 22, 10, 0),
        "Curd (Plain)": (60, 3, 3, 2)
    },
    "Pre/Post Workout":{
        "Protein Shake (Milk)": (350, 42, 2, 3),
        "Protein Shake (Water)" : (150, 30, 1, 2),
        "Banana": (105, 1, 0.4, 14),
        "Peanut Butter Sandwich": (380, 10, 16, 8),
        "Greek Yogurt": (130, 23, 2, 6)
    },
    "Snacks": {
        "Samosa": (265, 4, 16, 1),
        "Veg Puff": (275, 5, 18, 3),
        "Veg Burger": (400, 10, 15, 7),
        "Bhel Puri": (275, 6, 10, 6),
        "Pani Puri": (180, 4, 6, 5),
        "Sandwich (Veg)": (230, 7, 8, 4),
        "French Fries": (312, 4, 15, 0),
        "Biscuits": (70, 1, 3, 5),
        "Fruit Bowl": (120, 2, 0.5, 15),
        "Protein Bar": (200, 15, 7, 5),
        "Nuts (Handful)": (170, 6, 14, 2)
    },
    "Dinner": {
        "Chapati": (90, 3, 3, 0),
        "Plain Rice": (130, 2.7, 0.3, 0),
        "Jeera Rice": (160, 3, 5, 0),
        "Rasam": (50, 1, 2, 1.5),
        "Sambar": (150, 6, 5, 3),
        "Paneer Curry": (260, 12, 18, 2),
        "Chicken Curry": (300, 25, 15, 1),
        "Grilled Chicken": (220, 35, 5, 0),
        "Egg Curry": (190, 12, 14, 1),
        "Vegetable Stir Fry": (120, 4, 6, 3),
        "Soup (Veg)": (90, 3, 2, 4),
        "Salad": (80, 2, 3, 4)
    }
}

# ================= DB HELPERS =================
def get_db():
    db = sqlite3.connect(DB_NAME)
    db.row_factory = sqlite3.Row
    return db

def init_db():
    db = get_db()

    with open('schema.sql') as f:
        db.executescript(f.read())

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
            COALESCE(SUM(calories),0) AS cal,
            COALESCE(SUM(protein),0) AS protein,
            COALESCE(SUM(fat),0) AS fat,
            COALESCE(SUM(sugar),0) AS sugar
        FROM food_log WHERE date=?
    """, (selected_date,)).fetchone()

    gym_total = db.execute("SELECT COALESCE(SUM(calories),0) FROM gym_log WHERE date=?", (selected_date,)).fetchone()[0]

    weekly_cal, weekly_sleep, weekly_wellbeing, weekly_gym = [], [], [], []

    for d in week:
        weekly_cal.append(
            db.execute("SELECT COALESCE(SUM(calories),0) FROM food_log WHERE date=?", (d,)).fetchone()[0]
        )
        s = db.execute("SELECT hours FROM sleep_log WHERE date=?", (d,)).fetchone()
        weekly_sleep.append(s["hours"] if s else 0)
        weekly_wellbeing.append(
            db.execute("SELECT COALESCE(SUM(minutes),0) FROM wellbeing_log WHERE date=?", (d,)).fetchone()[0]
        )
        weekly_gym.append(
            db.execute("SELECT COALESCE(SUM(calories),0) FROM gym_log WHERE date=?", (d,)).fetchone()[0]
        )

    # Calculate daily workout duration
    gym_duration = db.execute("SELECT COALESCE(SUM(duration),0) FROM gym_log WHERE date=?", (selected_date,)).fetchone()[0]

    # Health Score Calculation
    score = 100
    reasons = []
    
    # 1. Calories (Intake vs Goal)
    cal_intake = totals["cal"]
    cal_goal = GOALS["calories"]
    if cal_intake > cal_goal:
        penalty = min(20, int((cal_intake - cal_goal) / 20))
        score -= penalty
        if penalty > 5: reasons.append(("✖ Calorie limit exceeded", "bad"))
    elif cal_intake > 0:
        reasons.append(("✔ Calorie target healthy", "good"))

    # 2. Protein
    if totals["protein"] >= GOALS["protein"]:
        reasons.append(("✔ Protein goal met", "good"))
    else:
        score -= 10
        reasons.append(("✖ Protein intake low", "bad"))

    # 3. Sugar
    if totals["sugar"] > GOALS["sugar"]:
        score -= 15
        reasons.append(("✖ Sugar limit exceeded", "bad"))
    else:
        reasons.append(("✔ Sugar within limit", "good"))

    # 4. Workout
    if gym_total > 0:
        score += 5 # Bonus for working out
        reasons.append(("✔ Workout completed", "good"))
    else:
        score -= 5
        reasons.append(("✖ No workout logged", "bad"))

    # 5. Sleep
    s = db.execute("SELECT hours FROM sleep_log WHERE date=?", (selected_date,)).fetchone()
    if s:
        if s["hours"] >= 7:
            reasons.append(("✔ Healthy sleep duration", "good"))
        else:
            score -= 10
            reasons.append(("✖ Short sleep duration", "bad"))
    else:
        score -= 5
        reasons.append(("✖ No sleep data", "bad"))

    score = max(0, min(100, score))

    db.close()

    return render_template(
        "index.html",
        selected_date=selected_date,
        goals=GOALS,
        total_calories=totals["cal"],
        total_protein=totals["protein"],
        total_fat=totals["fat"],
        total_sugar=totals["sugar"],
        gym_calories=gym_total,
        gym_duration=gym_duration,
        net_calories=totals["cal"] - gym_total,
        health_score=score,
        health_reasons=reasons,
        week=week,
        weekly_cal=weekly_cal,
        weekly_sleep=weekly_sleep,
        weekly_wellbeing=weekly_wellbeing,
        weekly_gym=weekly_gym
    )

# ================= FOOD =================
@app.route("/food", methods=["GET", "POST"])
def food():
    db = get_db()
    selected_date = request.args.get("date", request.form.get("date", date.today().isoformat()))

    if request.method == "POST":
        meal = request.form["meal"]
        food_item = request.form["food"]
        qty = float(request.form.get("qty", 1))

        if food_item == "OTHERS":
            name = request.form["other_name"]
            calories = float(request.form["other_calories"]) * qty
            protein = float(request.form["other_protein"]) * qty
            fat = float(request.form["other_fat"]) * qty
            sugar = float(request.form["other_sugar"]) * qty
        else:
            base = FOOD_DATA[meal][food_item]
            name = food_item
            calories, protein, fat, sugar = [x * qty for x in base]

        db.execute("""
            INSERT INTO food_log
            (date, meal, food, qty, calories, protein, fat, sugar)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (selected_date, meal, name, qty, calories, protein, fat, sugar))

        db.commit()
        db.close()
        return redirect(url_for("food", date=selected_date))

    food_logs = db.execute(
        "SELECT * FROM food_log WHERE date=? ORDER BY id DESC",
        (selected_date,)
    ).fetchall()

    db.close()
    return render_template("food.html", food_logs=food_logs, food_data=FOOD_DATA, selected_date=selected_date)

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
    return render_template("sleep.html", sleep=sleep_data, selected_date=selected_date)

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
        activity = request.form["activity"]
        if activity == "OTHERS":
            activity = request.form.get("other_activity", "Other")

        db.execute("""
            INSERT INTO wellbeing_log (date, activity, minutes)
            VALUES (?, ?, ?)
        """, (
            request.form["date"],
            activity,
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
    return render_template("wellbeing.html", wellbeing_logs=logs, selected_date=selected_date)

@app.route("/wellbeing/delete/<int:id>")
def delete_wellbeing(id):
    selected_date = request.args.get("date", date.today().isoformat())
    db = get_db()
    db.execute("DELETE FROM wellbeing_log WHERE id=?", (id,))
    db.commit()
    db.close()
    return redirect(url_for("wellbeing", date=selected_date))

# ================= GYM =================
@app.route("/gym", methods=["GET", "POST"])
def gym():
    selected_date = request.args.get("date", date.today().isoformat())
    db = get_db()

    if request.method == "POST":
        intensity = request.form.get("intensity", "Medium")
        
        # Safely parse numeric inputs that might come in as empty strings
        try:
            sets = int(request.form.get("sets") or 0)
        except ValueError:
            sets = 0
            
        try:
            reps = int(request.form.get("reps") or 0)
        except ValueError:
            reps = 0
            
        try:
            weight = float(request.form.get("weight") or 0)
        except ValueError:
            weight = 0
        
        # New Rep-based logic
        # Factors based on muscle group effort
        muscle_factors = {
            "Legs": 1.25, 
            "Back": 1.2, 
            "Chest": 1.1, 
            "Shoulders": 1.0, 
            "Arms": 0.8, 
            "Core": 0.9
        }
        muscle = request.form["muscle"]
        muscle_factor = muscle_factors.get(muscle, 1.0)
        
        # Intensity multiplier
        intensity_map = {"Easy": 0.8, "Medium": 1.0, "Hard": 1.3, "Extreme": 1.6}
        intensity_val = intensity_map.get(intensity, 1.0)

        # Bodyweight adjustment: treat 0kg as 50kg for calorie work estimation
        eff_weight = weight if weight > 0 else 50
        
        # Formula: Work-based estimation (Reps * Sets * Weight * Constant * Factors)
        # Constant 0.04 represents calories per kg moved in typical gym range
        calories = (sets * reps * eff_weight * 0.04) * muscle_factor * intensity_val

        db.execute("""
            INSERT INTO gym_log (date, muscle, exercise, sets, reps, weight, intensity, duration, calories)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            request.form.get("date", selected_date),
            muscle,
            request.form.get("exercise", ""),
            sets,
            reps,
            weight,
            intensity,
            0, # Duration removed
            calories
        ))
        db.commit()
        return redirect(url_for("gym", date=request.form.get("date", selected_date)))

    logs = db.execute("""
        SELECT * FROM gym_log
        WHERE date=?
        ORDER BY id DESC
    """, (selected_date,)).fetchall()
    
    # Auto-calculate gym streak (consecutive days)
    streak = 0
    all_dates = db.execute("SELECT DISTINCT date FROM gym_log ORDER BY date DESC").fetchall()
    dates = [d["date"] for d in all_dates]
    
    current = date.today()
    if dates and (dates[0] == current.isoformat() or dates[0] == (current - timedelta(days=1)).isoformat()):
        streak = 1
        check_date = datetime.strptime(dates[0], "%Y-%m-%d").date()
        for i in range(1, len(dates)):
            if dates[i] == (check_date - timedelta(days=1)).isoformat():
                streak += 1
                check_date -= timedelta(days=1)
            else:
                break
                
    # Get last workout for "Repeat Last"
    last_workout = db.execute("SELECT * FROM gym_log ORDER BY id DESC LIMIT 1").fetchone()

    db.close()
    return render_template("gym.html", gym_logs=logs, selected_date=selected_date, streak=streak, last_workout=last_workout)

@app.route("/gym/delete/<int:id>")
def delete_gym(id):
    selected_date = request.args.get("date", date.today().isoformat())
    db = get_db()
    db.execute("DELETE FROM gym_log WHERE id=?", (id,))
    db.commit()
    db.close()
    return redirect(url_for("gym", date=selected_date))

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

    weekly_cal, weekly_sleep, weekly_wellbeing, weekly_gym = [], [], [], []

    for d in week:
        weekly_cal.append(
            db.execute("SELECT COALESCE(SUM(calories),0) FROM food_log WHERE date=?", (d,)).fetchone()[0]
        )
        s = db.execute("SELECT hours FROM sleep_log WHERE date=?", (d,)).fetchone()
        weekly_sleep.append(s["hours"] if s else 0)
        weekly_wellbeing.append(
            db.execute("SELECT COALESCE(SUM(minutes),0) FROM wellbeing_log WHERE date=?", (d,)).fetchone()[0]
        )
        weekly_gym.append(
            db.execute("SELECT COALESCE(SUM(calories),0) FROM gym_log WHERE date=?", (d,)).fetchone()[0]
        )

    gym_logs = db.execute("SELECT * FROM gym_log WHERE date=?", (selected_date,)).fetchall()
    gym_total = db.execute("SELECT COALESCE(SUM(calories),0) FROM gym_log WHERE date=?", (selected_date,)).fetchone()[0]

    db.close()
    return render_template(
        "report.html",
        meals=meals,
        gym_logs=gym_logs,
        gym_total=gym_total,
        selected_date=selected_date,
        week=week,
        weekly_cal=weekly_cal,
        weekly_sleep=weekly_sleep,
        weekly_wellbeing=weekly_wellbeing,
        weekly_gym=weekly_gym
    )

# ================= RUN =================
if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5002)
