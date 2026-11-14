# Astro-Doctor

Astro-Doctor is a prototype crew-health dashboard. The installable Django PWA is the astronaut-facing interface; the existing Streamlit dashboard remains available for operators. Both use the same PostgreSQL database and Django staff accounts.

> **Medical safety:** This prototype and its synthetic thresholds/actions are not clinically validated or approved for flight operations. Do not use it to diagnose, triage, or replace a Crew Medical Officer. Validate the clinical logic, human factors, offline behavior, privacy, and operational procedures before real crew use.

## Features

- Django PWA dashboard with responsive layout, personal trend charts, status summaries, alerts, and daily check-ins.
- Offline check-in queue stored on the device; queued entries sync when the app is online and the operator is signed in. Entries are stored before sending and synced in submission order; retries reuse the same identifier to avoid duplicate records. Dashboard/history are not available offline.
- Streamlit dashboard remains at `/streamlit/` and shares the same database.
- PostgreSQL persistence for mission-day measurements and check-ins.
- CSV and `.xlsx` dataset imports. Import can replace the dataset or append non-overlapping mission days.
- One shared dataset and staff-only access. Create the operator account with Django's `createsuperuser` command.

## Crew profiles

Open **Crew** in the navigation to add astronauts and team members. Profiles include a portrait, call sign, role, agency, nationality, mission, mission start, date of birth, email, biography, and crew status. Staff can view and edit all profiles. Profiles are a personnel directory; the health dashboard still uses one shared dataset.

Portrait uploads accept JPEG, PNG, and WebP up to 5 MB and 20 megapixels. The app resizes portraits to 800 pixels, removes image metadata, and serves them through an authenticated endpoint with caching disabled. Back up the private `media/` directory with the database; do not expose it through a public web server alias.

The interface uses the supplied artwork in `static/backgrounds/` for the page, mission banners, and crew cards.

## My account profile

Click the avatar at the top right to edit your own profile. Display name, title, biography, and photo are optional. The avatar shows initials until you add a photo. Crew users and administrators can update only their own account profile here; the crew directory remains staff-managed.

Choose a file or select **Take a photo** to request camera access. Camera capture requires HTTPS (or localhost), browser support, and permission. Canceling or declining camera access leaves file upload available. A captured photo stays unsaved until you select **Save my profile**. Camera tracks stop after capture, cancellation, or leaving the page. Account photos use the same image validation as crew portraits and are served only to the signed-in owner.

## UI preferences and developer team

Use the footer controls to choose light or dark panels and any of the six supplied backgrounds. Preferences persist across pages and browser sessions and update across tabs. Crew search filters the directory immediately. Profile forms offer portrait previews, biography character counts, saving feedback, and a warning before leaving unsaved edits. Browser storage contains appearance preferences only; form contents are not saved as drafts.

Open **Meet the developers** in the footer to fill five developer slots. Each profile supports a name, role, biography, portrait, email, GitHub link, and website. Staff can add or edit profiles. The database restricts slots to 1–5 and makes each slot unique. Run `python manage.py migrate` after updating the app.

## Dataset training

After uploading data, select **Train dataset** on the health dashboard. The modal fits a statistical baseline (mean and sample standard deviation for the nine health indicators), saves it in PostgreSQL, and applies it to Django and Streamlit analysis. Choose at least 21 initial rows and reserve at least seven later rows for evaluation, so training requires 28 records or more. Without a saved calibration, analysis keeps its original first-21-row baseline.

The report shows the split by mission day, fitted statistics, evaluation rows with directional EWMA drift flags, and rows crossing fixed hard limits. These counts are descriptive checks, not prediction accuracy or evidence of clinical validity. Outcomes are not labeled, and this does not train a diagnostic classifier. Alert thresholds, smoothing, actions, radiation handling, and hard limits remain unchanged. Choose a representative normal period; the report warns about constant indicators, short evaluation segments, and baseline hard-limit crossings.

Every successful CSV/XLSX import (append or replace) clears the saved calibration. Retrain after importing. Check-ins retain the saved baseline; the report describes the evaluation segment at training time. Training never changes uploaded measurements. Staff sign-in is required.

## Dataset format

Upload at least 21 rows. Column names are case-insensitive; include:

```text
day,resting_hr,hrv_rmssd,spo2,grip_kg,resist_min,body_temp,sleep_h,mood,stress
```

`radiation_msv` is optional. It should contain cumulative dose in mSv; if omitted, the dashboard marks radiation dose as unavailable. Each mission day must be a unique positive whole number. Append mode rejects existing day numbers. Replace mode also removes prior check-ins.

## Run locally

Use Python 3.12 or newer supported by the installed Django release, and have PostgreSQL running. Create a database and role, then set the environment variables from `.env.example` in a local `.env` file. Do not commit `.env`.

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env: set a private DJANGO_SECRET_KEY and DATABASE_URL.
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open `http://127.0.0.1:8000/` and sign in. To run the retained Streamlit interface in another terminal:

```sh
streamlit run app.py
```

Streamlit uses the same Django staff login. For production, bind it to localhost and expose it only through the reverse proxy.

## Namecheap VPS deployment (`astrodoctor.space`)

These are Ubuntu-style commands; adapt package and service paths to your VPS image.

1. In Namecheap **Advanced DNS**, point `@` and `www` A records to the VPS public IPv4 address. Allow inbound TCP ports 80 and 443 in the VPS firewall.
2. Install PostgreSQL, Nginx, Python, and Certbot. Create a database and a dedicated local-only role:

   ```sql
   CREATE ROLE astrodoctor LOGIN PASSWORD 'use-a-unique-long-password';
   CREATE DATABASE astrodoctor OWNER astrodoctor;
   ```

3. Put the application on the VPS, create a Python virtual environment, install `requirements.txt`, and create a private `.env` beside `manage.py`. Set `DATABASE_URL` to the local PostgreSQL database, set a randomly generated `DJANGO_SECRET_KEY`, and set the allowed hosts and trusted HTTPS origins as shown in `.env.example`. Keep PostgreSQL bound to localhost unless you have a separately secured remote database.
4. Initialize the database and static files, then create the operator account:

   ```sh
   python manage.py migrate
   python manage.py collectstatic --noinput
   python manage.py createsuperuser
   ```

5. Run Gunicorn on `127.0.0.1:8000` with `config.wsgi:application`. If you want the retained Streamlit dashboard, run it separately on `127.0.0.1:8501`:

   ```sh
   gunicorn --workers 3 --bind 127.0.0.1:8000 config.wsgi:application
   streamlit run app.py --server.address 127.0.0.1 --server.port 8501 --server.baseUrlPath streamlit
   ```

   Configure both commands as supervised services (for example, systemd) so they restart after reboot. Do not expose either application port directly to the internet.

6. Configure Nginx to send `/streamlit/` to `127.0.0.1:8501` with WebSocket upgrade headers; send other requests to `127.0.0.1:8000`. Forward the original `Host` and `X-Forwarded-Proto` headers. Then use Certbot to issue TLS certificates for `astrodoctor.space` and `www.astrodoctor.space`, and redirect HTTP to HTTPS. The Django production settings require HTTPS for login/session cookies.
7. Verify sign-in, dataset upload, check-in save/sync, PWA install, and a database backup/restore before inviting users. Keep regular encrypted PostgreSQL backups and restrict their access; health data is sensitive.

The PWA caches only its offline screen and static assets, not authenticated dashboards or health records. Offline check-ins stay in the browser's IndexedDB until they can sync; avoid shared devices and clear local browser data according to your data-retention policy.
