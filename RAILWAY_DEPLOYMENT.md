# Railway Deployment

This Flask app is ready to deploy on Railway with PostgreSQL.

## What was prepared

- `railway.json`
  Uses Railway's `RAILPACK` builder and starts the app with Gunicorn.
- `requirements.txt`
  Includes `gunicorn` and `psycopg[binary]`.
- `schema_postgres.sql`
  PostgreSQL schema used when `DATABASE_URL` points to Postgres.
- `/health`
  Healthcheck endpoint for Railway deployments.

## Railway setup path

1. Push this repo to GitHub.
2. In Railway, create a new project from the GitHub repo.
3. Add a PostgreSQL database service to the same Railway project.
4. In your app service, add a variable reference for `DATABASE_URL` from the Postgres service.
5. Set `SECRET_KEY`.
6. Deploy the app.
7. Generate a public domain from the Railway service settings.

## Required variables

- `DATABASE_URL`
  Reference this from the Railway PostgreSQL service.
- `SECRET_KEY`
  Set this manually in Railway.

## Runtime details

- Build/Deploy: Railway uses Railpack by default for supported languages, and `railway.json` can override build and deploy settings. This repo includes a `railway.json` with `builder: "RAILPACK"`. Source: [Railpack docs](https://docs.railway.com/builds/nixpacks), [Config as Code](https://docs.railway.com/config-as-code/reference)
- Start command: Railway can auto-detect a start command, but custom start commands may be set in service settings or in config-as-code. This repo sets `gunicorn app:app --bind 0.0.0.0:$PORT`. Source: [Set a Start Command](https://docs.railway.com/deployments/start-command), [Build and Start Commands](https://docs.railway.com/builds/build-and-start-commands)
- Healthcheck: Railway can query a configured health endpoint and expects a `200` response. This repo exposes `/health`. Source: [Healthchecks](https://docs.railway.com/reference/healthchecks)
- PostgreSQL: Railway's PostgreSQL service provides `DATABASE_URL`, which many libraries can use directly. Source: [PostgreSQL guide](https://docs.railway.com/guides/postgresql)

## First deploy notes

On startup, the app runs `init_db()`.

- With PostgreSQL, it initializes tables from `schema_postgres.sql`.
- Without `DATABASE_URL`, it falls back to SQLite, which is not recommended for Railway production usage.

## Migrating old SQLite data

If you want to move your current local SQLite data to Railway Postgres:

```bash
export DATABASE_URL="your-railway-postgres-url"
python3 scripts/migrate_sqlite_to_postgres.py
```

Optional custom SQLite path:

```bash
export SQLITE_PATH="/path/to/fitness.db"
python3 scripts/migrate_sqlite_to_postgres.py
```

## Recommended Railway checklist

- App service created from GitHub repo
- PostgreSQL service added
- `DATABASE_URL` variable referenced into the app service
- `SECRET_KEY` set
- deployment succeeds
- `/health` returns 200
- login/register works
- food, sleep, wellbeing, gym logs save successfully
