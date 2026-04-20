import os
from datetime import date, datetime, timedelta
from flask import Blueprint, request, jsonify, render_template, redirect, url_for, abort, flash
from flask_login import login_required, current_user
import groq
from sqlalchemy import func

from extensions import db
from models import FoodLog, GymLog, SleepLog, WellbeingLog, User
from utils import normalize_selected_date, get_week_dates, parse_optional_float
from constants import GOALS, FOOD_DATA, CARDIO_EXERCISES
from config import Config

dashboard_bp = Blueprint("dashboard", __name__)

GROQ_API_KEY = Config.GROQ_API_KEY
groq_client = None
if GROQ_API_KEY:
    groq_client = groq.Groq(api_key=GROQ_API_KEY)

def is_cardio_exercise(exercise_name):
    return exercise_name in CARDIO_EXERCISES

def is_admin_user():
    return (getattr(current_user, "role", "") or "").lower() == "admin"

@dashboard_bp.route("/health")
def health():
    return {"ok": True, "status": "healthy"}, 200

@dashboard_bp.route("/")
@login_required
def index():
    selected_date = normalize_selected_date(request.args.get("date"))
    week = get_week_dates(selected_date)

    totals = db.session.query(
        func.coalesce(func.sum(FoodLog.calories), 0).label('cal'),
        func.coalesce(func.sum(FoodLog.protein), 0).label('protein'),
        func.coalesce(func.sum(FoodLog.fat), 0).label('fat'),
        func.coalesce(func.sum(FoodLog.sugar), 0).label('sugar')
    ).filter(FoodLog.user_id == current_user.id, FoodLog.date == selected_date).first()

    gym_total = db.session.query(func.coalesce(func.sum(GymLog.calories), 0)) \
        .filter(GymLog.user_id == current_user.id, GymLog.date == selected_date).scalar() or 0

    weekly_cal, weekly_sleep, weekly_wellbeing, weekly_gym = [], [], [], []

    for day_value in week:
        cal = db.session.query(func.coalesce(func.sum(FoodLog.calories), 0)) \
            .filter(FoodLog.user_id == current_user.id, FoodLog.date == day_value).scalar() or 0
        weekly_cal.append(cal)
        
        sleep_row = SleepLog.query.filter_by(user_id=current_user.id, date=day_value).first()
        weekly_sleep.append(sleep_row.hours if sleep_row else 0)
        
        wb = db.session.query(func.coalesce(func.sum(WellbeingLog.minutes), 0)) \
            .filter(WellbeingLog.user_id == current_user.id, WellbeingLog.date == day_value).scalar() or 0
        weekly_wellbeing.append(wb)
        
        gym_cal = db.session.query(func.coalesce(func.sum(GymLog.calories), 0)) \
            .filter(GymLog.user_id == current_user.id, GymLog.date == day_value).scalar() or 0
        weekly_gym.append(gym_cal)

    gym_duration = db.session.query(func.coalesce(func.sum(GymLog.duration), 0)) \
        .filter(GymLog.user_id == current_user.id, GymLog.date == selected_date).scalar() or 0

    score = 100
    reasons = []

    cal_intake = totals.cal
    cal_goal = GOALS["calories"]
    if cal_intake > cal_goal:
        penalty = min(20, int((cal_intake - cal_goal) / 20))
        score -= penalty
        if penalty > 5:
            reasons.append(("Calorie limit exceeded", "bad"))
    elif cal_intake > 0:
        reasons.append(("Calorie target healthy", "good"))

    if totals.protein >= GOALS["protein"]:
        reasons.append(("Protein goal met", "good"))
    else:
        score -= 10
        reasons.append(("Protein intake low", "bad"))

    if totals.sugar > GOALS["sugar"]:
        score -= 15
        reasons.append(("Sugar limit exceeded", "bad"))
    else:
        reasons.append(("Sugar within limit", "good"))

    if gym_total > 0:
        score += 5
        reasons.append(("Workout completed", "good"))
    else:
        score -= 5
        reasons.append(("No workout logged", "bad"))

    sleep_row = SleepLog.query.filter_by(user_id=current_user.id, date=selected_date).first()
    if sleep_row:
        if sleep_row.hours >= 7:
            reasons.append(("Healthy sleep duration", "good"))
        else:
            score -= 10
            reasons.append(("Short sleep duration", "bad"))
    else:
        score -= 5
        reasons.append(("No sleep data", "bad"))

    score = max(0, min(100, score))

    return render_template(
        "index.html",
        active_page="dashboard",
        selected_date=selected_date,
        goals=GOALS,
        total_calories=totals.cal,
        total_protein=totals.protein,
        total_fat=totals.fat,
        total_sugar=totals.sugar,
        gym_calories=gym_total,
        gym_duration=gym_duration,
        net_calories=totals.cal - gym_total,
        health_score=score,
        health_reasons=reasons,
        week=week,
        weekly_cal=weekly_cal,
        weekly_sleep=weekly_sleep,
        weekly_wellbeing=weekly_wellbeing,
        weekly_gym=weekly_gym,
        max_date=date.today().isoformat(),
    )


@dashboard_bp.route("/food", methods=["GET", "POST"])
@login_required
def food():
    selected_date = normalize_selected_date(request.args.get("date", request.form.get("date")))

    if request.method == "POST":
        meal = request.form["meal"]
        food_item = request.form["food"]
        try:
            qty = float(request.form.get("qty", 1))
            if qty <= 0:
                raise ValueError
        except (TypeError, ValueError):
            flash("Quantity must be a valid number greater than zero.")
            return redirect(url_for("dashboard.food", date=selected_date))

        if food_item == "OTHERS":
            name = (request.form.get("other_name") or "").strip() or "Other"
            calories = (parse_optional_float(request.form.get("other_calories")) or 0.0) * qty
            protein = (parse_optional_float(request.form.get("other_protein")) or 0.0) * qty
            fat = (parse_optional_float(request.form.get("other_fat")) or 0.0) * qty
            sugar = (parse_optional_float(request.form.get("other_sugar")) or 0.0) * qty
        else:
            if meal not in FOOD_DATA or food_item not in FOOD_DATA[meal]:
                flash("Invalid meal or food selection.")
                return redirect(url_for("dashboard.food", date=selected_date))

            base = FOOD_DATA[meal][food_item]
            name = food_item
            calories, protein, fat, sugar = [value * qty for value in base]

        log_entry = FoodLog(
            user_id=current_user.id,
            date=selected_date,
            meal=meal,
            food=name,
            qty=qty,
            calories=calories,
            protein=protein,
            fat=fat,
            sugar=sugar
        )
        db.session.add(log_entry)
        db.session.commit()
        return redirect(url_for("dashboard.food", date=selected_date))

    food_logs = FoodLog.query.filter_by(user_id=current_user.id, date=selected_date).order_by(FoodLog.id.desc()).all()

    return render_template(
        "food.html",
        active_page="food",
        food_logs=food_logs,
        food_data=FOOD_DATA,
        selected_date=selected_date,
        max_date=date.today().isoformat(),
    )


@dashboard_bp.route("/food/delete/<int:item_id>", methods=["POST"])
@login_required
def delete_food(item_id):
    selected_date = normalize_selected_date(request.form.get("date"))
    FoodLog.query.filter_by(id=item_id, user_id=current_user.id).delete()
    db.session.commit()
    return redirect(url_for("dashboard.food", date=selected_date))


@dashboard_bp.route("/food/edit/<int:item_id>", methods=["GET", "POST"])
@login_required
def edit_food(item_id):
    food_row = FoodLog.query.filter_by(id=item_id, user_id=current_user.id).first()

    if not food_row:
        abort(404)

    if request.method == "POST":
        food_row.qty = request.form["qty"]
        food_row.calories = request.form["calories"]
        food_row.protein = request.form["protein"]
        food_row.fat = request.form["fat"]
        food_row.sugar = request.form["sugar"]
        db.session.commit()
        return redirect(url_for("dashboard.food", date=food_row.date))

    return render_template("edit_food.html", active_page="food", f=food_row)


@dashboard_bp.route("/sleep", methods=["GET", "POST"])
@login_required
def sleep():
    selected_date = normalize_selected_date(request.args.get("date"))

    if request.method == "POST":
        post_date = normalize_selected_date(request.form["date"])
        sleep_entry = SleepLog.query.filter_by(user_id=current_user.id, date=post_date).first()
        if not sleep_entry:
            sleep_entry = SleepLog(user_id=current_user.id, date=post_date)
            db.session.add(sleep_entry)
        
        sleep_entry.hours = float(request.form["hours"])
        sleep_entry.quality = int(request.form["quality"])
        sleep_entry.notes = request.form.get("notes", "")
        db.session.commit()
        return redirect(url_for("dashboard.sleep", date=post_date))

    sleep_data = SleepLog.query.filter_by(user_id=current_user.id, date=selected_date).first()

    return render_template(
        "sleep.html",
        active_page="sleep",
        sleep=sleep_data,
        selected_date=selected_date,
        max_date=date.today().isoformat(),
    )


@dashboard_bp.route("/sleep/delete", methods=["POST"])
@login_required
def delete_sleep():
    selected_date = normalize_selected_date(request.form.get("date"))
    SleepLog.query.filter_by(user_id=current_user.id, date=selected_date).delete()
    db.session.commit()
    return redirect(url_for("dashboard.sleep", date=selected_date))


@dashboard_bp.route("/wellbeing", methods=["GET", "POST"])
@login_required
def wellbeing():
    selected_date = normalize_selected_date(request.args.get("date"))

    if request.method == "POST":
        activity = request.form["activity"]
        post_date = normalize_selected_date(request.form["date"])
        if activity == "OTHERS":
            activity = request.form.get("other_activity", "Other")

        log_entry = WellbeingLog(
            user_id=current_user.id,
            date=post_date,
            activity=activity,
            minutes=int(request.form["minutes"])
        )
        db.session.add(log_entry)
        db.session.commit()
        return redirect(url_for("dashboard.wellbeing", date=post_date))

    logs = WellbeingLog.query.filter_by(user_id=current_user.id, date=selected_date).order_by(WellbeingLog.id.desc()).all()

    return render_template(
        "wellbeing.html",
        active_page="wellbeing",
        wellbeing_logs=logs,
        selected_date=selected_date,
        max_date=date.today().isoformat(),
    )


@dashboard_bp.route("/wellbeing/delete/<int:item_id>", methods=["POST"])
@login_required
def delete_wellbeing(item_id):
    selected_date = normalize_selected_date(request.form.get("date"))
    WellbeingLog.query.filter_by(id=item_id, user_id=current_user.id).delete()
    db.session.commit()
    return redirect(url_for("dashboard.wellbeing", date=selected_date))


@dashboard_bp.route("/gym", methods=["GET", "POST"])
@login_required
def gym():
    selected_date = normalize_selected_date(request.args.get("date"))

    if request.method == "POST":
        post_date = normalize_selected_date(request.form.get("date", selected_date))
        intensity = request.form.get("intensity", "Medium")
        exercise = request.form.get("exercise", "")
        is_cardio = is_cardio_exercise(exercise)

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

        try:
            duration = float(request.form.get("duration") or 0)
        except ValueError:
            duration = 0

        try:
            speed = float(request.form.get("speed") or 0)
        except ValueError:
            speed = 0

        try:
            incline = float(request.form.get("incline") or 0)
        except ValueError:
            incline = 0

        muscle_factors = {
            "Legs": 1.25,
            "Back": 1.2,
            "Chest": 1.1,
            "Shoulders": 1.0,
            "Arms": 0.8,
            "Core": 0.9,
        }
        muscle = request.form["muscle"]
        muscle_factor = muscle_factors.get(muscle, 1.0)

        intensity_map = {"Easy": 0.8, "Medium": 1.0, "Hard": 1.3, "Extreme": 1.6}
        intensity_val = intensity_map.get(intensity, 1.0)

        if is_cardio:
            body_weight = current_user.weight if current_user.weight else 70

            cardio_met = {
                "Treadmill (Running)": 8.3,
                "Cycling": 6.8,
                "Elliptical": 5.0,
                "Inclined Walking": 4.3,
            }
            cardio_baseline_speed = {
                "Treadmill (Running)": 8.0,
                "Cycling": 16.0,
                "Elliptical": 6.0,
                "Inclined Walking": 5.0,
            }
            cardio_speed_factor = {
                "Treadmill (Running)": 0.45,
                "Cycling": 0.2,
                "Elliptical": 0.3,
                "Inclined Walking": 0.25,
            }

            base_met = cardio_met.get(exercise, 5.0)
            baseline_speed = cardio_baseline_speed.get(exercise, 6.0)
            speed_factor = cardio_speed_factor.get(exercise, 0.25)
            speed_boost = max(0, speed - baseline_speed) * speed_factor
            incline_boost = max(0, incline) * 0.35 if exercise == "Inclined Walking" else 0
            calories = ((base_met + speed_boost + incline_boost) * 3.5 * body_weight / 200) * duration
            sets = 0
            reps = 0
            weight = 0
        else:
            duration = 0
            speed = 0
            incline = 0
            eff_weight = weight if weight > 0 else 50
            calories = (sets * reps * eff_weight * 0.04) * muscle_factor * intensity_val

        log_entry = GymLog(
            user_id=current_user.id,
            date=post_date,
            muscle=muscle,
            exercise=exercise,
            sets=sets,
            reps=reps,
            weight=weight,
            speed=speed,
            incline=incline,
            intensity=intensity,
            duration=duration,
            calories=calories
        )
        db.session.add(log_entry)
        db.session.commit()
        return redirect(url_for("dashboard.gym", date=post_date))

    logs = GymLog.query.filter_by(user_id=current_user.id, date=selected_date).order_by(GymLog.id.desc()).all()

    streak = 0
    all_dates = db.session.query(GymLog.date).filter_by(user_id=current_user.id).distinct().order_by(GymLog.date.desc()).all()
    dates = [row.date for row in all_dates]

    current_day = date.today()
    if dates and (
        dates[0] == current_day.isoformat()
        or dates[0] == (current_day - timedelta(days=1)).isoformat()
    ):
        streak = 1
        check_date = datetime.strptime(dates[0], "%Y-%m-%d").date()
        for index in range(1, len(dates)):
            if dates[index] == (check_date - timedelta(days=1)).isoformat():
                streak += 1
                check_date -= timedelta(days=1)
            else:
                break

    last_workout = GymLog.query.filter_by(user_id=current_user.id).order_by(GymLog.id.desc()).first()

    return render_template(
        "gym.html",
        active_page="gym",
        cardio_exercises=sorted(CARDIO_EXERCISES),
        gym_logs=logs,
        selected_date=selected_date,
        streak=streak,
        last_workout=last_workout,
        max_date=date.today().isoformat(),
    )


@dashboard_bp.route("/gym/delete/<int:item_id>", methods=["POST"])
@login_required
def delete_gym(item_id):
    selected_date = normalize_selected_date(request.form.get("date"))
    GymLog.query.filter_by(id=item_id, user_id=current_user.id).delete()
    db.session.commit()
    return redirect(url_for("dashboard.gym", date=selected_date))


@dashboard_bp.route("/report")
@login_required
def report():
    selected_date = normalize_selected_date(request.args.get("date"))
    week = get_week_dates(selected_date)

    meals = db.session.query(
        FoodLog.meal,
        func.sum(FoodLog.calories).label('cal'),
        func.sum(FoodLog.protein).label('protein'),
        func.sum(FoodLog.fat).label('fat'),
        func.sum(FoodLog.sugar).label('sugar')
    ).filter(FoodLog.user_id == current_user.id, FoodLog.date == selected_date).group_by(FoodLog.meal).all()

    weekly_cal, weekly_sleep, weekly_wellbeing, weekly_gym = [], [], [], []

    for day_value in week:
        cal = db.session.query(func.coalesce(func.sum(FoodLog.calories), 0)).filter(FoodLog.user_id == current_user.id, FoodLog.date == day_value).scalar() or 0
        weekly_cal.append(cal)
        
        sleep_row = SleepLog.query.filter_by(user_id=current_user.id, date=day_value).first()
        weekly_sleep.append(sleep_row.hours if sleep_row else 0)
        
        wb = db.session.query(func.coalesce(func.sum(WellbeingLog.minutes), 0)).filter(WellbeingLog.user_id == current_user.id, WellbeingLog.date == day_value).scalar() or 0
        weekly_wellbeing.append(wb)
        
        gym_cal = db.session.query(func.coalesce(func.sum(GymLog.calories), 0)).filter(GymLog.user_id == current_user.id, GymLog.date == day_value).scalar() or 0
        weekly_gym.append(gym_cal)

    gym_logs = GymLog.query.filter_by(user_id=current_user.id, date=selected_date).all()
    gym_total = db.session.query(func.coalesce(func.sum(GymLog.calories), 0)).filter(GymLog.user_id == current_user.id, GymLog.date == selected_date).scalar() or 0

    return render_template(
        "report.html",
        active_page="report",
        meals=meals,
        gym_logs=gym_logs,
        gym_total=gym_total,
        selected_date=selected_date,
        week=week,
        weekly_cal=weekly_cal,
        weekly_sleep=weekly_sleep,
        weekly_wellbeing=weekly_wellbeing,
        weekly_gym=weekly_gym,
        max_date=date.today().isoformat(),
    )

@dashboard_bp.route("/admin/users")
@login_required
def admin_users():
    if not is_admin_user():
        abort(403)

    users = User.query.order_by(User.id.desc()).all()
    total_users = len(users)
    active_users = sum(1 for user in users if int(user.is_active or 0) == 1)

    return render_template(
        "admin_users.html",
        active_page="admin_users",
        users=users,
        total_users=total_users,
        active_users=active_users,
        inactive_users=total_users - active_users,
    )


@dashboard_bp.route("/chatbot", methods=["POST"])
@login_required
def chatbot():
    if not groq_client:
        return jsonify({
            "reply": "AI Chatbot is not configured. Please set the GROQ_API_KEY environment variable."
        }), 503

    data = request.json
    user_message = data.get("message", "").strip()
    if not user_message:
        return jsonify({"reply": "Please enter a message."}), 400

    today = date.today().isoformat()

    food_cal = db.session.query(func.coalesce(func.sum(FoodLog.calories), 0)).filter(FoodLog.user_id == current_user.id, FoodLog.date == today).scalar() or 0
    food_pro = db.session.query(func.coalesce(func.sum(FoodLog.protein), 0)).filter(FoodLog.user_id == current_user.id, FoodLog.date == today).scalar() or 0

    gym_logs = db.session.query(GymLog.exercise, GymLog.calories).filter(GymLog.user_id == current_user.id, GymLog.date == today).all()
    gym_cal_total = sum(row.calories for row in gym_logs)
    exercises = ", ".join(row.exercise for row in gym_logs)

    sleep_row = SleepLog.query.filter_by(user_id=current_user.id, date=today).first()

    age = current_user.age or "Not set"
    height = current_user.height or "Not set"
    weight = current_user.weight or "Not set"
    sleep_hrs = sleep_row.hours if sleep_row else "Not logged"

    context = (
        f"User Profile: Age: {age}, Height: {height}cm, Weight: {weight}kg.\n"
        f"Today's stats ({today}):\n"
        f"- Nutrition: consumed {food_cal} kcal and {food_pro}g protein.\n"
        f"- Activity: burned {gym_cal_total} kcal via: {exercises if exercises else 'No workout yet'}.\n"
        f"- Sleep: {sleep_hrs} hours logged."
    )

    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a fitness coach AI integrated into a fitness tracking app called VitalLog. "
                        "Give short, actionable, and encouraging advice. Avoid medical diagnosis. "
                        "Use the user's real data when relevant. Keep responses concise (under 3 sentences)."
                    ),
                },
                {"role": "user", "content": f"Context: {context}\n\nUser Question: {user_message}"},
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.7,
            max_tokens=256,
        )
        reply = chat_completion.choices[0].message.content
        return jsonify({"reply": reply})
    except Exception as e:
        print(f"Chatbot Error: {e}")
        return jsonify({"reply": "I'm sorry, I'm having trouble connecting. Try again in a moment!"}), 500
