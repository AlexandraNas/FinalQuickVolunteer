# Running the website with the Flask back end

The website now lives in `frontend/` and Flask serves it. Pages and API share one address (http://127.0.0.1:5000), so the login cookie and the CSRF token work without any extra set up.

## Run it locally
1. Start MySQL and load the database once:
   ```
   mysql -u root -p < database/schema.sql
   ```
2. Install the Python packages:
   ```
   pip install -r backend/requirements.txt
   ```
3. Set the secrets in the terminal (never in JavaScript or in Git):
   ```
   export MYSQL_PASSWORD="your MySQL app user password"
   export FLASK_SECRET_KEY="a long random string"
   ```
4. Add the categories, the demo data and the demo logins:
   ```
   python database/seeds/seed_categories.py
   python database/seeds/seed_demo.py
   export DEMO_PASSWORD="choose at least 12 characters"
   python database/seeds/demo_logins.py
   ```
5. Start Flask and open http://127.0.0.1:5000
   ```
   python backend/app.py
   ```

## Demo logins (password = your DEMO_PASSWORD)
| Email | Account |
|---|---|
| nadia.rossi.demo@example.com | Persona: Nadia, help seeker |
| adam.foster.demo@example.com | Persona: Adam, volunteer (remote) |
| sophie.williams.demo@example.com | Persona: Sophie, volunteer (in person) |
| daniel.brooks.demo@example.com | Persona: Daniel, administrator |
| emma.wilson.demo@example.com | Help seeker |
| james.carter.demo@example.com | Volunteer |
| sofia.martinez.demo@example.com | Both |
| admin.demo@example.com | Administrator |

## How the connection works
- `frontend/js/api.js` checks `/api/csrf-token` when a page opens. If Flask answers, every form and list uses the API. If not (GitHub Pages, Live Server), the site keeps working as the demo prototype from `js/main.js`.
- Every POST, PATCH and PUT sends the `X-CSRFToken` header. The session is a Flask cookie. No password is stored in the browser.
- `backend/frontend_routes.py` serves the HTML pages and the `css`, `js` and `assets` folders only, so Python files and settings can never be downloaded.

## Page to API map
| Page | API |
|---|---|
| signup.html | POST /api/register (account type "both"), then POST /api/login |
| login.html | POST /api/login, GET /api/me |
| header, Log out | GET /api/me, POST /api/logout, GET /api/notifications |
| onboarding.html, profile.html | GET /api/skills, PUT /api/users/me/skills, GET and POST /api/verifications |
| find-a-task.html, dashboard.html | GET /api/tasks, GET /api/categories, GET /api/tasks/{id}/skills |
| task.html | POST /api/tasks/{id}/apply |
| post-request.html | POST /api/tasks, PUT /api/tasks/{id}/skills |
| my-requests.html, request.html | GET /api/my-tasks, GET /api/tasks/{id}/applications, PATCH /api/applications/{id}/decision, PATCH /api/tasks/{id}/cancel |
| my-tasks.html | GET /api/my-applications |
| review.html | PATCH /api/tasks/{id}/complete, POST /api/reviews |
| report.html | POST /api/reports |
| admin.html | GET and PATCH /api/admin/verifications, GET and PATCH /api/admin/reports |

## Sprint 3 additions
| Page | API |
|---|---|
| profile.html | GET /api/users/me/profile, PATCH /api/users/me (admins are notified to check the change), POST /api/verifications (ID upload) |
| task.html, request.html | GET /api/users/{id}/summary (member summary before applying or accepting) |
| my-tasks.html | DELETE /api/applications/{id} (withdraw an offer), activity history |
| report.html | POST /api/reports with target type user, task or other, and contact_allowed |
| admin.html | GET /api/admin/members, PATCH /api/admin/users/{id}/status, GET /api/admin/reviews, GET /api/admin/verifications/{id}/document |

## Accessibility tools bar
- `js/accessibility.js` is loaded in the `<head>` of every page, so saved choices apply before the page is drawn.
- Tools: read aloud (with speed), text size 100% to 150%, easy to read font, more space between lines, Standard, High contrast, Dark and Soft cream colours, highlight links, reading ruler, screen mask, big cursor, Reset all.
- Choices are saved in the visitor's browser (`localStorage` key `qv_accessibility`). No API call and no database change, so it also works for visitors who are not logged in and on GitHub Pages.
- Every page also has a "Skip to main content" link that appears when you press Tab.
- Its styles are the "Accessibility tools" block at the end of `css/styles.css`. When you add a new font size elsewhere in the file, add a matching `html.qv-text` rule there so it grows with bigger text.

## Later features (not built yet)
- Changing language (the `users.preferred_language` column is ready for it), messages between members, email or text notifications, profile photo, preferred connections, volunteer levels, DBS checks.

## Updating the website copy
The website is also kept on its own (QuickVolunteer-website). After changing it, copy its `index.html`, other `.html` pages and the `css`, `js` and `assets` folders into `frontend/` here, replacing the old ones. Both copies should always match.
