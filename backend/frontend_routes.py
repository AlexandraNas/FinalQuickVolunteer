from pathlib import Path

from flask import Blueprint, abort, send_from_directory


# ==========================================
# FRONTEND PAGES (HTML, CSS, JS, IMAGES)
# ==========================================
# The website lives in the "frontend" folder. Flask serves it from the
# same address as the API, so the session cookie and CSRF token work.

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

frontend_bp = Blueprint("frontend", __name__)

ASSET_FOLDERS = ("css", "js", "assets")


@frontend_bp.route("/")
def index_page():
    return send_from_directory(FRONTEND_DIR, "index.html")


@frontend_bp.route("/<page>.html")
def html_page(page):
    if not (FRONTEND_DIR / f"{page}.html").is_file():
        abort(404)
    return send_from_directory(FRONTEND_DIR, f"{page}.html")


@frontend_bp.route("/<folder>/<path:filename>")
def asset_file(folder, filename):
    if folder not in ASSET_FOLDERS:
        abort(404)
    return send_from_directory(FRONTEND_DIR / folder, filename)
