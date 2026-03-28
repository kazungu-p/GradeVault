from db.connection import query, query_one, execute
from utils.session import Session


def get_students(search: str = "", class_id: int = None, status: str = "active") -> list:
    sql = """
        SELECT s.*, c.name AS class_name, c.stream
        FROM students s
        LEFT JOIN classes c ON s.class_id = c.id
        WHERE s.status = ?
    """
    params = [status]

    if search:
        sql += " AND (s.full_name LIKE ? OR s.admission_number LIKE ?)"
        params += [f"%{search}%", f"%{search}%"]

    if class_id:
        sql += " AND s.class_id = ?"
        params.append(class_id)

    sql += " ORDER BY c.name, c.stream, s.full_name"
    return [dict(r) for r in query(sql, tuple(params))]


def get_student(student_id: int) -> dict | None:
    row = query_one(
        "SELECT s.*, c.name AS class_name, c.stream "
        "FROM students s LEFT JOIN classes c ON s.class_id = c.id "
        "WHERE s.id = ?",
        (student_id,),
    )
    return dict(row) if row else None


def create_student(full_name: str, admission_number: str,
                   class_id: int, gender: str = None) -> tuple[bool, str]:
    if not full_name or not admission_number or not class_id:
        return False, "Full name, admission number and class are required."

    if query_one("SELECT id FROM students WHERE admission_number = ?", (admission_number,)):
        return False, f"Admission number '{admission_number}' already exists."

    new_id = execute(
        "INSERT INTO students (full_name, admission_number, class_id, gender) VALUES (?,?,?,?)",
        (full_name, admission_number, class_id, gender),
    )
    _audit("STUDENT_CREATE", f"Created student {admission_number}")
    return True, str(new_id)


def update_student(student_id: int, full_name: str, admission_number: str,
                   class_id: int, gender: str = None) -> tuple[bool, str]:
    existing = query_one(
        "SELECT id FROM students WHERE admission_number = ? AND id != ?",
        (admission_number, student_id),
    )
    if existing:
        return False, f"Admission number '{admission_number}' is taken by another student."

    execute(
        "UPDATE students SET full_name=?, admission_number=?, class_id=?, gender=?, "
        "updated_at=CURRENT_TIMESTAMP WHERE id=?",
        (full_name, admission_number, class_id, gender, student_id),
    )
    _audit("STUDENT_EDIT", f"Edited student id={student_id}")
    return True, "Student updated."


def transfer_student(student_id: int, new_class_id: int) -> None:
    execute(
        "UPDATE students SET class_id=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
        (new_class_id, student_id),
    )
    _audit("STUDENT_TRANSFER", f"Transferred student id={student_id} to class {new_class_id}")


def archive_student(student_id: int) -> None:
    execute(
        "UPDATE students SET status='archived', updated_at=CURRENT_TIMESTAMP WHERE id=?",
        (student_id,),
    )
    _audit("STUDENT_ARCHIVE", f"Archived student id={student_id}")


def get_classes() -> list:
    return [dict(r) for r in query("SELECT * FROM classes ORDER BY name, stream")]


def _audit(action: str, details: str) -> None:
    user = Session.get()
    user_id = user["id"] if user else None
    execute(
        "INSERT INTO audit_logs (user_id, action, details) VALUES (?,?,?)",
        (user_id, action, details),
    )
