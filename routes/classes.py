from db.connection import query, query_one, execute


# ── Classes ───────────────────────────────────────────────────
def get_classes() -> list:
    return query(
        "SELECT * FROM classes ORDER BY sort_order, name, stream"
    )


def create_class(name: str, stream: str = None,
                 sort_order: int = 0) -> tuple[bool, str]:
    name = name.strip()
    stream = stream.strip() if stream and stream.strip() else None
    if not name:
        return False, "Class name is required."
    existing = query_one(
        "SELECT id FROM classes WHERE name=? AND (stream=? OR (stream IS NULL AND ? IS NULL))",
        (name, stream, stream),
    )
    if existing:
        label = f"{name} {stream}" if stream else name
        return False, f"'{label}' already exists."
    execute(
        "INSERT INTO classes (name, stream, sort_order) VALUES (?,?,?)",
        (name, stream, sort_order),
    )
    return True, "Class created."


def update_class(class_id: int, name: str,
                 stream: str = None) -> tuple[bool, str]:
    name = name.strip()
    stream = stream.strip() if stream and stream.strip() else None
    if not name:
        return False, "Class name is required."
    execute(
        "UPDATE classes SET name=?, stream=? WHERE id=?",
        (name, stream, class_id),
    )
    return True, "Class updated."


def delete_class(class_id: int) -> tuple[bool, str]:
    students = query_one(
        "SELECT COUNT(*) AS n FROM students WHERE class_id=?", (class_id,)
    )
    if students and students["n"] > 0:
        return False, "Cannot delete — students are enrolled in this class."
    execute("DELETE FROM classes WHERE id=?", (class_id,))
    return True, "Class deleted."


def bulk_promote(from_class_id: int,
                 to_class_id: int) -> tuple[bool, str]:
    """Move all active students from one class to another."""
    count = query_one(
        "SELECT COUNT(*) AS n FROM students "
        "WHERE class_id=? AND status='active'",
        (from_class_id,),
    )
    n = count["n"] if count else 0
    if n == 0:
        return False, "No active students in this class."
    execute(
        "UPDATE students SET class_id=?, updated_at=CURRENT_TIMESTAMP "
        "WHERE class_id=? AND status='active'",
        (to_class_id, from_class_id),
    )
    return True, f"{n} student(s) promoted."


# ── Subjects ─────────────────────────────────────────────────
def get_subjects(active_only: bool = False) -> list:
    sql = "SELECT * FROM subjects"
    if active_only:
        sql += " WHERE is_active=1"
    sql += " ORDER BY name"
    return query(sql)


def create_subject(name: str, code: str = None,
                   curriculum: str = "all") -> tuple[bool, str]:
    name = name.strip()
    if not name:
        return False, "Subject name is required."
    if query_one("SELECT id FROM subjects WHERE name=?", (name,)):
        return False, f"'{name}' already exists."
    execute(
        "INSERT INTO subjects (name, code, curriculum) VALUES (?,?,?)",
        (name, code or None, curriculum),
    )
    return True, "Subject created."


def update_subject(subject_id: int, name: str,
                   code: str = None,
                   curriculum: str = "all") -> tuple[bool, str]:
    name = name.strip()
    if not name:
        return False, "Subject name is required."
    dup = query_one(
        "SELECT id FROM subjects WHERE name=? AND id!=?", (name, subject_id)
    )
    if dup:
        return False, f"'{name}' already exists."
    execute(
        "UPDATE subjects SET name=?, code=?, curriculum=? WHERE id=?",
        (name, code or None, curriculum, subject_id),
    )
    return True, "Subject updated."


def delete_subject(subject_id: int) -> tuple[bool, str]:
    marks = query_one(
        "SELECT COUNT(*) AS n FROM marks_new WHERE subject_id=?", (subject_id,)
    )
    if marks and marks["n"] > 0:
        return False, "Cannot delete — marks exist for this subject."
    execute("DELETE FROM subjects WHERE id=?", (subject_id,))
    return True, "Subject deleted."


def toggle_subject_active(subject_id: int) -> None:
    row = query_one("SELECT is_active FROM subjects WHERE id=?", (subject_id,))
    if row:
        execute(
            "UPDATE subjects SET is_active=? WHERE id=?",
            (0 if row["is_active"] else 1, subject_id),
        )


def retire_class(class_id: int, action: str) -> tuple[bool, str]:
    """
    Retire a class at year end.
    action = 'archive' — archive all students, keep class
    action = 'delete'  — archive all students, then delete class
    """
    from db.connection import execute, query_one
    count = query_one(
        "SELECT COUNT(*) AS n FROM students "
        "WHERE class_id=? AND status='active'", (class_id,)
    ) or {}
    n = count.get("n", 0)
    execute(
        "UPDATE students SET status='archived', updated_at=CURRENT_TIMESTAMP "
        "WHERE class_id=? AND status='active'", (class_id,)
    )
    if action == "delete":
        execute("DELETE FROM classes WHERE id=?", (class_id,))
        return True, f"{n} student(s) archived and class removed."
    return True, f"{n} student(s) archived. Class kept for records."
