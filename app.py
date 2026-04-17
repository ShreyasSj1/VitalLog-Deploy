import os
import secrets
import sqlite3
from datetime import date, datetime, timedelta, timezone
from functools import wraps
from pathlib import Path
from urllib.parse import urljoin, urlparse

from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
    jsonify,
)
import groq
import json
import base64
import firebase_admin
from firebase_admin import credentials, auth as firebase_auth
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from werkzeug.security import check_password_hash, generate_password_hash

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:
    psycopg = None
    dict_row = None

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-me-in-production")

DEFAULT_SQLITE_PATH = Path(__file__).with_name("fitness.db")
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DEFAULT_SQLITE_PATH}")

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)

@app.context_processor
def inject_firebase_config():
    return dict(
        firebase_api_key=os.environ.get("FIREBASE_API_KEY", ""),
        firebase_auth_domain=os.environ.get("FIREBASE_AUTH_DOMAIN", ""),
        firebase_project_id=os.environ.get("FIREBASE_PROJECT_ID", "")
    )

# ================= FIREBASE ADMIN =================
firebase_credentials = os.environ.get("FIREBASE_CREDENTIALS_BASE64")
if firebase_credentials:
    cred_json = base64.b64decode(firebase_credentials).decode("utf-8")
    cred = credentials.Certificate(json.loads(cred_json))
    firebase_admin.initialize_app(cred)
elif os.path.exists("firebase-adminsdk.json"):
    cred = credentials.Certificate("firebase-adminsdk.json")
    firebase_admin.initialize_app(cred)
else:
    try:
        firebase_admin.initialize_app()
    except ValueError:
        pass

# ================= GROQ AI =================
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
groq_client = None
if GROQ_API_KEY:
    groq_client = groq.Groq(api_key=GROQ_API_KEY)


# ================= DAILY GOALS =================
GOALS = {
    "calories": 1500,
    "protein": 100,
    "fat": 40,
    "sugar": 25,
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


class User(UserMixin):
    def __init__(self, row):
        self.id = row["id"]
        self.email = row["email"]
        self.name = row["name"] or row["email"]
        self.age = row["age"]
        self.height = row["height"]
        self.weight = row["weight"]
        self.role = row["role"]
        self.active = bool(row["is_active"])

    @property
    def is_active(self):
        return self.active


# ================= DB HELPERS =================
def normalize_database_url(url):
    return url.replace("postgres://", "postgresql://", 1)


DATABASE_URL = normalize_database_url(DATABASE_URL)
DB_SCHEME = urlparse(DATABASE_URL).scheme
DB_ENGINE = "postgres" if DB_SCHEME.startswith("postgresql") else "sqlite"


class DBConnection:
    def __init__(self, conn, engine):
        self._conn = conn
        self.engine = engine

    def _rewrite_query(self, query):
        if self.engine == "postgres":
            return query.replace("?", "%s")
        return query

    def execute(self, query, params=()):
        return self._conn.execute(self._rewrite_query(query), params)

    def executescript(self, script):
        if self.engine == "postgres":
            statements = [stmt.strip() for stmt in script.split(";") if stmt.strip()]
            for statement in statements:
                self._conn.execute(statement)
            return None
        return self._conn.executescript(script)

    def commit(self):
        self._conn.commit()

    def close(self):
        self._conn.close()


def get_sqlite_path():
    if DATABASE_URL.startswith("sqlite:///"):
        return DATABASE_URL.removeprefix("sqlite:///")
    if DATABASE_URL.startswith("sqlite://"):
        return DATABASE_URL.removeprefix("sqlite://")
    return str(DEFAULT_SQLITE_PATH)


def sqlite_compat_row(cursor):
    dict_maker = dict_row(cursor)
    def make_row(values):
        d = dict_maker(values)
        class Row(dict):
            def __getitem__(self, key):
                if isinstance(key, int):
                    return values[key]
                return super().__getitem__(key)
        return Row(d)
    return make_row


def get_db():
    if DB_ENGINE == "postgres":
        if psycopg is None:
            raise RuntimeError(
                "PostgreSQL support requires 'psycopg[binary]'. Install requirements before using DATABASE_URL."
            )
        conn = psycopg.connect(DATABASE_URL, row_factory=sqlite_compat_row)
        return DBConnection(conn, "postgres")

    db = sqlite3.connect(get_sqlite_path())
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return DBConnection(db, "sqlite")


def table_columns(db, table_name):
    return {row["name"] for row in db.execute(f"PRAGMA table_info({table_name})").fetchall()}


def index_columns(db, index_name):
    rows = db.execute(f"PRAGMA index_info({index_name})").fetchall()
    return [row["name"] for row in rows]


def sleep_log_has_user_unique_index(db):
    indexes = db.execute("PRAGMA index_list(sleep_log)").fetchall()
    for idx in indexes:
        if idx["unique"] and index_columns(db, idx["name"]) == ["user_id", "date"]:
            return True
    return False


def ensure_column(db, table_name, column_name, definition):
    if column_name not in table_columns(db, table_name):
        try:
            db.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")
        except sqlite3.OperationalError as exc:
            if "duplicate column name" not in str(exc).lower():
                raise


def migrate_users_table(db):
    columns = table_columns(db, "users")
    expected = {
        "id",
        "email",
        "password_hash",
        "name",
        "age",
        "height",
        "weight",
        "role",
        "is_active",
        "created_at",
    }
    if columns == expected:
        return

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS users_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT,
            age INTEGER,
            height REAL,
            weight REAL,
            role TEXT NOT NULL DEFAULT 'user',
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    if "users" in {
        row["name"] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    }:
        password_expr = (
            "password_hash"
            if "password_hash" in columns
            else "'__migrate_me__'"
        )
        created_expr = "created_at" if "created_at" in columns else "CURRENT_TIMESTAMP"
        name_expr = "name" if "name" in columns else "email"
        age_expr = "age" if "age" in columns else "NULL"
        height_expr = "height" if "height" in columns else "NULL"
        weight_expr = "weight" if "weight" in columns else "NULL"
        role_expr = "role" if "role" in columns else "'user'"
        active_expr = "is_active" if "is_active" in columns else "1"

        db.execute(
            f"""
            INSERT INTO users_new (id, email, password_hash, name, age, height, weight, role, is_active, created_at)
            SELECT id, email, {password_expr}, {name_expr}, {age_expr}, {height_expr}, {weight_expr}, {role_expr}, {active_expr}, {created_expr}
            FROM users
            """
        )
        db.execute("DROP TABLE users")

    db.execute("ALTER TABLE users_new RENAME TO users")


def migrate_sleep_log_table(db):
    columns = table_columns(db, "sleep_log")
    if "user_id" in columns and sleep_log_has_user_unique_index(db):
        return

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS sleep_log_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            date TEXT,
            hours REAL,
            quality INTEGER,
            notes TEXT,
            UNIQUE(user_id, date),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )

    if "user_id" in columns:
        db.execute(
            """
            INSERT INTO sleep_log_new (id, user_id, date, hours, quality, notes)
            SELECT id, user_id, date, hours, quality, notes
            FROM sleep_log
            """
        )
    else:
        db.execute(
            """
            INSERT INTO sleep_log_new (id, date, hours, quality, notes)
            SELECT id, date, hours, quality, notes
            FROM sleep_log
            """
        )

    db.execute("DROP TABLE sleep_log")
    db.execute("ALTER TABLE sleep_log_new RENAME TO sleep_log")


def migrate_schema():
    db = get_db()

    with open("schema.sql", encoding="utf-8") as f:
        db.executescript(f.read())

    migrate_users_table(db)
    ensure_column(db, "users", "age", "INTEGER")
    ensure_column(db, "users", "height", "REAL")
    ensure_column(db, "users", "weight", "REAL")
    ensure_column(db, "food_log", "user_id", "INTEGER")
    ensure_column(db, "wellbeing_log", "user_id", "INTEGER")
    ensure_column(db, "gym_log", "user_id", "INTEGER")
    ensure_column(db, "gym_log", "speed", "REAL")
    ensure_column(db, "gym_log", "incline", "REAL")
    migrate_sleep_log_table(db)

    db.execute("CREATE INDEX IF NOT EXISTS idx_food_log_user_date ON food_log(user_id, date)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_sleep_log_user_date ON sleep_log(user_id, date)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_wellbeing_log_user_date ON wellbeing_log(user_id, date)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_gym_log_user_date ON gym_log(user_id, date)")
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_token ON password_reset_tokens(token)"
    )

    db.commit()
    db.close()


def init_db():
    if DB_ENGINE == "postgres":
        db = get_db()
        with open("schema_postgres.sql", encoding="utf-8") as f:
            db.executescript(f.read())
        db.commit()
        db.close()
        return

    migrate_schema()


def get_user_by_id(user_id):
    db = get_db()
    row = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    db.close()
    return User(row) if row else None


def get_user_by_email(email):
    db = get_db()
    row = db.execute("SELECT * FROM users WHERE email = ?", (email.lower(),)).fetchone()
    db.close()
    return row


def parse_admin_emails():
    raw = os.environ.get("ADMIN_EMAILS", "")
    return {email.strip().lower() for email in raw.split(",") if email.strip()}


def default_role_for_email(db, email):
    if email.lower() in parse_admin_emails():
        return "admin"

    user_count = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    return "admin" if user_count == 0 else "user"


def claim_legacy_rows(db, user_id):
    user_count = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if user_count != 1:
        return

    for table_name in ("food_log", "sleep_log", "wellbeing_log", "gym_log"):
        db.execute(f"UPDATE {table_name} SET user_id = ? WHERE user_id IS NULL", (user_id,))


def create_user(name, email, password):
    db = get_db()
    normalized_email = email.strip().lower()
    existing = db.execute("SELECT id FROM users WHERE email = ?", (normalized_email,)).fetchone()
    if existing:
        db.close()
        return None, "An account with that email already exists."

    role = default_role_for_email(db, normalized_email)
    params = (normalized_email, generate_password_hash(password), name.strip() or normalized_email, role)
    if DB_ENGINE == "postgres":
        user_id = db.execute(
            """
            INSERT INTO users (email, password_hash, name, role, is_active)
            VALUES (?, ?, ?, ?, 1)
            RETURNING id
            """,
            params,
        ).fetchone()["id"]
    else:
        cursor = db.execute(
            """
            INSERT INTO users (email, password_hash, name, role, is_active)
            VALUES (?, ?, ?, ?, 1)
            """,
            params,
        )
        user_id = cursor.lastrowid
    claim_legacy_rows(db, user_id)
    db.commit()
    row = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    db.close()
    return User(row), None


def now_utc():
    return datetime.now(timezone.utc)


def utc_iso(dt):
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def parse_utc_iso(value):
    return datetime.fromisoformat(value)


def issue_password_reset_token(email):
    db = get_db()
    normalized_email = email.strip().lower()
    user = db.execute("SELECT id, email FROM users WHERE email = ?", (normalized_email,)).fetchone()
    if not user:
        db.close()
        return None

    db.execute(
        """
        UPDATE password_reset_tokens
        SET used_at = ?
        WHERE user_id = ? AND used_at IS NULL
        """,
        (utc_iso(now_utc()), user["id"]),
    )

    token = secrets.token_urlsafe(32)
    expires_at = now_utc() + timedelta(minutes=30)
    db.execute(
        """
        INSERT INTO password_reset_tokens (user_id, token, expires_at)
        VALUES (?, ?, ?)
        """,
        (user["id"], token, utc_iso(expires_at)),
    )
    db.commit()
    db.close()
    return token


def get_valid_password_reset_token(token):
    db = get_db()
    row = db.execute(
        """
        SELECT password_reset_tokens.*, users.email
        FROM password_reset_tokens
        JOIN users ON users.id = password_reset_tokens.user_id
        WHERE password_reset_tokens.token = ?
        """,
        (token,),
    ).fetchone()
    db.close()

    if not row or row["used_at"]:
        return None

    if parse_utc_iso(row["expires_at"]) < now_utc():
        return None

    return row


def consume_password_reset_token(token, new_password):
    token_row = get_valid_password_reset_token(token)
    if not token_row:
        return False

    db = get_db()
    used_at = utc_iso(now_utc())
    db.execute(
        "UPDATE users SET password_hash = ? WHERE id = ?",
        (generate_password_hash(new_password), token_row["user_id"]),
    )
    db.execute(
        "UPDATE password_reset_tokens SET used_at = ? WHERE token = ?",
        (used_at, token),
    )
    db.execute(
        """
        UPDATE password_reset_tokens
        SET used_at = ?
        WHERE user_id = ? AND token != ? AND used_at IS NULL
        """,
        (used_at, token_row["user_id"], token),
    )
    db.commit()
    db.close()
    return True


# ================= AUTH HELPERS =================
def render_page(template_name, **context):
    return render_template(template_name, **context)


def parse_optional_int(value):
    value = (value or "").strip()
    return int(value) if value else None


def parse_optional_float(value):
    value = (value or "").strip()
    return float(value) if value else None


def is_safe_redirect_target(target):
    if not target:
        return False
    host_url = urlparse(request.host_url)
    redirect_url = urlparse(urljoin(request.host_url, target))
    return redirect_url.scheme in ("http", "https") and host_url.netloc == redirect_url.netloc


def next_redirect_target(default_endpoint="index"):
    target = session.pop("next_url", None)
    if is_safe_redirect_target(target):
        return target
    return url_for(default_endpoint)


def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapped_view(*args, **kwargs):
            if current_user.role not in roles:
                abort(403)
            return view_func(*args, **kwargs)

        return wrapped_view

    return decorator


@login_manager.user_loader
def load_user(user_id):
    return get_user_by_id(int(user_id))


@login_manager.unauthorized_handler
def unauthorized():
    session["next_url"] = request.url
    return redirect(url_for("login"))


# ================= UTIL =================
def normalize_selected_date(raw_date):
    today_iso = date.today().isoformat()
    if not raw_date:
        return today_iso

    try:
        parsed = datetime.strptime(raw_date, "%Y-%m-%d").date()
    except ValueError:
        return today_iso

    return min(parsed, date.today()).isoformat()


def is_cardio_exercise(exercise_name):
    return exercise_name in CARDIO_EXERCISES


def get_week_dates(selected_date):
    d = datetime.strptime(selected_date, "%Y-%m-%d")
    start = d - timedelta(days=6)
    return [(start + timedelta(days=i)).date().isoformat() for i in range(7)]


# ================= AUTH =================
@app.route("/api/auth/firebase", methods=["POST"])
def auth_firebase():
    data = request.json
    id_token = data.get("idToken")
    name = data.get("name", "")
    
    if not id_token:
        return jsonify({"error": "No token provided"}), 400
        
    try:
        decoded_token = firebase_auth.verify_id_token(id_token)
        uid = decoded_token['uid']
        email = decoded_token.get('email', '').strip().lower()
        if not email:
            return jsonify({"error": "Email is required"}), 400
        
        # Look up user or create them
        user_row = get_user_by_email(email)
        if not user_row:
            # Create user (bypass normal create_user password flow)
            db = get_db()
            role = default_role_for_email(db, email)
            # Use 'firebase_managed' as password hash
            params = (email, 'firebase_managed', name or email, role)
            
            if DB_ENGINE == "postgres":
                user_id = db.execute(
                    "INSERT INTO users (email, password_hash, name, role, is_active) VALUES (%s, %s, %s, %s, 1) RETURNING id",
                    params,
                ).fetchone()["id"]
            else:
                cursor = db.execute(
                    "INSERT INTO users (email, password_hash, name, role, is_active) VALUES (?, ?, ?, ?, 1)",
                    params,
                )
                user_id = cursor.lastrowid
                
            claim_legacy_rows(db, user_id)
            db.commit()
            user_row = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            db.close()
            
        user = User(user_row)
        if not user.is_active:
            return jsonify({"error": "Account inactive"}), 403
            
        login_user(user)
        return jsonify({"success": True})
        
    except Exception as e:
        print(f"Firebase auth error: {e}")
        return jsonify({"error": "Invalid token"}), 401


@app.route("/login", methods=["GET"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    return render_page("login.html")


@app.route("/register", methods=["GET"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    return render_page("register.html")


@app.route("/logout", methods=["POST", "GET"])
@login_required
def logout():
    logout_user()
    flash("You're signed out for now. Let's get you back on track.")
    return redirect(url_for("login"))


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    db = get_db()

    if request.method == "POST":
        name = request.form.get("name", "").strip() or current_user.email
        try:
            age = parse_optional_int(request.form.get("age"))
            height = parse_optional_float(request.form.get("height"))
            weight = parse_optional_float(request.form.get("weight"))
        except ValueError:
            db.close()
            flash("Age, height, and weight must be valid numbers.")
            return redirect(url_for("profile"))

        db.execute(
            """
            UPDATE users
            SET name = ?, age = ?, height = ?, weight = ?
            WHERE id = ?
            """,
            (name, age, height, weight, current_user.id),
        )
        db.commit()
        db.close()
        flash("Personal information updated.")
        return redirect(url_for("profile"))

    user_row = db.execute("SELECT * FROM users WHERE id = ?", (current_user.id,)).fetchone()
    db.close()
    return render_page("profile.html", active_page="profile", profile=user_row)


@app.route("/forgot-password", methods=["GET"])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    return render_page("forgot_password.html")


@app.route("/reset-password/<token>", methods=["GET"])
def reset_password(token):
    # Deprecated in favor of Firebase Native Reset
    return redirect(url_for("login"))


# ================= HEALTH =================
@app.route("/health")
def health():
    return {"ok": True, "status": "healthy"}, 200


# ================= DASHBOARD =================
@app.route("/")
@login_required
def index():
    selected_date = normalize_selected_date(request.args.get("date"))
    week = get_week_dates(selected_date)
    db = get_db()

    totals = db.execute(
        """
        SELECT
            COALESCE(SUM(calories), 0) AS cal,
            COALESCE(SUM(protein), 0) AS protein,
            COALESCE(SUM(fat), 0) AS fat,
            COALESCE(SUM(sugar), 0) AS sugar
        FROM food_log
        WHERE user_id = ? AND date = ?
        """,
        (current_user.id, selected_date),
    ).fetchone()

    gym_total = db.execute(
        "SELECT COALESCE(SUM(calories), 0) FROM gym_log WHERE user_id = ? AND date = ?",
        (current_user.id, selected_date),
    ).fetchone()[0]

    weekly_cal, weekly_sleep, weekly_wellbeing, weekly_gym = [], [], [], []

    for day_value in week:
        weekly_cal.append(
            db.execute(
                "SELECT COALESCE(SUM(calories), 0) FROM food_log WHERE user_id = ? AND date = ?",
                (current_user.id, day_value),
            ).fetchone()[0]
        )
        sleep_row = db.execute(
            "SELECT hours FROM sleep_log WHERE user_id = ? AND date = ?",
            (current_user.id, day_value),
        ).fetchone()
        weekly_sleep.append(sleep_row["hours"] if sleep_row else 0)
        weekly_wellbeing.append(
            db.execute(
                "SELECT COALESCE(SUM(minutes), 0) FROM wellbeing_log WHERE user_id = ? AND date = ?",
                (current_user.id, day_value),
            ).fetchone()[0]
        )
        weekly_gym.append(
            db.execute(
                "SELECT COALESCE(SUM(calories), 0) FROM gym_log WHERE user_id = ? AND date = ?",
                (current_user.id, day_value),
            ).fetchone()[0]
        )

    gym_duration = db.execute(
        "SELECT COALESCE(SUM(duration), 0) FROM gym_log WHERE user_id = ? AND date = ?",
        (current_user.id, selected_date),
    ).fetchone()[0]

    score = 100
    reasons = []

    cal_intake = totals["cal"]
    cal_goal = GOALS["calories"]
    if cal_intake > cal_goal:
        penalty = min(20, int((cal_intake - cal_goal) / 20))
        score -= penalty
        if penalty > 5:
            reasons.append(("Calorie limit exceeded", "bad"))
    elif cal_intake > 0:
        reasons.append(("Calorie target healthy", "good"))

    if totals["protein"] >= GOALS["protein"]:
        reasons.append(("Protein goal met", "good"))
    else:
        score -= 10
        reasons.append(("Protein intake low", "bad"))

    if totals["sugar"] > GOALS["sugar"]:
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

    sleep_row = db.execute(
        "SELECT hours FROM sleep_log WHERE user_id = ? AND date = ?",
        (current_user.id, selected_date),
    ).fetchone()
    if sleep_row:
        if sleep_row["hours"] >= 7:
            reasons.append(("Healthy sleep duration", "good"))
        else:
            score -= 10
            reasons.append(("Short sleep duration", "bad"))
    else:
        score -= 5
        reasons.append(("No sleep data", "bad"))

    score = max(0, min(100, score))

    db.close()

    return render_page(
        "index.html",
        active_page="dashboard",
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
        weekly_gym=weekly_gym,
        max_date=date.today().isoformat(),
    )


# ================= FOOD =================
@app.route("/food", methods=["GET", "POST"])
@login_required
def food():
    db = get_db()
    selected_date = normalize_selected_date(request.args.get("date", request.form.get("date")))

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
            calories, protein, fat, sugar = [value * qty for value in base]

        db.execute(
            """
            INSERT INTO food_log
            (user_id, date, meal, food, qty, calories, protein, fat, sugar)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (current_user.id, selected_date, meal, name, qty, calories, protein, fat, sugar),
        )

        db.commit()
        db.close()
        return redirect(url_for("food", date=selected_date))

    food_logs = db.execute(
        "SELECT * FROM food_log WHERE user_id = ? AND date = ? ORDER BY id DESC",
        (current_user.id, selected_date),
    ).fetchall()

    db.close()
    return render_page(
        "food.html",
        active_page="food",
        food_logs=food_logs,
        food_data=FOOD_DATA,
        selected_date=selected_date,
        max_date=date.today().isoformat(),
    )


@app.route("/food/delete/<int:item_id>", methods=["POST"])
@login_required
def delete_food(item_id):
    selected_date = normalize_selected_date(request.form.get("date"))
    db = get_db()
    db.execute("DELETE FROM food_log WHERE id = ? AND user_id = ?", (item_id, current_user.id))
    db.commit()
    db.close()
    return redirect(url_for("food", date=selected_date))


@app.route("/food/edit/<int:item_id>", methods=["GET", "POST"])
@login_required
def edit_food(item_id):
    db = get_db()
    food_row = db.execute(
        "SELECT * FROM food_log WHERE id = ? AND user_id = ?",
        (item_id, current_user.id),
    ).fetchone()

    if not food_row:
        db.close()
        abort(404)

    if request.method == "POST":
        db.execute(
            """
            UPDATE food_log
            SET qty = ?, calories = ?, protein = ?, fat = ?, sugar = ?
            WHERE id = ? AND user_id = ?
            """,
            (
                request.form["qty"],
                request.form["calories"],
                request.form["protein"],
                request.form["fat"],
                request.form["sugar"],
                item_id,
                current_user.id,
            ),
        )
        db.commit()
        db.close()
        return redirect(url_for("food", date=food_row["date"]))

    db.close()
    return render_page("edit_food.html", active_page="food", f=food_row)


# ================= SLEEP =================
@app.route("/sleep", methods=["GET", "POST"])
@login_required
def sleep():
    selected_date = normalize_selected_date(request.args.get("date"))
    db = get_db()

    if request.method == "POST":
        db.execute(
            """
            INSERT INTO sleep_log (user_id, date, hours, quality, notes)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id, date) DO UPDATE SET
                hours = excluded.hours,
                quality = excluded.quality,
                notes = excluded.notes
            """,
            (
                current_user.id,
                normalize_selected_date(request.form["date"]),
                float(request.form["hours"]),
                int(request.form["quality"]),
                request.form.get("notes", ""),
            ),
        )
        db.commit()
        db.close()
        return redirect(url_for("sleep", date=normalize_selected_date(request.form["date"])))

    sleep_data = db.execute(
        "SELECT * FROM sleep_log WHERE user_id = ? AND date = ?",
        (current_user.id, selected_date),
    ).fetchone()

    db.close()
    return render_page(
        "sleep.html",
        active_page="sleep",
        sleep=sleep_data,
        selected_date=selected_date,
        max_date=date.today().isoformat(),
    )


@app.route("/sleep/delete", methods=["POST"])
@login_required
def delete_sleep():
    selected_date = normalize_selected_date(request.form.get("date"))
    db = get_db()
    db.execute("DELETE FROM sleep_log WHERE user_id = ? AND date = ?", (current_user.id, selected_date))
    db.commit()
    db.close()
    return redirect(url_for("sleep", date=selected_date))


# ================= WELL-BEING =================
@app.route("/wellbeing", methods=["GET", "POST"])
@login_required
def wellbeing():
    selected_date = normalize_selected_date(request.args.get("date"))
    db = get_db()

    if request.method == "POST":
        activity = request.form["activity"]
        if activity == "OTHERS":
            activity = request.form.get("other_activity", "Other")

        db.execute(
            """
            INSERT INTO wellbeing_log (user_id, date, activity, minutes)
            VALUES (?, ?, ?, ?)
            """,
            (
                current_user.id,
                normalize_selected_date(request.form["date"]),
                activity,
                int(request.form["minutes"]),
            ),
        )

        db.commit()
        db.close()
        return redirect(url_for("wellbeing", date=normalize_selected_date(request.form["date"])))

    logs = db.execute(
        """
        SELECT * FROM wellbeing_log
        WHERE user_id = ? AND date = ?
        ORDER BY id DESC
        """,
        (current_user.id, selected_date),
    ).fetchall()

    db.close()
    return render_page(
        "wellbeing.html",
        active_page="wellbeing",
        wellbeing_logs=logs,
        selected_date=selected_date,
        max_date=date.today().isoformat(),
    )


@app.route("/wellbeing/delete/<int:item_id>", methods=["POST"])
@login_required
def delete_wellbeing(item_id):
    selected_date = normalize_selected_date(request.form.get("date"))
    db = get_db()
    db.execute("DELETE FROM wellbeing_log WHERE id = ? AND user_id = ?", (item_id, current_user.id))
    db.commit()
    db.close()
    return redirect(url_for("wellbeing", date=selected_date))


# ================= GYM =================
@app.route("/gym", methods=["GET", "POST"])
@login_required
def gym():
    selected_date = normalize_selected_date(request.args.get("date"))
    db = get_db()

    if request.method == "POST":
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
            profile_weight_row = db.execute(
                "SELECT weight FROM users WHERE id = ?",
                (current_user.id,),
            ).fetchone()
            body_weight = profile_weight_row["weight"] if profile_weight_row and profile_weight_row["weight"] else 70

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

        db.execute(
            """
            INSERT INTO gym_log
            (user_id, date, muscle, exercise, sets, reps, weight, speed, incline, intensity, duration, calories)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                current_user.id,
                normalize_selected_date(request.form.get("date", selected_date)),
                muscle,
                exercise,
                sets,
                reps,
                weight,
                speed,
                incline,
                intensity,
                duration,
                calories,
            ),
        )
        db.commit()
        db.close()
        return redirect(url_for("gym", date=normalize_selected_date(request.form.get("date", selected_date))))

    logs = db.execute(
        """
        SELECT * FROM gym_log
        WHERE user_id = ? AND date = ?
        ORDER BY id DESC
        """,
        (current_user.id, selected_date),
    ).fetchall()

    streak = 0
    all_dates = db.execute(
        "SELECT DISTINCT date FROM gym_log WHERE user_id = ? ORDER BY date DESC",
        (current_user.id,),
    ).fetchall()
    dates = [row["date"] for row in all_dates]

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

    last_workout = db.execute(
        "SELECT * FROM gym_log WHERE user_id = ? ORDER BY id DESC LIMIT 1",
        (current_user.id,),
    ).fetchone()

    db.close()
    return render_page(
        "gym.html",
        active_page="gym",
        cardio_exercises=sorted(CARDIO_EXERCISES),
        gym_logs=logs,
        selected_date=selected_date,
        streak=streak,
        last_workout=last_workout,
        max_date=date.today().isoformat(),
    )


@app.route("/gym/delete/<int:item_id>", methods=["POST"])
@login_required
def delete_gym(item_id):
    selected_date = normalize_selected_date(request.form.get("date"))
    db = get_db()
    db.execute("DELETE FROM gym_log WHERE id = ? AND user_id = ?", (item_id, current_user.id))
    db.commit()
    db.close()
    return redirect(url_for("gym", date=selected_date))


# ================= REPORT =================
@app.route("/report")
@login_required
def report():
    selected_date = normalize_selected_date(request.args.get("date"))
    week = get_week_dates(selected_date)
    db = get_db()

    meals = db.execute(
        """
        SELECT meal,
               SUM(calories) cal,
               SUM(protein) protein,
               SUM(fat) fat,
               SUM(sugar) sugar
        FROM food_log
        WHERE user_id = ? AND date = ?
        GROUP BY meal
        """,
        (current_user.id, selected_date),
    ).fetchall()

    weekly_cal, weekly_sleep, weekly_wellbeing, weekly_gym = [], [], [], []

    for day_value in week:
        weekly_cal.append(
            db.execute(
                "SELECT COALESCE(SUM(calories), 0) FROM food_log WHERE user_id = ? AND date = ?",
                (current_user.id, day_value),
            ).fetchone()[0]
        )
        sleep_row = db.execute(
            "SELECT hours FROM sleep_log WHERE user_id = ? AND date = ?",
            (current_user.id, day_value),
        ).fetchone()
        weekly_sleep.append(sleep_row["hours"] if sleep_row else 0)
        weekly_wellbeing.append(
            db.execute(
                "SELECT COALESCE(SUM(minutes), 0) FROM wellbeing_log WHERE user_id = ? AND date = ?",
                (current_user.id, day_value),
            ).fetchone()[0]
        )
        weekly_gym.append(
            db.execute(
                "SELECT COALESCE(SUM(calories), 0) FROM gym_log WHERE user_id = ? AND date = ?",
                (current_user.id, day_value),
            ).fetchone()[0]
        )

    gym_logs = db.execute(
        "SELECT * FROM gym_log WHERE user_id = ? AND date = ?",
        (current_user.id, selected_date),
    ).fetchall()
    gym_total = db.execute(
        "SELECT COALESCE(SUM(calories), 0) FROM gym_log WHERE user_id = ? AND date = ?",
        (current_user.id, selected_date),
    ).fetchone()[0]

    db.close()
    return render_page(
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


# ================= CHATBOT =================
@app.route("/chatbot", methods=["POST"])
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

    db = get_db()
    today = date.today().isoformat()

    # 1. Fetch User Profile
    user_row = db.execute(
        "SELECT age, height, weight FROM users WHERE id = ?", (current_user.id,)
    ).fetchone()

    # 2. Fetch Today's Summaries
    food_summary = db.execute(
        """
        SELECT COALESCE(SUM(calories), 0) as cal, COALESCE(SUM(protein), 0) as pro
        FROM food_log WHERE user_id = ? AND date = ?
        """,
        (current_user.id, today),
    ).fetchone()

    gym_logs = db.execute(
        "SELECT exercise, calories FROM gym_log WHERE user_id = ? AND date = ?",
        (current_user.id, today),
    ).fetchall()
    gym_cal_total = sum(row["calories"] for row in gym_logs)
    exercises = ", ".join(row["exercise"] for row in gym_logs)

    sleep_row = db.execute(
        "SELECT hours FROM sleep_log WHERE user_id = ? AND date = ?",
        (current_user.id, today),
    ).fetchone()

    db.close()

    # 3. Build Context
    age = user_row["age"] or "Not set"
    height = user_row["height"] or "Not set"
    weight = user_row["weight"] or "Not set"
    food_cal = food_summary["cal"]
    food_pro = food_summary["pro"]
    sleep_hrs = sleep_row["hours"] if sleep_row else "Not logged"

    context = (
        f"User Profile: Age: {age}, Height: {height}cm, Weight: {weight}kg.\n"
        f"Today's stats ({today}):\n"
        f"- Nutrition: consumed {food_cal} kcal and {food_pro}g protein.\n"
        f"- Activity: burned {gym_cal_total} kcal via: {exercises if exercises else 'No workout yet'}.\n"
        f"- Sleep: {sleep_hrs} hours logged."
    )

    # 4. Groq API Call
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


init_db()


# ================= RUN =================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5002))
    debug = os.environ.get("FLASK_DEBUG", "true").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
