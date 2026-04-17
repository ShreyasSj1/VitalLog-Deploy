# Render Deployment

This Flask app is ready to deploy on Render with PostgreSQL.

## Setup path

1. Push this repo to GitHub.
2. In Render, create a new `Postgres` database.
3. In Render, create a new `Web Service` from this repo.
4. Either let Render read `render.yaml`, or set the same values manually.
5. Set `DATABASE_URL` to the Render Postgres internal connection URL.
6. Deploy the web service.

## Service settings

- Build Command: `pip install -r requirements.txt`
- Start Command: `gunicorn app:app`
- Runtime: Python

## Required environment variables

- `DATABASE_URL`
- `SECRET_KEY`
- `FLASK_DEBUG=false`
- `GROQ_API_KEY` (Required for the AI chatbot)

## Notes

- The app already binds to `0.0.0.0` and uses `PORT`, which Render requires for public web services.
- On startup, the app initializes PostgreSQL tables from `schema_postgres.sql` when `DATABASE_URL` is Postgres.
- Do not use SQLite in Render production because the filesystem is ephemeral.

## Optional migration

To move your current SQLite data into Postgres later:

```bash
export DATABASE_URL="your-render-postgres-url"
python3 scripts/migrate_sqlite_to_postgres.py
```
