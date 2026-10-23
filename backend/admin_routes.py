
import mysql.connector
from flask import Blueprint, jsonify, request, session

from auth import roles_required
from db import get_db_connection
from helpers import (
    COMPLETED_AS_REQUESTER_SQL, COMPLETED_AS_VOLUNTEER_SQL, VERIFIED_SQL,
    audit, notify, notify_admins
)


admin_bp = Blueprint("administration", __name__)


# ==========================================
# SUBMIT A REPORT
# ==========================================

@admin_bp.route("/api/reports", methods=["POST"])
@roles_required("volunteer", "help_seeker", "both")
def submit_report():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "JSON body required"}), 400

    reported_user_id = data.get("reported_user_id")
    task_id = data.get("task_id")
    other_details = data.get("other_details")
    reason = data.get("reason")
    contact_allowed = data.get("contact_allowed", True)

    # A report is about a member, a task, or something else (explained).
    target_type = data.get("target_type")

    if target_type is None:
        target_type = "user" if reported_user_id is not None else "task"

    if target_type not in ("user", "task", "other"):
        return jsonify({"error": "Target must be user, task or other"}), 400

    if target_type == "user":
        if task_id is not None or type(reported_user_id) is not int or reported_user_id <= 0:
            return jsonify({"error": "Report exactly one user or one task"}), 400
        other_details = None

    elif target_type == "task":
        if reported_user_id is not None or type(task_id) is not int or task_id <= 0:
            return jsonify({"error": "Report exactly one user or one task"}), 400
        other_details = None

    else:
        if reported_user_id is not None or task_id is not None:
            return jsonify({"error": "Something else reports have no member or task"}), 400
        if not isinstance(other_details, str) or not other_details.strip():
            return jsonify({"error": "Please say what the report is about"}), 400
        if len(other_details.strip()) > 2000:
            return jsonify({"error": "Details are too long"}), 400
        other_details = other_details.strip()

    if not isinstance(reason, str) or not reason.strip():
        return jsonify({"error": "Reason is required"}), 400

    if len(reason.strip()) > 5000:
        return jsonify({"error": "Reason is too long"}), 400

    if type(contact_allowed) is not bool:
        return jsonify({"error": "contact_allowed must be true or false"}), 400

    if reported_user_id == session["user_id"]:
        return jsonify({
            "error": "You cannot report yourself"
        }), 400

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            INSERT INTO reports (
                reporter_id,
                target_type,
                reported_user_id,
                task_id,
                other_details,
                reason,
                contact_allowed
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            session["user_id"],
            target_type,
            reported_user_id,
            task_id,
            other_details,
            reason.strip(),
            contact_allowed
        ))

        report_id = cursor.lastrowid

        notify_admins(
            cursor,
            "New concern reported",
            f"Report QV-{report_id} is waiting for review."
        )

        connection.commit()

        return jsonify({
            "message": "Report submitted successfully",
            "report_id": report_id
        }), 201

    except mysql.connector.IntegrityError:
        connection.rollback()
        return jsonify({
            "error": "Reported user or task does not exist"
        }), 404

    finally:
        cursor.close()
        connection.close()



# ==========================================
# ADMINISTRATOR - VIEW REPORTS
# ==========================================

@admin_bp.route("/api/admin/reports", methods=["GET"])
@roles_required("admin")
def admin_get_reports():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                r.report_id,
                r.target_type,
                r.reporter_id,
                CONCAT(rp.first_name, ' ', LEFT(rp.last_name, 1), '.') AS reporter_name,
                CASE WHEN r.contact_allowed THEN rp.email ELSE NULL END AS reporter_email,
                r.contact_allowed,
                r.reported_user_id,
                CONCAT(ru.first_name, ' ', ru.last_name) AS reported_user_name,
                ru.account_status AS reported_user_status,
                r.task_id,
                t.title AS task_title,
                r.other_details,
                r.reviewed_by,
                r.reason,
                r.status,
                r.created_at,
                r.reviewed_at
            FROM reports AS r
            JOIN users AS rp ON rp.user_id = r.reporter_id
            LEFT JOIN users AS ru ON ru.user_id = r.reported_user_id
            LEFT JOIN tasks AS t ON t.task_id = r.task_id
            ORDER BY r.created_at DESC, r.report_id DESC
        """)

        reports = cursor.fetchall()

        for report in reports:
            report["contact_allowed"] = bool(report["contact_allowed"])
            for field in ("created_at", "reviewed_at"):
                if report[field] is not None:
                    report[field] = report[field].isoformat()

        return jsonify({
            "reports": reports,
            "total": len(reports)
        }), 200

    finally:
        cursor.close()
        connection.close()



    
@admin_bp.route("/api/admin/reports/<int:report_id>/status", methods=["PATCH"])
@roles_required("admin")
def admin_update_report_status(report_id):
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "JSON body required"}), 400

    status = data.get("status")

    if status not in ("open", "reviewing", "closed"):
        return jsonify({"error": "Invalid report status"}), 400

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            UPDATE reports
            SET status = %s,
                reviewed_by = %s,
                reviewed_at = CASE
                    WHEN %s = 'open' THEN NULL
                    ELSE NOW()
                END
            WHERE report_id = %s
        """, (status, session["user_id"], status, report_id))

        
    

        if cursor.rowcount == 0:
            cursor.execute(
                "SELECT report_id FROM reports WHERE report_id = %s",
                (report_id,)
            )

            if cursor.fetchone() is None:
                connection.rollback()
                return jsonify({"error": "Report not found"}), 404

        connection.commit()

        return jsonify({
            "message": "Report status updated successfully",
            "report_id": report_id,
            "status": status
        }), 200

    finally:
        cursor.close()
        connection.close()


# ==========================================
# ADMINISTRATOR - REVIEW MODERATION
# ==========================================


@admin_bp.route("/api/admin/reviews/<int:review_id>/moderation", methods=["PATCH"])
@roles_required("admin")
def admin_moderate_review(review_id):
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "JSON body required"}), 400

    status = data.get("status")
    reason = data.get("reason")

    if status not in ("visible", "hidden"):
        return jsonify({"error": "Invalid moderation status"}), 400

    if not isinstance(reason, str) or not reason.strip():
        return jsonify({"error": "Moderation reason is required"}), 400

    reason = reason.strip()

    if len(reason) > 5000:
        return jsonify({"error": "Moderation reason is too long"}), 400

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT review_id
            FROM reviews
            WHERE review_id = %s
        """, (review_id,))

        if cursor.fetchone() is None:
            return jsonify({"error": "Review not found"}), 404

        cursor.execute("""
            UPDATE reviews
            SET moderation_status = %s,
                moderated_by = %s,
                moderated_at = NOW(),
                moderation_reason = %s
            WHERE review_id = %s
        """, (
            status,
            session["user_id"],
            reason,
            review_id
        ))

        connection.commit()

        return jsonify({
            "message": "Review moderation updated successfully",
            "review_id": review_id,
            "moderation_status": status
        }), 200

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()




# ==========================================
# ADMINISTRATOR - MEMBERS AND COMPLETED TASKS
# ==========================================
# Members never see hours or totals on their own dashboard. The number of
# completed tasks is kept here for administrators; it will support
# volunteer levels in a future version.

@admin_bp.route("/api/admin/members", methods=["GET"])
@roles_required("admin")
def admin_list_members():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(f"""
            SELECT
                u.user_id,
                u.first_name,
                u.last_name,
                u.email,
                u.account_type,
                u.account_status,
                u.neighbourhood,
                u.created_at,
                u.updated_at,
                {VERIFIED_SQL.format(alias='u')} AS verified,
                {COMPLETED_AS_VOLUNTEER_SQL.format(alias='u')} AS completed_as_volunteer,
                {COMPLETED_AS_REQUESTER_SQL.format(alias='u')} AS completed_as_requester
            FROM users AS u
            WHERE u.account_type <> 'admin'
            ORDER BY completed_as_volunteer DESC, u.first_name, u.last_name
        """)

        members = cursor.fetchall()

        for member in members:
            member["verified"] = bool(member["verified"])
            member["completed_as_volunteer"] = int(member["completed_as_volunteer"])
            member["completed_as_requester"] = int(member["completed_as_requester"])
            for field in ("created_at", "updated_at"):
                if member[field] is not None:
                    member[field] = member[field].isoformat()

        return jsonify({"members": members, "total": len(members)}), 200

    finally:
        cursor.close()
        connection.close()


@admin_bp.route("/api/admin/users/<int:user_id>/status", methods=["PATCH"])
@roles_required("admin")
def admin_update_account_status(user_id):
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "JSON body required"}), 400

    status = data.get("status")

    if status not in ("active", "suspended"):
        return jsonify({"error": "Status must be active or suspended"}), 400

    if user_id == session["user_id"]:
        return jsonify({"error": "You cannot change your own account"}), 400

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT user_id, account_type FROM users WHERE user_id = %s",
            (user_id,)
        )
        user = cursor.fetchone()

        if user is None:
            return jsonify({"error": "Member not found"}), 404

        if user["account_type"] == "admin":
            return jsonify({"error": "Administrator accounts cannot be suspended here"}), 403

        cursor.execute(
            "UPDATE users SET account_status = %s WHERE user_id = %s",
            (status, user_id)
        )

        if status == "active":
            notify(cursor, user_id, "Account reactivated",
                   "Your QuickVolunteer account is active again.")

        audit(cursor, session["user_id"],
              "account_" + ("suspended" if status == "suspended" else "reactivated"),
              "user", user_id)

        connection.commit()

        return jsonify({
            "message": "Account status updated",
            "user_id": user_id,
            "account_status": status
        }), 200

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()


@admin_bp.route("/api/admin/reviews", methods=["GET"])
@roles_required("admin")
def admin_list_reviews():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                r.review_id,
                r.rating,
                r.comment,
                r.created_at,
                r.moderation_status,
                r.moderated_at,
                r.moderation_reason,
                t.title AS task_title,
                CONCAT(rv.first_name, ' ', LEFT(rv.last_name, 1), '.') AS reviewer_name,
                CONCAT(rd.first_name, ' ', LEFT(rd.last_name, 1), '.') AS reviewed_name
            FROM reviews AS r
            JOIN task_applications AS a ON a.application_id = r.application_id
            JOIN tasks AS t ON t.task_id = a.task_id
            JOIN users AS rv ON rv.user_id = r.reviewer_id
            JOIN users AS rd ON rd.user_id = r.reviewed_user_id
            ORDER BY r.created_at DESC, r.review_id DESC
        """)

        reviews = cursor.fetchall()

        for review in reviews:
            for field in ("created_at", "moderated_at"):
                if review[field] is not None:
                    review[field] = review[field].isoformat()

        return jsonify({"reviews": reviews, "total": len(reviews)}), 200

    finally:
        cursor.close()
        connection.close()
