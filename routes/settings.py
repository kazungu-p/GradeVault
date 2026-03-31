from db.connection import query_one, execute, query


def get_setting(key: str, default: str = "") -> str:
    row = query_one("SELECT value FROM school_settings WHERE key = ?", (key,))
    return row["value"] if row else default


def set_setting(key: str, value: str) -> None:
    execute(
        "INSERT INTO school_settings (key, value) VALUES (?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )


def is_setup_complete() -> bool:
    return get_setting("setup_complete") == "1"


def mark_setup_complete() -> None:
    set_setting("setup_complete", "1")


def get_all_settings() -> dict:
    rows = query("SELECT key, value FROM school_settings")
    return {r["key"]: r["value"] for r in rows}


# ── Permissions ───────────────────────────────────────────────
ALL_PERMISSIONS = [
    ("enter_marks",      "Enter marks",         "Enter marks for assigned subjects & classes"),
    ("manage_students",  "Manage students",      "Add, edit, transfer and archive students"),
    ("manage_exams",     "Manage exams",         "Create and manage assessments & CATs"),
    ("generate_reports", "Generate reports",     "Export report cards and performance reports"),
    ("view_all_classes", "View all classes",     "View students and marks across all classes"),
    ("manage_users",     "Manage users",         "Add and edit teacher accounts"),
    ("manage_subjects",  "Manage subjects",      "Add, edit and delete subjects and classes"),
    ("manage_term",      "Manage term",          "Set and switch the current academic term"),
]


def get_user_permissions(user_id: int) -> list[str]:
    rows = query(
        "SELECT perm FROM user_permissions WHERE user_id = ?", (user_id,)
    )
    return [r["perm"] for r in rows]


def set_user_permissions(user_id: int, perms: list[str]) -> None:
    execute("DELETE FROM user_permissions WHERE user_id = ?", (user_id,))
    from db.connection import execute_many
    execute_many(
        "INSERT OR IGNORE INTO user_permissions (user_id, perm) VALUES (?,?)",
        [(user_id, p) for p in perms],
    )


def has_permission(user_id: int, perm: str) -> bool:
    return bool(query_one(
        "SELECT 1 FROM user_permissions WHERE user_id=? AND perm=?",
        (user_id, perm),
    ))
