import os
import secrets
from pathlib import Path

import mysql.connector
from flask import Blueprint, jsonify, request, send_file, session

from auth import roles_required
from db import get_db_connection
from helpers import audit, notify, notify_admins, short_name


verification_bp = Blueprint("verification", __name__)


# ==========================================
# PROFILE VERIFICATION WITH AN ID DOCUMENT
# ==========================================
# Verification is optional. A member who asks for it uploads a photo or scan
# of an ID document. The file is stored in a private folder that the website
# never serves; only administrators can open it. After the decision the file
# is deleted and only the result is kept. Verified members get a badge.

UPLOAD_DIR = Path(
    os.environ.get(
        "QV_PRIVATE_UPLOAD_DIR",
        Path(__file__).resolve().parent.parent / "private_uploads"
    )
)
MAX_DOCUMENT_BYTES = 5 * 1024 * 1024

# Accepted files, checked by their first bytes (not just the name).
FILE_SIGNATURES = {
    ".jpg": (b"\xff\xd8\xff",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".pdf": (b"%PDF",),
}
CONTENT_TYPES = {".jpg": "image/jpeg", ".png": "image/png", ".pdf": "application/pdf"}


def detect_extension(header):
    for extension, signatures in FILE_SIGNATURES.items():
        if any(header.startswith(sig) for sig in signatures):
            return extension
    return None


def delete_document(reference):
    if not reference:
        return
    path = (UPLOAD_DIR / reference).resolve()
    if path.parent == UPLOAD_DIR.resolve() and path.is_file():
        path.unlink()


@verification_bp.route("/api/verifications", methods=["POST"])
@roles_required("volunteer", "help_seeker", "both")
def request_verification():
    document = request.files.get("document")

    if document is None or not document.filename:
        return jsonify({
            "error": "Please upload a photo or scan of your ID document"
        }), 400

    content = document.read(MAX_DOCUMENT_BYTES + 1)

    if len(content) > MAX_DOCUMENT_BYTES:
        return jsonify({"error": "The file must be 5 MB or smaller"}), 400

    extension = detect_extension(content[:8])

    if extension is None:
        return jsonify({
            "error": "Please upload a JPG, PNG or PDF file"
        }), 400

    user_id = session["user_id"]

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    saved_path = None

    try:
        connection.start_transaction()

        cursor.execute("""
            SELECT user_id, first_name, last_name
            FROM users
            WHERE user_id = %s
            FOR UPDATE
        """, (user_id,))
        user = cursor.fetchone()

        cursor.execute("""
            SELECT verification_id, status
            FROM user_verifications
            WHERE user_id = %s
              AND status IN ('pending', 'approved')
            ORDER BY verification_id DESC
            LIMIT 1
        """, (user_id,))

        existing = cursor.fetchone()

        if existing:
            connection.rollback()
            return jsonify({
                "error": "Verification already pending or approved",
                "status": existing["status"]
            }), 409

        # Random private file name: never the user's own file name.
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        reference = f"{secrets.token_hex(16)}{extension}"
        saved_path = UPLOAD_DIR / reference
        saved_path.write_bytes(content)

        cursor.execute("""
            INSERT INTO user_verifications (
                user_id, verification_method, evidence_reference, status
            )
            VALUES (%s, 'identity_document', %s, 'pending')
        """, (user_id, reference))

        verification_id = cursor.lastrowid

        notify_admins(
            cursor,
            "ID document to check",
            f"Member #{user_id} ({short_name(user['first_name'], user['last_name'])}) "
            "asked for profile verification."
        )

        connection.commit()

        return jsonify({
            "message": "Verification request submitted",
            "verification_id": verification_id,
            "status": "pending"
        }), 201

    except Exception:
        connection.rollback()
        if saved_path is not None and saved_path.exists():
            saved_path.unlink()
        raise

    finally:
        cursor.close()
        connection.close()


@verification_bp.route("/api/verifications/me", methods=["GET"])
@roles_required("volunteer", "help_seeker", "both")
def my_verifications():
    user_id = session["user_id"]

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                verification_id,
                verification_method,
                status,
                submitted_at,
                reviewed_at
            FROM user_verifications
            WHERE user_id = %s
            ORDER BY submitted_at DESC, verification_id DESC
        """, (user_id,))

        verifications = cursor.fetchall()

        for verification in verifications:
            for field in ("submitted_at", "reviewed_at"):
                if verification[field] is not None:
                    verification[field] = verification[field].isoformat()

        return jsonify({
            "verifications": verifications,
            "total": len(verifications)
        }), 200

    finally:
        cursor.close()
        connection.close()


# ==========================================
# ADMINISTRATOR - VERIFICATION DECISIONS
# ==========================================

@verification_bp.route(
    "/api/admin/verifications/<int:verification_id>/decision",
    methods=["PATCH"]
)
@roles_required("admin")
def admin_decide_verification(verification_id):
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "JSON body required"}), 400

    status = data.get("status")
    notes = data.get("admin_notes")

    if status not in ("approved", "rejected"):
        return jsonify({
            "error": "Status must be approved or rejected"
        }), 400

    if notes is not None and (not isinstance(notes, str) or len(notes) > 2000):
        return jsonify({"error": "Invalid admin notes"}), 400

    admin_id = session["user_id"]

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    reference = None

    try:
        connection.start_transaction()

        cursor.execute("""
            SELECT verification_id, user_id, status, evidence_reference
            FROM user_verifications
            WHERE verification_id = %s
            FOR UPDATE
        """, (verification_id,))

        verification = cursor.fetchone()

        if verification is None:
            connection.rollback()
            return jsonify({
                "error": "Verification request not found"
            }), 404

        if verification["status"] != "pending":
            connection.rollback()
            return jsonify({
                "error": "Only pending requests can be reviewed"
            }), 409

        reference = verification["evidence_reference"]

        # The document is no longer needed after the decision.
        cursor.execute("""
            UPDATE user_verifications
            SET status = %s,
                reviewed_by = %s,
                reviewed_at = NOW(),
                admin_notes = %s,
                evidence_reference = NULL
            WHERE verification_id = %s
        """, (status, admin_id, notes.strip() if notes else None, verification_id))

        notify(
            cursor,
            verification["user_id"],
            "Profile verified" if status == "approved" else "Verification not approved",
            "Your ID document was checked. Your profile now shows the verified badge."
            if status == "approved"
            else "We could not verify your ID document. You can send a clearer copy."
        )

        audit(cursor, admin_id, "verification_" + status,
              "user_verification", verification_id)

        connection.commit()

        delete_document(reference)

        return jsonify({
            "message": "Verification decision saved",
            "verification_id": verification_id,
            "status": status
        }), 200

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()


# ==========================================
# ADMINISTRATOR - LIST VERIFICATIONS AND VIEW A DOCUMENT
# ==========================================

@verification_bp.route("/api/admin/verifications", methods=["GET"])
@roles_required("admin")
def admin_list_verifications():
    status = request.args.get("status")

    if status is not None and status not in (
        "pending", "approved", "rejected"
    ):
        return jsonify({"error": "Invalid verification status"}), 400

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        query = """
            SELECT
                v.verification_id,
                v.user_id,
                u.first_name,
                u.last_name,
                u.email,
                u.account_type,
                u.created_at AS member_since,
                v.verification_method,
                v.evidence_reference IS NOT NULL AS has_document,
                v.status,
                v.submitted_at,
                v.reviewed_by,
                v.reviewed_at,
                v.admin_notes
            FROM user_verifications AS v
            JOIN users AS u ON u.user_id = v.user_id
        """

        params = ()

        if status is not None:
            query += " WHERE v.status = %s"
            params = (status,)

        query += " ORDER BY v.submitted_at DESC, v.verification_id DESC"

        cursor.execute(query, params)
        verifications = cursor.fetchall()

        for verification in verifications:
            verification["has_document"] = bool(verification["has_document"])
            for field in ("submitted_at", "reviewed_at", "member_since"):
                if verification[field] is not None:
                    verification[field] = verification[field].isoformat()

        return jsonify({
            "verifications": verifications,
            "total": len(verifications)
        }), 200

    finally:
        cursor.close()
        connection.close()


@verification_bp.route(
    "/api/admin/verifications/<int:verification_id>/document",
    methods=["GET"]
)
@roles_required("admin")
def admin_view_document(verification_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT evidence_reference
            FROM user_verifications
            WHERE verification_id = %s
        """, (verification_id,))
        row = cursor.fetchone()
    finally:
        cursor.close()
        connection.close()

    reference = row["evidence_reference"] if row else None
    path = (UPLOAD_DIR / reference).resolve() if reference else None

    if path is None or path.parent != UPLOAD_DIR.resolve() or not path.is_file():
        return jsonify({"error": "Document not available"}), 404

    response = send_file(
        path,
        mimetype=CONTENT_TYPES.get(path.suffix, "application/octet-stream"),
        max_age=0
    )
    response.headers["Cache-Control"] = "no-store"
    return response
