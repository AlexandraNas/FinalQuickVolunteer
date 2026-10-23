-- QuickVolunteer V1 - MySQL 8
-- Matches Database_Normalisation.xlsx and the ERD (15 entities, 3NF).
-- Accounts are active from sign-up. Verification is optional and uses an ID document.
-- Later features (not in this schema): DBS checks, profile photos, preferred
-- connections, volunteer levels, email or text notifications.

CREATE TABLE users (
    user_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(254) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    phone VARCHAR(30),
    postcode VARCHAR(10),
    neighbourhood VARCHAR(80),
    preferred_language VARCHAR(10),
    account_type ENUM(
        'help_seeker', 'volunteer', 'both', 'admin'
    ) NOT NULL DEFAULT 'both',
    about_me TEXT,
    availability_notes VARCHAR(255),
    preferred_mode ENUM('in_person', 'remote', 'any')
        NOT NULL DEFAULT 'any',
    max_distance_miles TINYINT UNSIGNED,
    account_status ENUM(
        'pending', 'active', 'suspended'
    ) NOT NULL DEFAULT 'active',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME,

    CONSTRAINT chk_users_distance
        CHECK (max_distance_miles IS NULL OR max_distance_miles BETWEEN 1 AND 50)
) ENGINE=InnoDB;

-- Optional profile verification with an ID document.
-- The document file is kept in private storage outside the website;
-- evidence_reference stores only its private file name.
CREATE TABLE user_verifications (
    verification_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT UNSIGNED NOT NULL,
    verification_method ENUM('identity_document')
        NOT NULL DEFAULT 'identity_document',
    evidence_reference VARCHAR(500),
    status ENUM('pending', 'approved', 'rejected')
        NOT NULL DEFAULT 'pending',
    submitted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reviewed_by BIGINT UNSIGNED,
    reviewed_at DATETIME,
    admin_notes TEXT,

    FOREIGN KEY (user_id) REFERENCES users(user_id)
        ON DELETE CASCADE,
    FOREIGN KEY (reviewed_by) REFERENCES users(user_id)
        ON DELETE SET NULL,
    INDEX idx_verifications_status (status)
) ENGINE=InnoDB;

CREATE TABLE task_categories (
    category_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    category_name VARCHAR(80) NOT NULL UNIQUE
) ENGINE=InnoDB;

CREATE TABLE tasks (
    task_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    creator_id BIGINT UNSIGNED NOT NULL,
    category_id BIGINT UNSIGNED NOT NULL,
    title VARCHAR(160) NOT NULL,
    description TEXT NOT NULL,
    location_text VARCHAR(160),
    postcode VARCHAR(10),
    delivery_mode ENUM('in_person', 'remote') NOT NULL,
    estimated_minutes SMALLINT UNSIGNED NOT NULL,
    deadline_at DATETIME NOT NULL,
    status ENUM('open', 'filled', 'completed', 'closed')
        NOT NULL DEFAULT 'open',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_task_duration
        CHECK (estimated_minutes BETWEEN 15 AND 60),

    -- In-person tasks need a postcode and neighbourhood; remote tasks have none.
    CONSTRAINT chk_task_location
        CHECK (
            (delivery_mode = 'in_person'
                AND postcode IS NOT NULL AND location_text IS NOT NULL)
            OR
            (delivery_mode = 'remote' AND postcode IS NULL)
        ),

    FOREIGN KEY (creator_id) REFERENCES users(user_id)
        ON DELETE RESTRICT,
    FOREIGN KEY (category_id) REFERENCES task_categories(category_id)
        ON DELETE RESTRICT,
    INDEX idx_tasks_creator (creator_id),
    INDEX idx_tasks_category_status (category_id, status)
) ENGINE=InnoDB;

-- A withdrawn offer is deleted, so it is never recorded.
CREATE TABLE task_applications (
    application_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    task_id BIGINT UNSIGNED NOT NULL,
    volunteer_id BIGINT UNSIGNED NOT NULL,
    status ENUM('pending', 'accepted', 'rejected', 'completed')
        NOT NULL DEFAULT 'pending',
    applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    accepted_at DATETIME,
    volunteer_completed_at DATETIME,
    help_seeker_completed_at DATETIME,

    UNIQUE KEY uq_task_volunteer (task_id, volunteer_id),
    FOREIGN KEY (task_id) REFERENCES tasks(task_id)
        ON DELETE CASCADE,
    FOREIGN KEY (volunteer_id) REFERENCES users(user_id)
        ON DELETE RESTRICT,
    INDEX idx_applications_volunteer (volunteer_id)
) ENGINE=InnoDB;

CREATE TABLE reports (
    report_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    reporter_id BIGINT UNSIGNED NOT NULL,
    target_type ENUM('user', 'task', 'other') NOT NULL,
    reported_user_id BIGINT UNSIGNED,
    task_id BIGINT UNSIGNED,
    other_details TEXT,
    reason TEXT NOT NULL,
    contact_allowed BOOLEAN NOT NULL DEFAULT TRUE,
    reviewed_by BIGINT UNSIGNED,
    status ENUM('open', 'reviewing', 'closed')
        NOT NULL DEFAULT 'open',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reviewed_at DATETIME,

    FOREIGN KEY (reporter_id) REFERENCES users(user_id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_reports_reported_user
        FOREIGN KEY (reported_user_id) REFERENCES users(user_id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_reports_task
        FOREIGN KEY (task_id) REFERENCES tasks(task_id)
        ON DELETE RESTRICT,
    FOREIGN KEY (reviewed_by) REFERENCES users(user_id)
        ON DELETE SET NULL,

    -- Exactly one target: a member, a task, or something else (explained).
    CONSTRAINT chk_reports_one_target
        CHECK (
            (target_type = 'user'
                AND reported_user_id IS NOT NULL AND task_id IS NULL)
            OR
            (target_type = 'task'
                AND task_id IS NOT NULL AND reported_user_id IS NULL)
            OR
            (target_type = 'other'
                AND reported_user_id IS NULL AND task_id IS NULL
                AND other_details IS NOT NULL)
        ),

    INDEX idx_reports_status (status)
) ENGINE=InnoDB;

CREATE TABLE reviews (
    review_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    application_id BIGINT UNSIGNED NOT NULL,
    reviewer_id BIGINT UNSIGNED NOT NULL,
    reviewed_user_id BIGINT UNSIGNED NOT NULL,
    rating TINYINT UNSIGNED NOT NULL,
    comment TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    moderation_status ENUM('visible', 'hidden')
        NOT NULL DEFAULT 'visible',
    moderated_by BIGINT UNSIGNED,
    moderated_at DATETIME,
    moderation_reason TEXT,

    CONSTRAINT chk_review_rating CHECK (rating BETWEEN 1 AND 5),
    UNIQUE KEY uq_review_application_reviewer (application_id, reviewer_id),
    FOREIGN KEY (application_id) REFERENCES task_applications(application_id)
        ON DELETE RESTRICT,
    FOREIGN KEY (reviewer_id) REFERENCES users(user_id)
        ON DELETE RESTRICT,
    FOREIGN KEY (reviewed_user_id) REFERENCES users(user_id)
        ON DELETE RESTRICT,
    FOREIGN KEY (moderated_by) REFERENCES users(user_id)
        ON DELETE SET NULL
) ENGINE=InnoDB;

-- MESSAGING (later feature: tables kept for the future version)

CREATE TABLE conversations (
    conversation_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    task_id BIGINT UNSIGNED NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (task_id) REFERENCES tasks(task_id)
        ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE conversation_members (
    conversation_id BIGINT UNSIGNED NOT NULL,
    user_id BIGINT UNSIGNED NOT NULL,
    joined_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_read_at DATETIME,

    PRIMARY KEY (conversation_id, user_id),
    FOREIGN KEY (conversation_id)
        REFERENCES conversations(conversation_id)
        ON DELETE CASCADE,
    FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE messages (
    message_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    conversation_id BIGINT UNSIGNED NOT NULL,
    sender_id BIGINT UNSIGNED NOT NULL,
    content TEXT NOT NULL,
    sent_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (conversation_id)
        REFERENCES conversations(conversation_id)
        ON DELETE CASCADE,
    FOREIGN KEY (sender_id)
        REFERENCES users(user_id)
        ON DELETE RESTRICT
) ENGINE=InnoDB;

-- In-app notifications (email or text messages are a later feature).
CREATE TABLE notifications (
    notification_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT UNSIGNED NOT NULL,
    task_application_id BIGINT UNSIGNED,
    title VARCHAR(120) NOT NULL,
    content TEXT NOT NULL,
    read_at DATETIME,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE CASCADE,
    FOREIGN KEY (task_application_id)
        REFERENCES task_applications(application_id)
        ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE audit_logs (
    audit_log_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    actor_id BIGINT UNSIGNED,
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id BIGINT UNSIGNED,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (actor_id)
        REFERENCES users(user_id)
        ON DELETE SET NULL
) ENGINE=InnoDB;

-- SKILLS SYSTEM (at least one user skill is required to finish onboarding;
-- checked in Flask)

CREATE TABLE skills (
    skill_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    skill_name VARCHAR(80) NOT NULL UNIQUE,
    category VARCHAR(80)
) ENGINE=InnoDB;

CREATE TABLE user_skills (
    user_id BIGINT UNSIGNED NOT NULL,
    skill_id BIGINT UNSIGNED NOT NULL,
    skill_level ENUM('beginner', 'intermediate', 'advanced'),
    selected_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (user_id, skill_id),
    FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE CASCADE,
    FOREIGN KEY (skill_id)
        REFERENCES skills(skill_id)
        ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE task_skills (
    task_id BIGINT UNSIGNED NOT NULL,
    skill_id BIGINT UNSIGNED NOT NULL,
    importance ENUM('required', 'helpful') NOT NULL DEFAULT 'helpful',

    PRIMARY KEY (task_id, skill_id),
    FOREIGN KEY (task_id)
        REFERENCES tasks(task_id)
        ON DELETE CASCADE,
    FOREIGN KEY (skill_id)
        REFERENCES skills(skill_id)
        ON DELETE RESTRICT
) ENGINE=InnoDB;
