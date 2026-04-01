import bcrypt
from db.connection import query, query_one, execute, execute_many
from utils.session import Session


def get_users(role: str = None) -> list:
    sql = """
        SELECT id, username, full_name, role, is_active, created_at
        FROM users
        WHERE 1=1
    """
    params = []
    if role:
        sql += " AND role = ?"
        params.append(role)
    sql += " ORDER BY role, full_name"
    return query(sql, tuple(params))


def get_user(user_id: int) -> dict | None:
    return query_one(
        "SELECT id, username, full_name, role, is_active FROM users WHERE id = ?",
        (user_id,)
    )


def create_user(username: str, full_name: str, role: str,
                password: str) -> tuple[bool, str]:
    if not username or not full_name or not password:
        return False, "Username, full name and password are required."
    if role not in ("admin", "teacher"):
        return False, "Role must be admin or teacher."
    if query_one("SELECT id FROM users WHERE username = ?", (username,)):
        return False, f"Username '{username}' is already taken."
    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    execute(
        "INSERT INTO users (username, password_hash, full_name, role) VALUES (?,?,?,?)",
        (username, pw_hash, full_name, role),
    )
    _audit("USER_CREATE", f"Created user {username} ({role})")
    return True, "User created."


def update_user(user_id: int, full_name: str, role: str,
                new_password: str = None) -> tuple[bool, str]:
    if not full_name:
        return False, "Full name is required."
    if role not in ("admin", "teacher"):
        return False, "Role must be admin or teacher."
    if new_password:
        pw_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
        execute(
            "UPDATE users SET full_name=?, role=?, password_hash=?, "
            "updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (full_name, role, pw_hash, user_id),
        )
    else:
        execute(
            "UPDATE users SET full_name=?, role=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (full_name, role, user_id),
        )
    _audit("USER_EDIT", f"Edited user id={user_id}")
    return True, "User updated."


def toggle_user_active(user_id: int) -> None:
    row = query_one("SELECT is_active FROM users WHERE id = ?", (user_id,))
    if row:
        new_state = 0 if row["is_active"] else 1
        execute("UPDATE users SET is_active=? WHERE id=?", (new_state, user_id))
        _audit("USER_TOGGLE", f"User id={user_id} active={new_state}")


# ── Teacher assignments ───────────────────────────────────────
def get_assignments(user_id: int) -> list:
    return query(
        """
        SELECT ta.id, ta.subject_id, ta.class_id,
               s.name AS subject_name,
               c.name AS class_name, c.stream
        FROM teacher_assignments ta
        JOIN subjects s ON ta.subject_id = s.id
        JOIN classes  c ON ta.class_id  = c.id
        WHERE ta.user_id = ?
        ORDER BY c.name, c.stream, s.name
        """,
        (user_id,),
    )


def assign_teacher(user_id: int, subject_id: int,
                   class_id: int) -> tuple[bool, str]:
    # Check if already assigned to this user
    existing = query_one(
        "SELECT id FROM teacher_assignments "
        "WHERE user_id=? AND subject_id=? AND class_id=?",
        (user_id, subject_id, class_id),
    )
    if existing:
        return False, "This assignment already exists for this teacher."

    # Check if another teacher already has this subject+class
    taken = query_one(
        """
        SELECT u.full_name
        FROM teacher_assignments ta
        JOIN users u ON ta.user_id = u.id
        WHERE ta.subject_id=? AND ta.class_id=? AND ta.user_id != ?
        """,
        (subject_id, class_id, user_id),
    )
    if taken:
        return False, f"Already assigned to {taken['full_name']}. Only one teacher per subject/class."

    execute(
        "INSERT INTO teacher_assignments (user_id, subject_id, class_id) VALUES (?,?,?)",
        (user_id, subject_id, class_id),
    )
    _audit("TEACHER_ASSIGN",
           f"Assigned user={user_id} subject={subject_id} class={class_id}")
    return True, "Assignment added."


def remove_assignment(assignment_id: int) -> None:
    execute("DELETE FROM teacher_assignments WHERE id=?", (assignment_id,))
    _audit("TEACHER_UNASSIGN", f"Removed assignment id={assignment_id}")


def get_subjects() -> list:
    return query("SELECT * FROM subjects ORDER BY name")


def get_classes() -> list:
    return query("SELECT * FROM classes ORDER BY name, stream")


def _audit(action: str, details: str) -> None:
    user = Session.get()
    user_id = user["id"] if user else None
    execute(
        "INSERT INTO audit_logs (user_id, action, details) VALUES (?,?,?)",
        (user_id, action, details),
    )
