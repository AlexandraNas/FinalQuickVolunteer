# Putting QuickVolunteer online (Aiven + Render)

- **Aiven** (aiven.io) hosts the MySQL database.
- **Render** (render.com) runs the Flask app and the website, and gives you the public link.

Do the steps in this order: Aiven first, because Render needs the database details.

## 1. Create the database on Aiven

1. Go to **console.aiven.io** and sign up (free, no card needed).
2. Click **Create service** → **MySQL** → choose the **Free** plan.
3. Pick a region close to you (for example Europe), give it a name such as `quickvolunteer-db` and click **Create**.
4. Wait until the status shows **Running** (a few minutes).
5. On the service **Overview** page, find **Connection information**. Keep this page open; you need:
   - Host
   - Port
   - User (usually `avnadmin`)
   - Password (click the eye icon)
   - Database name (usually `defaultdb`)

Aiven requires an encrypted (SSL) connection. The MySQL connector used by the app does this on its own.

## 2. Load the tables and demo data (from your Mac, once)

Open Terminal in the project folder (the folder that contains `backend` and `database`):

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

export MYSQL_HOST="the Aiven host"
export MYSQL_PORT="the Aiven port"
export MYSQL_USER="avnadmin"
export MYSQL_PASSWORD="the Aiven password"
export MYSQL_DATABASE="defaultdb"

python3 database/load_schema.py
python3 database/seeds/seed_demo.py
export DEMO_PASSWORD="choose at least 12 characters"
python3 database/seeds/demo_logins.py
```

You should see `Done: 15 tables created.` If you run `load_schema.py` again it stops, so it can never wipe your data.

Never put these passwords in the code or on GitHub.

## 3. Create the web service on Render

1. Go to **render.com**, sign up with GitHub and click **New** → **Web Service**.
2. Choose your QuickVolunteer GitHub repo.
3. Fill in:
   - **Language:** Python 3
   - **Build command:** `pip install -r backend/requirements.txt`
   - **Start command:** `gunicorn --chdir backend app:app`
   - **Instance type:** Free
4. Under **Environment variables**, add:

| Name | Value |
|---|---|
| `MYSQL_HOST` | the Aiven host |
| `MYSQL_PORT` | the Aiven port |
| `MYSQL_USER` | `avnadmin` |
| `MYSQL_PASSWORD` | the Aiven password |
| `MYSQL_DATABASE` | `defaultdb` |
| `FLASK_SECRET_KEY` | click **Generate** |
| `SESSION_COOKIE_SECURE` | `1` |
| `TRUST_PROXY` | `1` |

5. Click **Create Web Service**. When the log says it is live, open the link at the top (for example `https://quickvolunteer.onrender.com`).

## 4. Check it works

1. Open the link and log in with a demo account (password = your `DEMO_PASSWORD`):
   - `james.carter.demo@example.com` (volunteer)
   - `emma.wilson.demo@example.com` (help seeker)
   - `admin.demo@example.com` (administrator)
2. If you see the demo tasks and your name in the header, the database is connected.
3. If login fails and the site shows sample data only, check the environment variables in Render (a typo in the host or password is the usual cause) and look at the **Logs** tab.

## Good to know

- **Free Render apps sleep** after about 15 minutes without visitors. The first visit then takes up to a minute. Open the link a minute before a demo.
- **Aiven may switch off a free database** that nobody uses for a while. It emails a warning first; switch it back on from the console.
- **ID documents uploaded on the free Render plan are deleted when the app restarts.** Check verification requests soon after they arrive.
- **Every push to GitHub redeploys the site.** The database keeps its data.
- **On your own computer nothing changes:** leave `SESSION_COOKIE_SECURE` and `TRUST_PROXY` unset and run `python backend/app.py` as before.
