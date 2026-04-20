"""
migrations.py — Safe, idempotent schema migration helper.

Runs on every startup (called from app.py after db.create_all()).
Uses raw SQL with IF NOT EXISTS / ADD COLUMN IF NOT EXISTS so it is safe
to call against both fresh databases and already-migrated ones.
"""
from extensions import db


def run_migrations():
    """Apply all pending schema changes that SQLAlchemy cannot handle via
    create_all() (i.e. adding columns to *existing* tables).
    """
    engine = db.engine
    dialect = engine.dialect.name  # 'sqlite' or 'postgresql'

    with engine.connect() as conn:
        # ── Phase 5A: per-user goal columns on `users` ──────────────────
        if dialect == "postgresql":
            conn.execute(db.text(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS goal_calories FLOAT"
            ))
            conn.execute(db.text(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS goal_protein FLOAT"
            ))
            conn.execute(db.text(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS goal_fat FLOAT"
            ))
            conn.execute(db.text(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS goal_sugar FLOAT"
            ))
        else:
            # SQLite does not support ADD COLUMN IF NOT EXISTS — check first
            existing = {
                row[1]
                for row in conn.execute(db.text("PRAGMA table_info(users)"))
            }
            for col in ("goal_calories", "goal_protein", "goal_fat", "goal_sugar"):
                if col not in existing:
                    conn.execute(db.text(f"ALTER TABLE users ADD COLUMN {col} FLOAT"))

        conn.commit()
