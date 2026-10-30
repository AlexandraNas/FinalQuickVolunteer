# QuickVolunteer

QuickVolunteer is a micro volunteering website. Neighbours post small tasks of 15 to 60 minutes, in person or remote, and other members offer to help.

**Live website:** https://finalquickvolunteer.onrender.com

The first visit can take up to a minute to load; after that it is quick.

---

## How to log in

Every demo account uses the same password. For safety it is not stored on GitHub: it is given with the module submission.

| Name | Email | Role |
|---|---|---|
| Nadia Rossi | nadia.rossi.demo@example.com | Help seeker (asks for help) |
| Adam Foster | adam.foster.demo@example.com | Volunteer, helps remotely |
| Sophie Williams | sophie.williams.demo@example.com | Volunteer, helps in person |
| Sofia Martinez | sofia.martinez.demo@example.com | Both (asks for and gives help) |
| Daniel Brooks | daniel.brooks.demo@example.com | Administrator |

Extra accounts: emma.wilson.demo@example.com (help seeker), james.carter.demo@example.com (volunteer) and admin.demo@example.com (administrator).

All demo dates are set as if today were **15 March 2027**, so the demo tasks are still open.

You can also create your own account with **Sign up**.

---

## What each user can do

### Visitor (not logged in)
- Read the Home, Impact, About, FAQs, Volunteer guide, Privacy Policy and Terms of Use pages.
- Browse and search tasks on **Offer Support**, and open a task to read the details.
- Use the **Accessibility tools** bar: read aloud, bigger text, easy to read font, line spacing, colour themes, highlighted links, reading ruler, screen mask and big cursor.
- Sign up or log in. Posting a request or offering to help asks you to log in first.

### Every member
- Sign up and set up a profile: postcode (with a map of the area), how you take part, skills and availability.
- Edit your own profile and preferences on **My profile**. Members cannot edit a request after posting it.
- Ask to be **verified** by uploading an ID document. Verified members get a badge.
- See notifications in the bell, for example new offers, accepted offers and finished tasks.
- Report a concern about a task or a member, and use the Contact form.

### Help seeker (asks for help)
- **Ask for Help:** post a request with a title, description, type of help, skills, in person or remote, postcode, time needed and a "Complete by" date.
- **My requests:** see the offers on each request, read each volunteer's profile, then accept or decline.
- Close a request, mark a task as done, and leave a review for the volunteer.

### Volunteer (gives help)
- **Offer Support:** search tasks and filter by type of help, duration, distance, postcode or area, and verified members. A map shows the tasks around the postcode.
- Tasks that match your skills come first.
- Offer to help, withdraw an offer, follow your offers on **My tasks**, mark a task as done and leave a review.

### Both
- One account can ask for help and offer help, with every feature above.

### Administrator
- The menu shows **Home** (the admin dashboard), **Ask for Help**, **Offer Support**, **Impact** and **About**.
- **Verification:** open each ID document, then approve or reject it. The document is deleted after the decision.
- **Members:** search, sort (newest, oldest, name, most completed tasks) and filter (taking part as, verified, account). Suspend or reactivate an account.
- **Reported concerns:** read each report and change its status.
- **Profile changes:** check the details members have changed.
- **Reviews:** hide a review that breaks the guidelines, or show it again.
- **Offer Support:** view any task and **delete** a request. The requester and any volunteers who offered are told. Admins cannot offer to help or edit a task.
- **Ask for Help, Contact and Report:** admins can view these forms to help members, but cannot send them.
- **My profile:** name and email only.

---

## A tour for tutors

Each step takes a minute or two. Use the live website and the logins above.

1. **As a visitor:** open the site, try **Accessibility tools**, then open **Offer Support**. Type `E8 1AB` in **Postcode or area** to see the nearby tasks and the map.
2. **As Nadia (help seeker):** log in, open **Ask for Help** and post a request. Then open **My requests** to see it and the offers on her other requests.
3. **As Sophie (volunteer):** log in, open **Offer Support**, open Nadia's new task and click **Offer to help**. Follow it on **My tasks**.
4. **As Nadia again:** open **My requests**, accept Sophie's offer, and when the task is done mark it as complete and leave a review.
5. **As Sophie:** mark the task as done too, then see the review on **My profile**.
6. **As Daniel (administrator):** log in to reach the admin dashboard. Try the **Members** search, sort and filters, look at **Reported concerns** and **Reviews**, then open a task from **Offer Support** and delete it.

---

## How the team worked on the code

We worked on the code offline, together in class sessions and through our shared OneDrive folder, rather than each of us pushing to GitHub. To keep one clean, working version of the project, we agreed that Alexandra would be the only one to upload to this repository: when a part was ready and tested, it was combined on her computer and uploaded here.


---

## How the project is organised

| Folder | What it holds |
|---|---|
| `frontend/` | The website: HTML pages, `css/styles.css`, `js/` and `assets/` |
| `backend/` | The Flask API (Python) that serves the website and talks to the database |
| `database/` | `schema.sql` (15 tables) and the demo data scripts in `seeds/` |
| `tests/` | 104 automated API tests (the runner reports 320 runs because three modules reuse the core test class). Full output: `evidence/testing/unittest_run_27Oct2026.log` |

The live site runs on **Render** and the MySQL database on **Aiven**. `DEPLOY_RENDER.md` explains the set up and `CONNECTING_FRONTEND.md` explains how the website talks to the API.

## Run it on your own computer

1. Install Python 3 and MySQL, then run `pip install -r backend/requirements.txt`.
2. Create the database with `database/schema.sql`, then run `database/seeds/seed_demo.py` and `database/seeds/demo_logins.py`.
3. Set `MYSQL_PASSWORD`, `FLASK_SECRET_KEY` and `DEMO_PASSWORD`, then run `python backend/app.py` and open http://127.0.0.1:5000.
4. To run the tests: `MYSQL_DATABASE=quickvolunteer_test_db python -m unittest tests.test_backend tests.test_audit tests.test_messaging tests.test_notifications tests.test_sprint3`.
