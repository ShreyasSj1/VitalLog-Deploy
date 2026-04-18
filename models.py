import os
import secrets
from datetime import datetime, timedelta, timezone
from werkzeug.security import check_password_hash, generate_password_hash
from flask_login import UserMixin
from extensions import db

def now_utc():
    return datetime.now(timezone.utc)

def utc_iso(dt):
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat()

def parse_utc_iso(value):
    return datetime.fromisoformat(value)


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(100))
    age = db.Column(db.Integer)
    height = db.Column(db.Float)
    weight = db.Column(db.Float)
    role = db.Column(db.String(20), nullable=False, default='user')
    is_active = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.String(50), nullable=False, default=lambda: utc_iso(now_utc()))

    food_logs = db.relationship('FoodLog', backref='user', lazy=True, cascade="all, delete-orphan")
    sleep_logs = db.relationship('SleepLog', backref='user', lazy=True, cascade="all, delete-orphan")
    wellbeing_logs = db.relationship('WellbeingLog', backref='user', lazy=True, cascade="all, delete-orphan")
    gym_logs = db.relationship('GymLog', backref='user', lazy=True, cascade="all, delete-orphan")
    reset_tokens = db.relationship('PasswordResetToken', backref='user', lazy=True, cascade="all, delete-orphan")


class PasswordResetToken(db.Model):
    __tablename__ = "password_reset_tokens"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    token = db.Column(db.String(100), unique=True, nullable=False, index=True)
    expires_at = db.Column(db.String(50), nullable=False)
    used_at = db.Column(db.String(50))
    created_at = db.Column(db.String(50), nullable=False, default=lambda: utc_iso(now_utc()))


class FoodLog(db.Model):
    __tablename__ = "food_log"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
    date = db.Column(db.String(20))
    meal = db.Column(db.String(50))
    food = db.Column(db.String(100))
    qty = db.Column(db.Float)
    calories = db.Column(db.Float)
    protein = db.Column(db.Float)
    fat = db.Column(db.Float)
    sugar = db.Column(db.Float)

    __table_args__ = (
        db.Index('idx_food_log_user_date', 'user_id', 'date'),
    )


class SleepLog(db.Model):
    __tablename__ = "sleep_log"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
    date = db.Column(db.String(20))
    hours = db.Column(db.Float)
    quality = db.Column(db.Integer)
    notes = db.Column(db.Text)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'date', name='uq_sleep_user_date'),
        db.Index('idx_sleep_log_user_date', 'user_id', 'date'),
    )


class WellbeingLog(db.Model):
    __tablename__ = "wellbeing_log"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
    date = db.Column(db.String(20))
    activity = db.Column(db.String(100))
    minutes = db.Column(db.Integer)

    __table_args__ = (
        db.Index('idx_wellbeing_log_user_date', 'user_id', 'date'),
    )


class GymLog(db.Model):
    __tablename__ = "gym_log"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
    date = db.Column(db.String(20))
    muscle = db.Column(db.String(50))
    exercise = db.Column(db.String(100))
    sets = db.Column(db.Integer)
    reps = db.Column(db.Integer)
    weight = db.Column(db.Float)
    speed = db.Column(db.Float)
    incline = db.Column(db.Float)
    intensity = db.Column(db.String(50))
    duration = db.Column(db.Float)
    calories = db.Column(db.Float)

    __table_args__ = (
        db.Index('idx_gym_log_user_date', 'user_id', 'date'),
    )


def get_user_by_id(user_id):
    return User.query.get(user_id)


def get_user_by_email(email):
    return User.query.filter(User.email.ilike(email)).first()


def parse_admin_emails():
    raw = os.environ.get("ADMIN_EMAILS", "")
    return {email.strip().lower() for email in raw.split(",") if email.strip()}


def default_role_for_email(email):
    if email.lower() in parse_admin_emails():
        return "admin"
    user_count = User.query.count()
    return "admin" if user_count == 0 else "user"


def claim_legacy_rows(user_id):
    user_count = User.query.count()
    if user_count != 1:
        return

    FoodLog.query.filter(FoodLog.user_id.is_(None)).update({"user_id": user_id})
    SleepLog.query.filter(SleepLog.user_id.is_(None)).update({"user_id": user_id})
    WellbeingLog.query.filter(WellbeingLog.user_id.is_(None)).update({"user_id": user_id})
    GymLog.query.filter(GymLog.user_id.is_(None)).update({"user_id": user_id})
    db.session.commit()


def create_user(name, email, password):
    normalized_email = email.strip().lower()
    existing = get_user_by_email(normalized_email)
    if existing:
        return None, "An account with that email already exists."

    role = default_role_for_email(normalized_email)
    user = User(
        email=normalized_email,
        password_hash=generate_password_hash(password),
        name=name.strip() or normalized_email,
        role=role,
        is_active=1
    )
    db.session.add(user)
    db.session.commit()
    claim_legacy_rows(user.id)
    return user, None


def issue_password_reset_token(email):
    normalized_email = email.strip().lower()
    user = get_user_by_email(normalized_email)
    if not user:
        return None

    PasswordResetToken.query.filter_by(user_id=user.id, used_at=None).update({"used_at": utc_iso(now_utc())})

    token = secrets.token_urlsafe(32)
    expires_at = now_utc() + timedelta(minutes=30)
    reset_token = PasswordResetToken(
        user_id=user.id,
        token=token,
        expires_at=utc_iso(expires_at)
    )
    db.session.add(reset_token)
    db.session.commit()
    return token


def get_valid_password_reset_token(token):
    token_row = PasswordResetToken.query.filter_by(token=token).first()
    if not token_row or token_row.used_at:
        return None
    if parse_utc_iso(token_row.expires_at) < now_utc():
        return None
    return token_row


def consume_password_reset_token(token, new_password):
    token_row = get_valid_password_reset_token(token)
    if not token_row:
        return False

    used_at = utc_iso(now_utc())
    user = User.query.get(token_row.user_id)
    user.password_hash = generate_password_hash(new_password)
    
    token_row.used_at = used_at
    PasswordResetToken.query.filter(
        PasswordResetToken.user_id == token_row.user_id,
        PasswordResetToken.token != token,
        PasswordResetToken.used_at.is_(None)
    ).update({"used_at": used_at})
    
    db.session.commit()
    return True
