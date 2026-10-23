import mysql.connector
from flask import Blueprint, jsonify, request, session

from auth import login_required
from db import get_db_connection


skills_bp = Blueprint("skills", __name__)


# ==========================================
# GET ALL AVAILABLE SKILLS
# ==========================================

@skills_bp.route("/api/skills", methods=["GET"])
def get_skills():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT skill_id, skill_name, category
            FROM skills
            ORDER BY category ASC, skill_name ASC
        """)

        skills = cursor.fetchall()

        return jsonify({
            "skills": skills,
            "total": len(skills)
        }), 200

    finally:
        cursor.close()
        connection.close()


# ==========================================
# GET CURRENT USER'S SKILLS
# ==========================================

@skills_bp.route("/api/users/me/skills", methods=["GET"])
@login_required
def get_my_skills():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT s.skill_id, s.skill_name, s.category,
                   us.skill_level, us.selected_at
            FROM user_skills AS us
            JOIN skills AS s
                ON us.skill_id = s.skill_id
            WHERE us.user_id = %s
            ORDER BY s.skill_name ASC
        """, (session["user_id"],))

        skills = cursor.fetchall()

        for skill in skills:
            skill["selected_at"] = skill["selected_at"].isoformat()

        return jsonify({
            "user_id": session["user_id"],
            "skills": skills,
            "total": len(skills)
        }), 200

    finally:
        cursor.close()
        connection.close()


# ==========================================
# UPDATE CURRENT USER'S SKILLS
# ==========================================

@skills_bp.route("/api/users/me/skills", methods=["PUT"])
@login_required
def update_my_skills():
    """Replace the member's skills.

    Body: {"skill_ids": [1, 2]} or
          {"skills": [{"skill_id": 1, "skill_level": "beginner"}, ...]}
    Members need at least one skill to finish onboarding and get matches.
    """
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "JSON body required"}), 400

    entries, error = read_skill_entries(data, "skill_level",
                                        ("beginner", "intermediate", "advanced"),
                                        None)
    if error:
        return jsonify({"error": error}), 400

    if not entries:
        return jsonify({
            "error": "Choose at least one skill"
        }), 400

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        error = check_skills_exist(cursor, [e[0] for e in entries])
        if error:
            return jsonify({"error": error}), 400

        user_id = session["user_id"]
        placeholders = ", ".join(["%s"] * len(entries))

        # Keep the original selected_at for skills the member already had.
        cursor.execute(
            f"DELETE FROM user_skills WHERE user_id = %s "
            f"AND skill_id NOT IN ({placeholders})",
            (user_id, *[e[0] for e in entries])
        )
        cursor.executemany("""
            INSERT INTO user_skills (user_id, skill_id, skill_level)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE skill_level = VALUES(skill_level)
        """, [(user_id, skill_id, level) for skill_id, level in entries])

        connection.commit()

        return jsonify({
            "message": "Skills updated successfully",
            "skill_ids": [e[0] for e in entries]
        }), 200

    except mysql.connector.Error:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()


def read_skill_entries(data, extra_field, allowed, default):
    """Read skill_ids or skills[] from a request body.

    Returns ([(skill_id, extra_value), ...], error)."""
    if "skills" in data:
        items = data.get("skills")
        if not isinstance(items, list):
            return None, "skills must be a list"
        entries = []
        for item in items:
            if not isinstance(item, dict):
                return None, "Invalid skill entry"
            value = item.get(extra_field, default)
            if value is not None and value not in allowed:
                return None, f"Invalid {extra_field}"
            entries.append((item.get("skill_id"), value))
    else:
        skill_ids = data.get("skill_ids")
        if not isinstance(skill_ids, list):
            return None, "skill_ids must be a list"
        required = data.get("required_skill_ids", [])
        if not isinstance(required, list):
            return None, "required_skill_ids must be a list"
        entries = [
            (skill_id,
             "required" if (extra_field == "importance" and skill_id in required)
             else default)
            for skill_id in skill_ids
        ]

    ids = [e[0] for e in entries]
    if (
        len(ids) > 50
        or any(type(i) is not int or i <= 0 for i in ids)
        or len(ids) != len(set(ids))
    ):
        return None, "Invalid or duplicate skill IDs"

    return entries, None


def check_skills_exist(cursor, skill_ids):
    if not skill_ids:
        return None
    placeholders = ", ".join(["%s"] * len(skill_ids))
    cursor.execute(
        f"SELECT skill_id FROM skills WHERE skill_id IN ({placeholders})",
        tuple(skill_ids)
    )
    if len(cursor.fetchall()) != len(skill_ids):
        return "Unknown skill ID"
    return None


# ==========================================
# GET SKILLS REQUIRED FOR A TASK
# ==========================================

@skills_bp.route("/api/tasks/<int:task_id>/skills", methods=["GET"])
def get_task_skills(task_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT task_id FROM tasks WHERE task_id = %s",
            (task_id,)
        )

        if cursor.fetchone() is None:
            return jsonify({"error": "Task not found"}), 404

        cursor.execute("""
            SELECT s.skill_id, s.skill_name, s.category, ts.importance
            FROM task_skills AS ts
            JOIN skills AS s
                ON ts.skill_id = s.skill_id
            WHERE ts.task_id = %s
            ORDER BY ts.importance = 'helpful', s.skill_name ASC
        """, (task_id,))

        skills = cursor.fetchall()

        return jsonify({
            "task_id": task_id,
            "skills": skills,
            "total": len(skills)
        }), 200

    finally:
        cursor.close()
        connection.close()


# ==========================================
# UPDATE TASK SKILLS - CREATOR ONLY
# ==========================================

@skills_bp.route("/api/tasks/<int:task_id>/skills", methods=["PUT"])
@login_required
def update_task_skills(task_id):
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "JSON body required"}), 400

    # Body: {"skill_ids": [...], "required_skill_ids": [...]} or
    #       {"skills": [{"skill_id": 1, "importance": "required"}, ...]}
    entries, error = read_skill_entries(data, "importance",
                                        ("required", "helpful"), "helpful")
    if error:
        return jsonify({"error": error}), 400

    skill_ids = [e[0] for e in entries]

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT creator_id FROM tasks WHERE task_id = %s",
            (task_id,)
        )
        task = cursor.fetchone()

        if task is None:
            return jsonify({"error": "Task not found"}), 404

        if task["creator_id"] != session["user_id"]:
            return jsonify({"error": "Permission denied"}), 403

        error = check_skills_exist(cursor, skill_ids)
        if error:
            return jsonify({"error": error}), 400

        cursor.execute(
            "DELETE FROM task_skills WHERE task_id = %s",
            (task_id,)
        )

        if skill_ids:
            cursor.executemany("""
                INSERT INTO task_skills (task_id, skill_id, importance)
                VALUES (%s, %s, %s)
            """, [(task_id, skill_id, importance)
                  for skill_id, importance in entries])

        connection.commit()

        return jsonify({
            "message": "Task skills updated successfully",
            "task_id": task_id,
            "skill_ids": skill_ids
        }), 200

    except mysql.connector.Error:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()
