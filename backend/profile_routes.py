"""Member profiles.

- Each member can read and edit their own details.
- Every change sends a notification to the administrators, who check that
  the new details follow the safety rules.
- Members can see a short summary of each other before accepting an offer
  or offering to help: name and initial, member since, verification,
  about me, skills and number of completed tasks.
"""

import mysql.connector
from flask import Blueprint, jsonify, request, session

from auth import login_required
from db import get_db_connection
from helpers import (
    VERIFIED_SQL, audit, clean_postcode, member_summary, notify_admins,
    short_name
)


profile_bp = Blueprint("profiles", __name__)

PROFILE_FIELDS = (
    "first_name", "last_name", "postcode", "neighbourhood", "about_me",
    "availability_notes", "preferred_mode", "max_distance_miles",
    "account_type", "phone", "preferred_language",
)

FIELD_LABELS = {
    "first_name": "first name",
    "last_name": "last name",
    "postcode": "postcode",
    "neighbourhood": "neighbourhood",
    "about_me": "about me",
    "availability_notes": "availability",
    "preferred_mode": "preferred help mode",
    "max_distance_miles": "distance",
    "account_type": "ask or give help",
    "phone": "phone",
    "preferred_language": "language",
}


def serialise_profile(row):
    profile = dict(row)
    for field in ("created_at", "updated_at"):
        if profile.get(field) is not None:
            profile[field] = profile[field].isoformat()
    profile["verified"] = bool(profile.get("verified"))
    return profile


@profile_bp.route("/api/users/me/profile", methods=["GET"])
@login_required
def my_profile():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(f"""
            SELECT
                u.user_id, u.first_name, u.last_name, u.email, u.phone,
                u.postcode, u.neighbourhood, u.preferred_language,
                u.account_type, u.about_me, u.availability_notes,
                u.preferred_mode, u.max_distance_miles,
                u.created_at, u.updated_at,
                {VERIFIED_SQL.format(alias='u')} AS verified
            FROM users AS u
            WHERE u.user_id = %s
        """, (session["user_id"],))

        profile = serialise_profile(cursor.fetchone())

        cursor.execute("""
            SELECT s.skill_id, s.skill_name, s.category, us.skill_level
            FROM user_skills AS us
            JOIN skills AS s ON s.skill_id = us.skill_id
            WHERE us.user_id = %s
            ORDER BY s.skill_name
        """, (session["user_id"],))
        profile["skills"] = cursor.fetchall()

        return jsonify({"profile": profile}), 200

    finally:
        cursor.close()
        connection.close()


def validate_changes(data):
    """Return (changes, error)."""
    changes = {}

    for field in PROFILE_FIELDS:
        if field not in data:
            continue
        value = data[field]

        if field in ("first_name", "last_name"):
            if not isinstance(value, str) or not value.strip():
                return None, "Name cannot be empty"
            if len(value.strip()) > 50:
                return None, "Name is too long"
            value = value.strip()

        elif field == "postcode":
            if value in (None, ""):
                value = None
            else:
                value = clean_postcode(value)
                if value is None:
                    return None, "Please enter a valid UK postcode"

        elif field in ("neighbourhood", "phone", "preferred_language"):
            limits = {"neighbourhood": 80, "phone": 30, "preferred_language": 10}
            if value in (None, ""):
                value = None
            elif not isinstance(value, str) or len(value.strip()) > limits[field]:
                return None, f"Invalid {FIELD_LABELS[field]}"
            else:
                value = value.strip()

        elif field == "about_me":
            if value in (None, ""):
                value = None
            elif not isinstance(value, str) or len(value) > 1000:
                return None, "About me must be 1000 characters or fewer"
            else:
                value = value.strip()

        elif field == "availability_notes":
            if value in (None, ""):
                value = None
            elif not isinstance(value, str) or len(value) > 255:
                return None, "Availability is too long"

        elif field == "preferred_mode":
            if value not in ("in_person", "remote", "any"):
                return None, "Preferred help mode must be in_person, remote or any"

        elif field == "max_distance_miles":
            if value is not None and (type(value) is not int or not 1 <= value <= 50):
                return None, "Distance must be between 1 and 50 miles"

        elif field == "account_type":
            # Members choose ask, give or both; admin is never self-assigned.
            if value not in ("help_seeker", "volunteer", "both"):
                return None, "Invalid account type"

        changes[field] = value

    return changes, None


@profile_bp.route("/api/users/me", methods=["PATCH"])
@login_required
def update_my_profile():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "JSON body required"}), 400

    changes, error = validate_changes(data)

    if error:
        return jsonify({"error": error}), 400

    if not changes:
        return jsonify({"error": "No changes to save"}), 400

    user_id = session["user_id"]

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT * FROM users WHERE user_id = %s FOR UPDATE",
            (user_id,)
        )
        current = cursor.fetchone()

        if current["account_type"] == "admin" and "account_type" in changes:
            return jsonify({"error": "Administrators cannot change account type"}), 403

        changed = {
            field: value for field, value in changes.items()
            if current.get(field) != value
        }

        if not changed:
            return jsonify({"message": "Nothing changed"}), 200

        # Column names come from the fixed PROFILE_FIELDS list, never from input.
        assignments = ", ".join(f"{field} = %s" for field in changed)
        cursor.execute(
            f"UPDATE users SET {assignments}, updated_at = NOW() "
            "WHERE user_id = %s",
            (*changed.values(), user_id)
        )

        # Administrators check profile changes against the safety rules.
        if current["account_type"] != "admin":
            name = short_name(
                changed.get("first_name", current["first_name"]),
                changed.get("last_name", current["last_name"])
            )
            labels = ", ".join(FIELD_LABELS[field] for field in changed)
            notify_admins(
                cursor,
                "Profile changes to check",
                f"Member #{user_id} ({name}) changed: {labels}."
            )

        audit(cursor, user_id, "profile_updated", "user", user_id)
        connection.commit()

        return jsonify({
            "message": "Profile updated",
            "changed": sorted(changed)
        }), 200

    except mysql.connector.Error:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()


@profile_bp.route("/api/users/<int:user_id>/summary", methods=["GET"])
@login_required
def user_summary(user_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        summary = member_summary(cursor, user_id)

        if summary is None:
            return jsonify({"error": "Member not found"}), 404

        return jsonify({"member": summary}), 200

    finally:
        cursor.close()
        connection.close()
