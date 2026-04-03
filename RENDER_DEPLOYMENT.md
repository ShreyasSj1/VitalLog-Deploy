# Render Deployment

This app is ready to deploy on Render as a Python web service backed by PostgreSQL.

## Files added for Render

- `render.yaml`: Render service configuration
- `requirements.txt`: includes `gunicorn` and `psycopg[binary]`
- `schema_postgres.sql`: PostgreSQL schema used when `DATABASE_URL` points to Postgres

## Recommended setup

1. Push this repo to GitHub.
2. In Render, create a new `Web Service` from the repo.
3. Render will detect `render.yaml` automatically.
4. Create a PostgreSQL database in Render or use an external Postgres provider like Neon/Supabase.
5. Set the `DATABASE_URL` environment variable on the web service to the Postgres connection string.

## Required environment variables

- `DATABASE_URL`
  Use a PostgreSQL connection string in production.
- `SECRET_KEY`
  Render will generate this automatically from `render.yaml`.
- `FLASK_DEBUG=false`
  Already set in `render.yaml`.

## Start command

Render will start the app with:

```bash
gunicorn app:app
```

## First deploy behavior

On startup, the app runs `init_db()`.

- If `DATABASE_URL` is PostgreSQL, it initializes the schema from `schema_postgres.sql`.
- If `DATABASE_URL` is not set, it falls back to local SQLite, which is not recommended on Render.

## Migrating existing SQLite data

If you want to move your current local data into PostgreSQL:

```bash
export DATABASE_URL="your-postgres-connection-string"
python3 scripts/migrate_sqlite_to_postgres.py
```

Optionally set a custom SQLite source path:

```bash
export SQLITE_PATH="/path/to/fitness.db"
python3 scripts/migrate_sqlite_to_postgres.py
```

## Important note

Do not rely on SQLite for Render production deployments. Render instances have ephemeral filesystems, so PostgreSQL should be used for persistent data.
