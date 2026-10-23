
import os
import mysql.connector

# QuickVolunteer fictional demonstration data
# Never run against the automated test database.
# Safe to run more than once: existing rows are skipped.

DATABASE_NAME = os.getenv("MYSQL_DATABASE", "quickvolunteer_db")

# All demo dates are worked out from this moment, as if "today" were in 2027,
# so the demo tasks stay open (their deadlines are in 2027) during the demo.
# Change it with the DEMO_NOW setting, for example DEMO_NOW="2027-05-01 10:00:00".
DEMO_NOW = os.getenv("DEMO_NOW", "2027-03-15 10:00:00")


# ==========================================
# REFERENCE DATA: one agreed list used by the database and the website
# ==========================================

# Task categories (type of help a task needs).
CATEGORIES = [
    "Shopping and errands",
    "Home and cleaning",
    "Garden and pets",
    "Small repairs",
    "Tech help",
    "Learning and languages",
    "Forms and letters",
    "Company and calls",
]

# Skills (what a member can offer), grouped by skills.category.
SKILLS = [
    ("Shopping", "Everyday help"),
    ("Cooking", "Everyday help"),
    ("Cleaning", "Everyday help"),
    ("Gardening", "Home and garden"),
    ("Pet care", "Home and garden"),
    ("DIY and small repairs", "Home and garden"),
    ("IT support", "Digital"),
    ("Phones and apps", "Digital"),
    ("Tutoring", "Learning and language"),
    ("Translation", "Learning and language"),
    ("Writing and forms", "Admin and company"),
    ("Friendly calls", "Admin and company"),
]


# ==========================================
# FICTIONAL MEMBERS (reserved example.com addresses)
# ==========================================
# first, last, email, account type, postcode, neighbourhood,
# about me, availability, preferred mode, max distance (miles), skills

DEMO_USERS = [
    ("Emma", "Wilson", "emma.wilson.demo@example.com", "help_seeker",
     "E15 1AA", "Stratford",
     "Retired teacher who loves the local library.",
     None, "in_person", 3, ["Friendly calls"]),

    ("James", "Carter", "james.carter.demo@example.com", "volunteer",
     "NW1 1AA", "Camden",
     "I like practical jobs and getting to know my neighbours.",
     "Weekends, mornings", "in_person", 5, ["Shopping", "Gardening"]),

    ("Sofia", "Martinez", "sofia.martinez.demo@example.com", "both",
     "HA9 0AA", "Wembley",
     "I work in IT and enjoy helping people feel confident online.",
     "Evenings", "any", 5, ["IT support", "Phones and apps", "Translation"]),

    ("Oliver", "Brown", "oliver.brown.demo@example.com", "volunteer",
     "N1 1AA", "Islington",
     "Happy to help with shopping and small jobs around the home.",
     "Weekdays, afternoons", "in_person", 3, ["Shopping", "DIY and small repairs"]),

    ("Amelia", "Taylor", "amelia.taylor.demo@example.com", "help_seeker",
     "SE10 8AA", "Greenwich",
     "Learning to use my new laptop.",
     None, "any", 3, ["Cooking"]),

    ("Noah", "Williams", "noah.williams.demo@example.com", "volunteer",
     "E3 3AA", "Bow",
     "Software developer. I can set up laptops, printers and phones.",
     "Weekends", "remote", 5, ["IT support", "Phones and apps"]),

    ("Isabella", "Clark", "isabella.clark.demo@example.com", "both",
     "SW11 1AA", "Battersea",
     "Student teacher, happy to help with study and forms.",
     "Afternoons", "any", 3, ["Tutoring", "Writing and forms"]),

    ("Lucas", "Evans", "lucas.evans.demo@example.com", "help_seeker",
     "E20 1AA", "Stratford",
     "Busy parent who sometimes needs a hand.",
     None, "in_person", 1, ["Cooking"]),

    ("Mia", "Roberts", "mia.roberts.demo@example.com", "volunteer",
     "E8 1AA", "Hackney",
     "I tutor maths and English and enjoy a friendly chat.",
     "Evenings", "remote", 5, ["Tutoring", "Friendly calls"]),

    ("Ethan", "Walker", "ethan.walker.demo@example.com", "both",
     "NW10 1AA", "Willesden",
     "Keen cook and gardener.",
     "Weekends", "any", 5, ["Cooking", "Gardening", "Pet care"]),

    ("Grace", "Harris", "grace.harris.demo@example.com", "help_seeker",
     "E17 1AA", "Walthamstow",
     "I enjoy company and a good cup of tea.",
     None, "in_person", 1, ["Friendly calls"]),

    ("Daniel", "Lewis", "daniel.lewis.demo@example.com", "volunteer",
     "SE1 1AA", "Southwark",
     "Retired engineer with time to help in the community.",
     "Flexible", "any", 5, ["DIY and small repairs", "Writing and forms", "Cleaning"]),
]

# Members whose ID document was checked by an administrator.
# The document file is deleted after the decision, so no reference is kept.
VERIFIED_MEMBERS = [
    "james.carter.demo@example.com",
    "sofia.martinez.demo@example.com",
    "noah.williams.demo@example.com",
    "emma.wilson.demo@example.com",
    "mia.roberts.demo@example.com",
]


# ==========================================
# FICTIONAL TASKS
# ==========================================
# creator email, category, title, description,
# neighbourhood, postcode, delivery mode, minutes,
# deadline in days from today (negative = past), status, skills needed

DEMO_TASKS = [
    ("emma.wilson.demo@example.com", "Shopping and errands",
     "Help with weekly grocery shopping",
     "Looking for someone to help collect groceries from a local supermarket.",
     "Stratford", "E15 1AA", "in_person", 45, 4, "open", ["Shopping"]),

    ("amelia.taylor.demo@example.com", "Tech help",
     "Help setting up a new laptop",
     "Need assistance installing basic software and organising files.",
     "Greenwich", "SE10 8AA", "in_person", 45, 6, "open", ["IT support"]),

    ("lucas.evans.demo@example.com", "Home and cleaning",
     "Help tidying a small kitchen",
     "Looking for a volunteer to help sort and tidy kitchen cupboards.",
     "Stratford", "E20 1AA", "in_person", 60, 5, "open", ["Cleaning"]),

    ("grace.harris.demo@example.com", "Shopping and errands",
     "Collect a few groceries",
     "Need help collecting essential groceries from a nearby shop.",
     "Walthamstow", "E17 1AA", "in_person", 30, 3, "open", ["Shopping"]),

    ("sofia.martinez.demo@example.com", "Tech help",
     "Help with email settings",
     "Need assistance organising email folders and account settings.",
     None, None, "remote", 30, 7, "open", ["IT support"]),

    ("isabella.clark.demo@example.com", "Learning and languages",
     "Help preparing study notes",
     "Looking for help organising revision notes for an upcoming course.",
     None, None, "remote", 45, 8, "open", ["Tutoring"]),

    ("ethan.walker.demo@example.com", "Tech help",
     "Help installing useful mobile apps",
     "Need help choosing and installing everyday mobile applications.",
     None, None, "remote", 30, 5, "open", ["Phones and apps"]),

    ("emma.wilson.demo@example.com", "Company and calls",
     "A friendly weekly phone call",
     "I would enjoy a 30 minute chat on the phone this week.",
     None, None, "remote", 30, 6, "open", ["Friendly calls"]),

    ("amelia.taylor.demo@example.com", "Forms and letters",
     "Help filling in a council form",
     "Looking for someone to explain and help fill in a parking permit form.",
     None, None, "remote", 45, 9, "open", ["Writing and forms"]),

    ("lucas.evans.demo@example.com", "Garden and pets",
     "Walk my dog for half an hour",
     "Friendly dog, needs a short walk while I am at an appointment.",
     "Stratford", "E15 1AA", "in_person", 30, 2, "open", ["Pet care"]),

    ("grace.harris.demo@example.com", "Tech help",
     "Help connecting a printer",
     "Looking for someone to help connect a printer to a laptop.",
     "Walthamstow", "E17 1AA", "in_person", 30, 4, "filled", ["IT support"]),

    ("sofia.martinez.demo@example.com", "Small repairs",
     "Fix a wobbly shelf",
     "A kitchen shelf needs two screws tightened.",
     "Wembley", "HA9 0AA", "in_person", 30, 6, "filled", ["DIY and small repairs"]),

    ("isabella.clark.demo@example.com", "Learning and languages",
     "Help with online learning tools",
     "Looking for guidance using an online learning platform.",
     None, None, "remote", 45, -3, "completed", ["Tutoring"]),

    ("ethan.walker.demo@example.com", "Shopping and errands",
     "Help with supermarket collection",
     "Need help collecting a small grocery order.",
     "Willesden", "NW10 1AA", "in_person", 30, -5, "completed", ["Shopping"]),

    ("emma.wilson.demo@example.com", "Tech help",
     "Help organising smartphone contacts",
     "Need assistance organising contacts and phone settings.",
     None, None, "remote", 30, -2, "completed", ["Phones and apps"]),
]


# ==========================================
# FICTIONAL OFFERS TO HELP
# ==========================================
# task title, volunteer email, status

DEMO_APPLICATIONS = [
    ("Help with weekly grocery shopping", "james.carter.demo@example.com", "pending"),
    ("Help with weekly grocery shopping", "oliver.brown.demo@example.com", "pending"),
    ("Help setting up a new laptop", "noah.williams.demo@example.com", "pending"),
    ("Help setting up a new laptop", "sofia.martinez.demo@example.com", "pending"),
    ("Help tidying a small kitchen", "daniel.lewis.demo@example.com", "pending"),
    ("Collect a few groceries", "james.carter.demo@example.com", "pending"),
    ("Help with email settings", "noah.williams.demo@example.com", "pending"),
    ("Help preparing study notes", "mia.roberts.demo@example.com", "pending"),
    ("Help installing useful mobile apps", "noah.williams.demo@example.com", "pending"),
    ("A friendly weekly phone call", "mia.roberts.demo@example.com", "pending"),
    ("Help filling in a council form", "daniel.lewis.demo@example.com", "pending"),

    ("Help connecting a printer", "noah.williams.demo@example.com", "accepted"),
    ("Help connecting a printer", "oliver.brown.demo@example.com", "rejected"),
    ("Fix a wobbly shelf", "daniel.lewis.demo@example.com", "accepted"),

    ("Help with online learning tools", "mia.roberts.demo@example.com", "completed"),
    ("Help with online learning tools", "james.carter.demo@example.com", "rejected"),
    ("Help with supermarket collection", "james.carter.demo@example.com", "completed"),
    ("Help organising smartphone contacts", "noah.williams.demo@example.com", "completed"),
    ("Help organising smartphone contacts", "daniel.lewis.demo@example.com", "rejected"),
]

# Reviews on completed tasks: task title, reviewer email, rating, comment
DEMO_REVIEWS = [
    ("Help with online learning tools", "isabella.clark.demo@example.com", 5,
     "Clear and patient, thank you."),
    ("Help with online learning tools", "mia.roberts.demo@example.com", 5,
     "Lovely to help, very well prepared."),
    ("Help with supermarket collection", "ethan.walker.demo@example.com", 4,
     "On time and friendly."),
    ("Help organising smartphone contacts", "emma.wilson.demo@example.com", 5,
     "My phone finally makes sense!"),
]


def get_connection():
    if os.getenv("QUICKVOLUNTEER_TESTING") == "1":
        raise RuntimeError("Demo data cannot run in test mode.")

    if not os.getenv("MYSQL_PASSWORD"):
        raise RuntimeError("MYSQL_PASSWORD is not configured.")

    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER", "quickvolunteer_app"),
        password=os.environ["MYSQL_PASSWORD"],
        database=DATABASE_NAME,
    )


def lookup(cursor, sql, params, message):
    cursor.execute(sql, params)
    row = cursor.fetchone()
    if row is None:
        raise RuntimeError(message)
    return row[0]


def seed_reference_data(connection):
    cursor = connection.cursor()
    cursor.executemany(
        "INSERT IGNORE INTO task_categories (category_name) VALUES (%s)",
        [(name,) for name in CATEGORIES],
    )
    for name, group in SKILLS:
        cursor.execute(
            """
            INSERT INTO skills (skill_name, category) VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE category = VALUES(category)
            """,
            (name, group),
        )
    cursor.close()
    print(f"Categories: {len(CATEGORIES)} · Skills: {len(SKILLS)}")


def seed_users(connection):
    from werkzeug.security import generate_password_hash
    import secrets

    cursor = connection.cursor()
    inserted = 0

    for (first, last, email, account_type, postcode, neighbourhood,
         about_me, availability, mode, distance, skills) in DEMO_USERS:

        cursor.execute("SELECT user_id FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            print(f"Already exists: {email}")
            continue

        # Each demo account gets a random password; only its hash is stored.
        # Use demo_logins.py to set a known password for presentations.
        cursor.execute(
            """
            INSERT INTO users (
                first_name, last_name, email, password_hash,
                postcode, neighbourhood, preferred_language,
                account_type, about_me, availability_notes,
                preferred_mode, max_distance_miles, account_status, created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, 'en', %s, %s, %s, %s, %s, 'active',
                    @demo_now - INTERVAL %s DAY)
            """,
            (first, last, email,
             generate_password_hash(secrets.token_urlsafe(32)),
             postcode, neighbourhood, account_type, about_me,
             availability, mode, distance, 10 + 5 * inserted),
        )
        user_id = cursor.lastrowid

        for skill in skills:
            skill_id = lookup(cursor, "SELECT skill_id FROM skills WHERE skill_name = %s",
                              (skill,), f"Skill not found: {skill}")
            cursor.execute(
                "INSERT INTO user_skills (user_id, skill_id) VALUES (%s, %s)",
                (user_id, skill_id),
            )
        inserted += 1

    cursor.close()
    print(f"New fictional users added: {inserted}")


def seed_verifications(connection):
    cursor = connection.cursor()
    admin = None
    cursor.execute("SELECT user_id FROM users WHERE account_type = 'admin' LIMIT 1")
    row = cursor.fetchone()
    if row:
        admin = row[0]

    for email in VERIFIED_MEMBERS:
        user_id = lookup(cursor, "SELECT user_id FROM users WHERE email = %s",
                         (email,), f"Demo user not found: {email}")
        cursor.execute(
            "SELECT verification_id FROM user_verifications WHERE user_id = %s",
            (user_id,),
        )
        if cursor.fetchone():
            continue
        cursor.execute(
            """
            INSERT INTO user_verifications
                (user_id, verification_method, evidence_reference, status,
                 reviewed_by, reviewed_at, admin_notes)
            VALUES (%s, 'identity_document', NULL, 'approved', %s, @demo_now,
                    'ID document checked; file deleted after the decision.')
            """,
            (user_id, admin),
        )
    cursor.close()


def seed_tasks(connection):
    cursor = connection.cursor()
    inserted = 0

    for (creator_email, category, title, description, neighbourhood, postcode,
         mode, minutes, deadline_days, status, skills) in DEMO_TASKS:

        creator_id = lookup(cursor, "SELECT user_id FROM users WHERE email = %s",
                            (creator_email,), f"Demo user not found: {creator_email}")
        category_id = lookup(cursor,
                             "SELECT category_id FROM task_categories WHERE category_name = %s",
                             (category,), f"Category not found: {category}")

        cursor.execute(
            "SELECT task_id FROM tasks WHERE creator_id = %s AND title = %s",
            (creator_id, title),
        )
        if cursor.fetchone():
            print(f"Already exists: {title}")
            continue

        cursor.execute(
            """
            INSERT INTO tasks (
                creator_id, category_id, title, description,
                location_text, postcode, delivery_mode,
                estimated_minutes, deadline_at, status, created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s,
                    TIMESTAMP(DATE(@demo_now + INTERVAL %s DAY), '23:59:00'),
                    %s,
                    @demo_now - INTERVAL 7 DAY)
            """,
            (creator_id, category_id, title, description, neighbourhood,
             postcode, mode, minutes, deadline_days, status),
        )
        task_id = cursor.lastrowid

        for index, skill in enumerate(skills):
            skill_id = lookup(cursor, "SELECT skill_id FROM skills WHERE skill_name = %s",
                              (skill,), f"Skill not found: {skill}")
            cursor.execute(
                "INSERT INTO task_skills (task_id, skill_id, importance) VALUES (%s, %s, %s)",
                (task_id, skill_id, "required" if index == 0 else "helpful"),
            )
        inserted += 1

    cursor.close()
    print(f"New fictional tasks added: {inserted}")


def seed_applications(connection):
    cursor = connection.cursor()
    inserted = 0

    for task_title, volunteer_email, status in DEMO_APPLICATIONS:
        cursor.execute(
            """
            SELECT t.task_id, t.creator_id, t.status
            FROM tasks AS t
            JOIN users AS u ON u.user_id = t.creator_id
            WHERE t.title = %s AND u.email LIKE %s
            """,
            (task_title, "%.demo@example.com"),
        )
        task = cursor.fetchone()
        if task is None:
            raise RuntimeError(f"Demo task not found: {task_title}")
        task_id, creator_id, task_status = task

        cursor.execute("SELECT user_id, account_type FROM users WHERE email = %s",
                       (volunteer_email,))
        volunteer = cursor.fetchone()
        if volunteer is None:
            raise RuntimeError(f"Demo volunteer not found: {volunteer_email}")
        volunteer_id, account_type = volunteer

        if account_type not in ("volunteer", "both"):
            raise RuntimeError("Account is not a volunteer.")
        if volunteer_id == creator_id:
            raise RuntimeError("Users cannot apply to their own tasks.")
        if status == "accepted" and task_status != "filled":
            raise RuntimeError("Accepted application requires a filled task.")
        if status == "completed" and task_status != "completed":
            raise RuntimeError("Completed application requires a completed task.")

        cursor.execute(
            "SELECT application_id FROM task_applications WHERE task_id = %s AND volunteer_id = %s",
            (task_id, volunteer_id),
        )
        if cursor.fetchone():
            continue

        cursor.execute(
            """
            INSERT INTO task_applications (
                task_id, volunteer_id, status, applied_at, accepted_at,
                volunteer_completed_at, help_seeker_completed_at
            )
            VALUES (
                %s, %s, %s, @demo_now - INTERVAL 6 DAY,
                CASE WHEN %s IN ('accepted', 'completed') THEN @demo_now - INTERVAL 5 DAY ELSE NULL END,
                CASE WHEN %s = 'completed' THEN @demo_now - INTERVAL 4 DAY ELSE NULL END,
                CASE WHEN %s = 'completed' THEN @demo_now - INTERVAL 4 DAY ELSE NULL END
            )
            """,
            (task_id, volunteer_id, status, status, status, status),
        )
        inserted += 1

    cursor.close()
    print(f"New fictional offers added: {inserted}")


def seed_reviews(connection):
    cursor = connection.cursor()
    for task_title, reviewer_email, rating, comment in DEMO_REVIEWS:
        cursor.execute(
            """
            SELECT a.application_id, a.volunteer_id, t.creator_id
            FROM task_applications AS a
            JOIN tasks AS t ON t.task_id = a.task_id
            WHERE t.title = %s AND a.status = 'completed'
            """,
            (task_title,),
        )
        row = cursor.fetchone()
        if row is None:
            continue
        application_id, volunteer_id, creator_id = row
        reviewer_id = lookup(cursor, "SELECT user_id FROM users WHERE email = %s",
                             (reviewer_email,), f"Demo user not found: {reviewer_email}")
        reviewed = volunteer_id if reviewer_id == creator_id else creator_id
        cursor.execute(
            """
            INSERT IGNORE INTO reviews
                (application_id, reviewer_id, reviewed_user_id, rating, comment, created_at)
            VALUES (%s, %s, %s, %s, %s, @demo_now - INTERVAL 3 DAY)
            """,
            (application_id, reviewer_id, reviewed, rating, comment),
        )
    cursor.close()


def main():
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("SET @demo_now = %s", (DEMO_NOW,))
        cursor.close()
        print(f"Demo dates as if today were {DEMO_NOW}")
        seed_reference_data(connection)
        seed_users(connection)
        seed_verifications(connection)
        seed_tasks(connection)
        seed_applications(connection)
        seed_reviews(connection)
        connection.commit()

        cursor = connection.cursor()
        for table in ("users", "tasks", "task_applications", "reviews"):
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            print(f"Total {table}: {cursor.fetchone()[0]}")
        cursor.close()
        print("QuickVolunteer demo data setup completed!")

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


if __name__ == "__main__":
    main()
