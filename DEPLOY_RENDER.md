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

## 2. Tables and demo data: Render does this for you

The first time the app starts on Render, `database/setup_online.py` creates the 15 tables, the demo data and the demo logins in the empty Aiven database. On every later start it sees the tables and does nothing, so data is never overwritten.

All demo dates are set as if today were **15 March 2027**, so the demo tasks stay open during your presentation. To use another date, add `DEMO_NOW` (for example `2027-05-01 10:00:00`) in Render before the first start.

**Starting again with fresh demo data:** add `RESET_DATABASE` = `yes-delete-everything` in Render's Environment and save. Render redeploys, deletes every table and creates the demo data again. **Then remove `RESET_DATABASE` straight away**, or it will wipe the database on every restart. This deletes everything, including accounts and tasks people created.

(You can also load them from your own computer with `database/load_schema.py` and the seed scripts, but many university and office networks block database ports, so the Render way is easier.)

## 3. Create the web service on Render

1. Go to **render.com**, sign up with GitHub and click **New** → **Web Service**.
2. Choose your QuickVolunteer GitHub repo.
3. Fill in:
   - **Language:** Python 3
   - **Build command:** `pip install -r backend/requirements.txt`
   - **Start command:** `python database/setup_online.py; gunicorn --chdir backend app:app`
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
| `DEMO_PASSWORD` | a password for the demo logins (12+ characters) |

5. Click **Create Web Service**. When the log says it is live, open the link at the top (for example `https://quickvolunteer.onrender.com`).

## 4. Check it works

1. In the **Logs** tab you should see `Setup: 15 tables created.` and `Ready: daniel.brooks.demo@example.com (administrator)` on the first start.
2. Open the link and log in with a demo account (password = your `DEMO_PASSWORD`). The team's personas:
   - `nadia.rossi.demo@example.com` (Nadia, help seeker)
   - `adam.foster.demo@example.com` (Adam, volunteer, remote)
   - `sophie.williams.demo@example.com` (Sophie, volunteer, in person)
   - `daniel.brooks.demo@example.com` (Daniel, administrator)

   Also available: `emma.wilson.demo@example.com` (help seeker), `james.carter.demo@example.com` (volunteer), `sofia.martinez.demo@example.com` (both) and `admin.demo@example.com` (administrator).
3. If you see the demo tasks and your name in the header, the database is connected.
4. If login fails and the site shows sample data only, check the environment variables in Render (a typo in the host or password is the usual cause) and look at the **Logs** tab.

## Good to know

- **Free Render apps sleep** after about 15 minutes without visitors. The first visit then takes up to a minute. Open the link a minute before a demo.
- **Aiven may switch off a free database** that nobody uses for a while. It emails a warning first; switch it back on from the console.
- **ID documents uploaded on the free Render plan are deleted when the app restarts.** Check verification requests soon after they arrive.
- **Every push to GitHub redeploys the site.** The database keeps its data.
- **On your own computer nothing changes:** leave `SESSION_COOKIE_SECURE` and `TRUST_PROXY` unset and run `python backend/app.py` as before.
