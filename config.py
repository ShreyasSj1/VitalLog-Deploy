import os
from pathlib import Path

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-production")
    
    # SQLAlchemy Configuration
    default_db_path = Path(__file__).parent / "fitness.db"
    raw_db_url = os.environ.get("DATABASE_URL", f"sqlite:///{default_db_path}")

    # Render/Heroku-style URLs may be "postgres://...".
    # SQLAlchemy 2 defaults to psycopg2 for "postgresql://..." unless a driver is explicit.
    # We install psycopg (v3), so force the URL to use the psycopg driver.
    if raw_db_url.startswith("postgres://"):
        raw_db_url = raw_db_url.replace("postgres://", "postgresql+psycopg://", 1)
    elif raw_db_url.startswith("postgresql://"):
        raw_db_url = raw_db_url.replace("postgresql://", "postgresql+psycopg://", 1)
    
    SQLALCHEMY_DATABASE_URI = raw_db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    FIREBASE_API_KEY = os.environ.get("FIREBASE_API_KEY", "")
    FIREBASE_AUTH_DOMAIN = os.environ.get("FIREBASE_AUTH_DOMAIN", "")
    FIREBASE_PROJECT_ID = os.environ.get("FIREBASE_PROJECT_ID", "")
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
