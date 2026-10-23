from pathlib import Path

from flask import Blueprint, Response, abort, send_from_directory


# ==========================================
# FRONTEND PAGES (HTML, CSS, JS, IMAGES)
# ==========================================
# The website lives in the "frontend" folder. Flask serves it from the
# same address as the API, so the session cookie and CSRF token work.

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

frontend_bp = Blueprint("frontend", __name__)

ASSET_FOLDERS = ("css", "js", "assets")


def serve_page(name):
    """Send an HTML page marked as served by Flask (class "qv-server").

    The page then keeps its built-in demo content hidden until api.js has
    loaded the real data from the database, so demo tasks and names never
    show on the live site.
    """
    path = FRONTEND_DIR / name
    if not path.is_file():
        abort(404)
    html = path.read_text(encoding="utf-8").replace(
        '<html lang="en">', '<html lang="en" class="qv-server">', 1
    )
    return Response(html, mimetype="text/html")


@frontend_bp.route("/")
def index_page():
    return serve_page("index.html")


@frontend_bp.route("/<page>.html")
def html_page(page):
    return serve_page(f"{page}.html")


@frontend_bp.route("/<folder>/<path:filename>")
def asset_file(folder, filename):
    if folder not in ASSET_FOLDERS:
        abort(404)
    return send_from_directory(FRONTEND_DIR / folder, filename)
