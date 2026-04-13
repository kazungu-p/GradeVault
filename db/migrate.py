import bcrypt
from db.connection import execute_script, query_one, execute

SCHEMA = """
CREATE TABLE IF NOT EXISTS school_settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name     TEXT NOT NULL,
    role          TEXT NOT NULL CHECK(role IN ('admin', 'teacher')),
    is_active     INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_permissions (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    perm    TEXT NOT NULL,
    UNIQUE(user_id, perm)
);

CREATE TABLE IF NOT EXISTS classes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    stream      TEXT,
    is_combined INTEGER NOT NULL DEFAULT 0,
    description TEXT,
    sort_order  INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name, stream)
);

CREATE TABLE IF NOT EXISTS subjects (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL UNIQUE,
    code         TEXT,
    curriculum   TEXT NOT NULL DEFAULT 'all',
    is_active    INTEGER NOT NULL DEFAULT 1,
    created_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS class_subjects (
    class_id   INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    PRIMARY KEY (class_id, subject_id)
);

CREATE TABLE IF NOT EXISTS teacher_assignments (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    class_id   INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    UNIQUE(user_id, subject_id, class_id)
);

CREATE TABLE IF NOT EXISTS students (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name        TEXT NOT NULL,
    admission_number TEXT NOT NULL UNIQUE,
    class_id         INTEGER NOT NULL REFERENCES classes(id),
    gender           TEXT CHECK(gender IN ('M', 'F', NULL)),
    status           TEXT NOT NULL DEFAULT 'active'
                         CHECK(status IN ('active', 'archived')),
    created_at       TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at       TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS terms (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    year       INTEGER NOT NULL,
    term       INTEGER NOT NULL CHECK(term IN (1, 2, 3)),
    is_current INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(year, term)
);

-- legacy stub (safe to ignore)
CREATE TABLE IF NOT EXISTS _assessments_old (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    term_id    INTEGER NOT NULL REFERENCES terms(id),
    class_id   INTEGER NOT NULL REFERENCES classes(id),
    type       TEXT NOT NULL CHECK(type IN ('CAT', 'Exam', 'Assignment')),
    name       TEXT NOT NULL,
    out_of     INTEGER NOT NULL DEFAULT 100,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- legacy stub (safe to ignore)
CREATE TABLE IF NOT EXISTS _marks_old (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id    INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    assessment_id INTEGER NOT NULL REFERENCES assessments(id) ON DELETE CASCADE,
    subject_id    INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    score         REAL NOT NULL CHECK(score >= 0 AND score <= 100),
    entered_by    INTEGER REFERENCES users(id),
    created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(student_id, assessment_id, subject_id)
);


CREATE TABLE IF NOT EXISTS subject_enrollments (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    class_id   INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    UNIQUE(student_id, subject_id, class_id)
);

CREATE TABLE IF NOT EXISTS assessments (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    term_id    INTEGER NOT NULL REFERENCES terms(id),
    name       TEXT NOT NULL,
    type       TEXT NOT NULL CHECK(type IN ('CAT', 'Exam', 'Assignment')),
    out_of     INTEGER NOT NULL DEFAULT 100,
    created_by INTEGER REFERENCES users(id),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS marks_new (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id    INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    assessment_id INTEGER NOT NULL REFERENCES assessments(id) ON DELETE CASCADE,
    subject_id    INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    class_id      INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    raw_score     REAL,
    out_of        REAL NOT NULL DEFAULT 100,
    percentage    REAL,
    grade         TEXT,
    entered_by    INTEGER REFERENCES users(id),
    created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(student_id, assessment_id, subject_id)
);


CREATE TABLE IF NOT EXISTS student_contacts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id   INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    name         TEXT NOT NULL,
    relationship TEXT NOT NULL DEFAULT 'Parent',
    phone        TEXT NOT NULL,
    is_primary   INTEGER NOT NULL DEFAULT 0,
    created_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sms_log (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    recipient    TEXT NOT NULL,
    phone        TEXT NOT NULL,
    message      TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'pending',
    provider_id  TEXT,
    cost         TEXT,
    sent_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS grading_scales (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    min_score  REAL NOT NULL,
    max_score  REAL NOT NULL,
    grade      TEXT NOT NULL,
    points     REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER REFERENCES users(id),
    action     TEXT NOT NULL,
    details    TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

KCSE_SCALE = [
    ("KCSE Standard", 80, 100, "A",  12),
    ("KCSE Standard", 75, 79,  "A-", 11),
    ("KCSE Standard", 70, 74,  "B+", 10),
    ("KCSE Standard", 65, 69,  "B",  9),
    ("KCSE Standard", 60, 64,  "B-", 8),
    ("KCSE Standard", 55, 59,  "C+", 7),
    ("KCSE Standard", 50, 54,  "C",  6),
    ("KCSE Standard", 45, 49,  "C-", 5),
    ("KCSE Standard", 40, 44,  "D+", 4),
    ("KCSE Standard", 35, 39,  "D",  3),
    ("KCSE Standard", 30, 34,  "D-", 2),
    ("KCSE Standard",  0, 29,  "E",  1),
]



def _ensure_new_tables():
    """Create any tables added after initial migration."""
    from db.connection import get_connection
    conn = get_connection()
    existing = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    if "student_contacts" not in existing:
        conn.execute("""CREATE TABLE IF NOT EXISTS student_contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            relationship TEXT NOT NULL DEFAULT 'Parent',
            phone TEXT NOT NULL,
            is_primary INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")
        conn.commit()
    if "sms_log" not in existing:
        conn.execute("""CREATE TABLE IF NOT EXISTS sms_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recipient TEXT NOT NULL,
            phone TEXT NOT NULL,
            message TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            provider_id TEXT,
            cost TEXT,
            sent_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")
        conn.commit()
    conn.close()

def _add_columns_if_missing():
    """Safely add new columns to existing databases."""
    from db.connection import get_connection
    conn = get_connection()
    cursor = conn.execute("PRAGMA table_info(classes)")
    existing_cols = [row[1] for row in cursor.fetchall()]
    
    if "is_combined" not in existing_cols:
        conn.execute("ALTER TABLE classes ADD COLUMN is_combined INTEGER NOT NULL DEFAULT 0")
        conn.commit()
        print("Added is_combined column to classes.")
    if "description" not in existing_cols:
        conn.execute("ALTER TABLE classes ADD COLUMN description TEXT")
        conn.commit()
        print("Added description column to classes.")
    conn.close()

def run():
    print("Running GradeVault migrations...")
    execute_script(SCHEMA)
    _add_columns_if_missing()
    _ensure_new_tables()

    # Default admin
    if not query_one("SELECT id FROM users WHERE username = 'admin'"):
        # Temporary password — setup wizard forces the admin to change this on first run
        pw_hash = bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode()
        execute(
            "INSERT INTO users (username, password_hash, full_name, role) "
            "VALUES (?,?,?,?)",
            ("admin", pw_hash, "System Administrator", "admin"),
        )
        print("Default admin created — username: admin / password: admin123")
        print("The setup wizard will prompt you to change this password.")

    # KCSE grading scale
    if not query_one("SELECT id FROM grading_scales LIMIT 1"):
        from db.connection import execute_many
        execute_many(
            "INSERT INTO grading_scales "
            "(name, min_score, max_score, grade, points) VALUES (?,?,?,?,?)",
            KCSE_SCALE,
        )

    print("Migrations complete.")


if __name__ == "__main__":
    run()
