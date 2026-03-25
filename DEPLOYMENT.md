# Deployment Guide

## Backend on Render

1. Push this repository to GitHub.
2. Create a new Render Web Service from the repo root.
3. Render settings:
   - Runtime: `Python`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
4. Set environment variables:
   - `SECRET_KEY`: any long random string
   - `CORS_ORIGINS`: your Vercel domain, for example `https://your-app.vercel.app`
   - `DATABASE_PATH`: `fitness.db` or a mounted disk path such as `/var/data/fitness.db`
5. Optional but recommended for SQLite:
   - Attach a persistent disk in Render and point `DATABASE_PATH` to that disk path.
6. Deploy and copy the Render URL.

## Frontend on Vercel

1. In [`frontend/config.js`](/Users/sj/Desktop/Stuff/fitness-web%20test/frontend/config.js), replace the local URL with your Render backend URL.
2. Import the same repo into Vercel.
3. Set the project root directory to `frontend`.
4. Deploy.

## Verify

1. Open `https://your-backend.onrender.com/api/health` and confirm you get JSON.
2. Open the Vercel site and register or login.
3. Confirm these flows work from the deployed frontend:
   - Dashboard load
   - Add nutrition entry
   - Add workout entry
   - Save sleep entry
   - Save wellbeing entry

## Notes

- The frontend uses `fetch(..., { credentials: "include" })`, so CORS must allow your Vercel origin.
- In production, Flask session cookies are configured for secure cross-site use.
- Avoid hardcoding the backend URL anywhere except [`frontend/config.js`](/Users/sj/Desktop/Stuff/fitness-web%20test/frontend/config.js).
