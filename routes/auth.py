import bcrypt
from db.connection import query_one, execute
from utils.session import Session


def login(username: str, password: str) -> dict | None:
    """
    Attempt login. Returns user dict on success, None on failure.
    Also writes to audit_logs.
    """
    if not username or not password:
        return None

    row = query_one(
        "SELECT id, username, password_hash, role, full_name "
        "FROM users WHERE username = ? AND is_active = 1",
        (username,),
    )
    if not row:
        return None

    if not bcrypt.checkpw(password.encode(), row["password_hash"].encode()):
        return None

    execute(
        "INSERT INTO audit_logs (user_id, action, details) VALUES (?,?,?)",
        (row["id"], "LOGIN", f"User {username} logged in"),
    )

    user = {
        "id":       row["id"],
        "username": row["username"],
        "role":     row["role"],
        "fullName": row["full_name"],
    }
    Session.set(user)
    return user


def logout() -> None:
    user = Session.get()
    if user:
        execute(
            "INSERT INTO audit_logs (user_id, action, details) VALUES (?,?,?)",
            (user["id"], "LOGOUT", f"User {user['username']} logged out"),
        )
    Session.clear()


def change_password(user_id: int, current_pw: str,
                    new_pw: str) -> tuple[bool, str]:
    import bcrypt
    from db.connection import query_one, execute
    user = query_one("SELECT password_hash FROM users WHERE id=?",
                     (user_id,))
    if not user:
        return False, "User not found."
    if not bcrypt.checkpw(current_pw.encode(),
                           user["password_hash"].encode()):
        return False, "Current password is incorrect."
    new_hash = bcrypt.hashpw(new_pw.encode(), bcrypt.gensalt()).decode()
    execute("UPDATE users SET password_hash=? WHERE id=?",
            (new_hash, user_id))
    return True, "Password changed."
