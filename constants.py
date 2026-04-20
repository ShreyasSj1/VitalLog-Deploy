GOALS = {
    "calories": 1500,
    "protein": 100,
    "fat": 40,
    "sugar": 25,
}

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
        "Tea / Coffee": (90, 2.5, 3, 7),
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
        "Curd (Plain)": (60, 3, 3, 2),
    },
    "Pre/Post Workout": {
        "Protein Shake (Milk)": (450, 45, 15, 15),
        "Protein Shake (Water)": (150, 30, 1, 2),
        "Banana": (105, 1, 0.4, 14),
        "Peanut Butter Sandwich": (380, 10, 16, 8),
        "Greek Yogurt": (130, 23, 2, 6),
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
        "Nuts (Handful)": (170, 6, 14, 2),
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
        "Salad": (80, 2, 3, 4),
    },
}

CARDIO_EXERCISES = {"Treadmill (Running)", "Cycling", "Elliptical", "Inclined Walking"}

# ============================================================
# Full exercise catalog: muscle_group → list of exercise names
# ============================================================
EXERCISE_CATALOG = {
    "Chest": [
        "Bench Press", "Incline Bench Press", "Decline Bench Press",
        "Dumbbell Fly", "Push-Ups", "Cable Crossover", "Chest Dip",
    ],
    "Back": [
        "Pull-Ups", "Lat Pulldown", "Seated Cable Row", "Barbell Row",
        "Dumbbell Row", "Deadlift", "T-Bar Row", "Face Pulls",
    ],
    "Shoulders": [
        "Overhead Press", "Arnold Press", "Lateral Raises",
        "Front Raises", "Rear Delt Fly", "Shrugs",
    ],
    "Arms": [
        "Bicep Curl", "Hammer Curl", "Preacher Curl",
        "Tricep Pushdown", "Skull Crushers", "Close-Grip Bench Press",
        "Tricep Dip", "Concentration Curl",
    ],
    "Legs": [
        "Squat", "Leg Press", "Leg Extension", "Leg Curl",
        "Romanian Deadlift", "Lunges", "Calf Raises", "Hack Squat",
        "Goblet Squat", "Bulgarian Split Squat",
    ],
    "Core": [
        "Plank", "Crunches", "Leg Raises", "Russian Twists",
        "Ab Rollout", "Cable Crunch", "Hanging Knee Raise",
        "Bicycle Crunches", "Side Plank",
    ],
    "Cardio": [
        "Treadmill (Running)", "Cycling", "Elliptical", "Inclined Walking",
    ],
}

# Muscle calorie multipliers (used in calorie estimation for weight training)
MUSCLE_FACTORS = {
    "Legs": 1.25,
    "Back": 1.2,
    "Chest": 1.1,
    "Shoulders": 1.0,
    "Arms": 0.8,
    "Core": 0.9,
    "Cardio": 1.0,
}

# Cardio MET values and speed parameters
CARDIO_META = {
    "Treadmill (Running)": {"met": 8.3, "baseline_speed": 8.0, "speed_factor": 0.45},
    "Cycling":             {"met": 6.8, "baseline_speed": 16.0, "speed_factor": 0.2},
    "Elliptical":          {"met": 5.0, "baseline_speed": 6.0,  "speed_factor": 0.3},
    "Inclined Walking":    {"met": 4.3, "baseline_speed": 5.0,  "speed_factor": 0.25},
}

INTENSITY_MAP = {"Easy": 0.8, "Medium": 1.0, "Hard": 1.3, "Extreme": 1.6}
