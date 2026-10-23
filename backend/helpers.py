"""Small shared helpers: notifications, audit logs and member summaries."""

import re

# UK postcode check (format only), e.g. "E8 1AA", "SW1A 1AA".
POSTCODE_PATTERN = re.compile(r"^[A-Z]{1,2}[0-9][A-Z0-9]? ?[0-9][A-Z]{2}$")


def clean_postcode(value):
    """Return the postcode in upper case with one space, or None if invalid."""
    if not isinstance(value, str):
        return None
    compact = value.strip().upper().replace(" ", "")
    if not 5 <= len(compact) <= 7:
        return None
    formatted = compact[:-3] + " " + compact[-3:]
    return formatted if POSTCODE_PATTERN.match(formatted) else None


def short_name(first_name, last_name):
    """First name and last initial only, e.g. "Emma W."."""
    initial = (last_name or "")[:1]
    return f"{first_name} {initial}." if initial else first_name


def notify(cursor, user_id, title, content, application_id=None):
    """Add an in-app notification (email or text are a later feature)."""
    cursor.execute("""
        INSERT INTO notifications
            (user_id, task_application_id, title, content)
        VALUES (%s, %s, %s, %s)
    """, (user_id, application_id, title[:120], content))


def notify_admins(cursor, title, content):
    cursor.execute("""
        INSERT INTO notifications (user_id, title, content)
        SELECT user_id, %s, %s
        FROM users
        WHERE account_type = 'admin' AND account_status = 'active'
    """, (title[:120], content))


def audit(cursor, actor_id, action, entity_type, entity_id):
    cursor.execute("""
        INSERT INTO audit_logs (actor_id, action, entity_type, entity_id)
        VALUES (%s, %s, %s, %s)
    """, (actor_id, action, entity_type, entity_id))


# Shared SQL: is the member's profile verified, and how many tasks completed.
VERIFIED_SQL = """
    EXISTS (
        SELECT 1 FROM user_verifications AS v
        WHERE v.user_id = {alias}.user_id AND v.status = 'approved'
    )
"""

COMPLETED_AS_VOLUNTEER_SQL = """
    (SELECT COUNT(*) FROM task_applications AS ca
     WHERE ca.volunteer_id = {alias}.user_id AND ca.status = 'completed')
"""

COMPLETED_AS_REQUESTER_SQL = """
    (SELECT COUNT(*) FROM tasks AS ct
     WHERE ct.creator_id = {alias}.user_id AND ct.status = 'completed')
"""


def member_summary(cursor, user_id):
    """The few details members can see about each other before accepting
    an offer or offering to help: name and initial, member since,
    verification, about me, skills and number of completed tasks."""
    cursor.execute(f"""
        SELECT
            u.user_id,
            u.first_name,
            u.last_name,
            u.about_me,
            u.created_at,
            {VERIFIED_SQL.format(alias='u')} AS verified,
            {COMPLETED_AS_VOLUNTEER_SQL.format(alias='u')} AS completed_as_volunteer,
            {COMPLETED_AS_REQUESTER_SQL.format(alias='u')} AS completed_as_requester
        FROM users AS u
        WHERE u.user_id = %s
          AND u.account_status = 'active'
          AND u.account_type <> 'admin'
    """, (user_id,))
    row = cursor.fetchone()
    if row is None:
        return None

    cursor.execute("""
        SELECT s.skill_name
        FROM user_skills AS us
        JOIN skills AS s ON s.skill_id = us.skill_id
        WHERE us.user_id = %s
        ORDER BY s.skill_name
    """, (user_id,))
    skills = [r["skill_name"] for r in cursor.fetchall()]

    return {
        "user_id": row["user_id"],
        "display_name": short_name(row["first_name"], row["last_name"]),
        "member_since": row["created_at"].date().isoformat(),
        "verified": bool(row["verified"]),
        "about_me": row["about_me"] or "",
        "skills": skills,
        "completed_tasks": int(row["completed_as_volunteer"])
        + int(row["completed_as_requester"]),
        "completed_as_volunteer": int(row["completed_as_volunteer"]),
        "completed_as_requester": int(row["completed_as_requester"]),
    }
