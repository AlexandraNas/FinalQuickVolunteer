
import os
from pathlib import Path

from flask import Flask, jsonify, render_template
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_wtf.csrf import CSRFProtect, generate_csrf

from db import get_db_connection
from auth import auth_bp
from task_routes import task_bp
from admin_routes import admin_bp
from skills_routes import skills_bp
from review_routes import review_bp
from verification_routes import verification_bp
from messaging_routes import messaging_bp
from notification_routes import notification_bp
from frontend_routes import frontend_bp
from profile_routes import profile_bp
from helpers import VERIFIED_SQL


# ==========================================
# FLASK APPLICATION CONFIGURATION
# ==========================================

BASE_DIR = Path(__file__).resolve().parent.parent

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "static")
)

app.config.update(
    SECRET_KEY=os.environ.get("FLASK_SECRET_KEY"),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    # Online (https) set SESSION_COOKIE_SECURE=1; leave it unset on your computer.
    SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE") == "1",
    MAX_CONTENT_LENGTH=6 * 1024 * 1024  # ID document uploads (5 MB file)
)

# Behind a hosting proxy such as Render, trust its https and client address headers.
if os.environ.get("TRUST_PROXY") == "1":
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

if not app.config["SECRET_KEY"]:
    raise RuntimeError(
        "Set FLASK_SECRET_KEY before starting Flask"
    )


# ==========================================
# REGISTER BLUEPRINTS AND CSRF PROTECTION
# ==========================================

app.register_blueprint(auth_bp)
app.register_blueprint(task_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(skills_bp)
app.register_blueprint(review_bp)
app.register_blueprint(verification_bp)
app.register_blueprint(messaging_bp)
app.register_blueprint(notification_bp)
app.register_blueprint(frontend_bp)
app.register_blueprint(profile_bp)

csrf = CSRFProtect(app)


# ==========================================
# MYSQL TASK QUERY
# ==========================================

def fetch_open_tasks():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(f"""
            SELECT
                t.task_id,
                t.title,
                t.description,
                t.delivery_mode,
                t.estimated_minutes,
                t.location_text,
                t.postcode,
                t.status,
                t.category_id,
                t.deadline_at,
                t.created_at,
                t.creator_id,
                u.first_name AS creator_first_name,
                LEFT(u.last_name, 1) AS creator_last_initial,
                {VERIFIED_SQL.format(alias='u')} AS creator_verified,
                c.category_name
            FROM tasks AS t
            JOIN task_categories AS c
                ON t.category_id = c.category_id
            JOIN users AS u
                ON u.user_id = t.creator_id
            WHERE t.status = 'open'
              AND t.deadline_at > NOW()
              AND u.account_status = 'active'
            ORDER BY t.deadline_at, t.task_id
        """)

        tasks = cursor.fetchall()

        # Dates as ISO text so the website can read them.
        # Only the first name and last initial are shared.
        for task in tasks:
            task["creator_verified"] = bool(task["creator_verified"])
            for field in ("deadline_at", "created_at"):
                if task[field] is not None:
                    task[field] = task[field].isoformat()

        return tasks

    finally:
        cursor.close()
        connection.close()


# The home page ("/") and the other website pages are served by
# frontend_routes.py from the "frontend" folder.


# ==========================================
# TASKS PAGE
# ==========================================

@app.route("/tasks")
def tasks_page():
    tasks = fetch_open_tasks()
    return render_template("tasks.html", tasks=tasks)


# ==========================================
# REST API - GET TASKS
# ==========================================

@app.route("/api/tasks", methods=["GET"])
def tasks_api():
    return jsonify(fetch_open_tasks())



# ==========================================
# REST API - GET TASK CATEGORIES
# ==========================================

@app.route("/api/categories", methods=["GET"])
def categories_api():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                category_id,
                category_name
            FROM task_categories
            ORDER BY category_name
        """)

        categories = cursor.fetchall()
        return jsonify(categories), 200

    finally:
        cursor.close()
        connection.close()


# ==========================================
# CSRF TOKEN ENDPOINT
# ==========================================

@app.route("/api/csrf-token", methods=["GET"])
def csrf_token():
    return jsonify({
        "csrf_token": generate_csrf()
    })


# ==========================================
# RUN FLASK
# ==========================================

if __name__ == "__main__":
    app.run(debug=False)
