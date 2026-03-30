from db.connection import query, query_one, execute, execute_many
from utils.session import Session


# ── Assessments ───────────────────────────────────────────────
def get_assessments(term_id: int = None) -> list:
    sql = """
        SELECT a.*, t.year, t.term AS term_number,
               u.full_name AS created_by_name
        FROM assessments a
        JOIN terms t ON a.term_id = t.id
        LEFT JOIN users u ON a.created_by = u.id
        WHERE 1=1
    """
    params = []
    if term_id:
        sql += " AND a.term_id = ?"
        params.append(term_id)
    sql += " ORDER BY a.created_at DESC"
    return query(sql, tuple(params))


def get_assessment(assessment_id: int) -> dict | None:
    return query_one(
        "SELECT a.*, t.year, t.term AS term_number "
        "FROM assessments a JOIN terms t ON a.term_id = t.id "
        "WHERE a.id = ?",
        (assessment_id,)
    )


def create_assessment(name: str, type_: str,
                      out_of: int = 100,
                      term_id: int = None) -> tuple[bool, str]:
    if not name:
        return False, "Assessment name is required."
    if type_ not in ("CAT", "Exam", "Assignment"):
        return False, "Type must be CAT, Exam or Assignment."
    if not term_id:
        term = query_one("SELECT id FROM terms WHERE is_current=1")
        if not term:
            return False, "No current term set. Please set a term first."
        term_id = term["id"]

    user = Session.get()
    execute(
        "INSERT INTO assessments (term_id, name, type, out_of, created_by) "
        "VALUES (?,?,?,?,?)",
        (term_id, name, type_, out_of, user["id"] if user else None),
    )
    return True, "Assessment created."


def update_assessment(assessment_id: int, name: str,
                      type_: str, out_of: int) -> tuple[bool, str]:
    if not name:
        return False, "Name is required."
    execute(
        "UPDATE assessments SET name=?, type=?, out_of=? WHERE id=?",
        (name, type_, out_of, assessment_id),
    )
    return True, "Assessment updated."


def delete_assessment(assessment_id: int) -> tuple[bool, str]:
    has_marks = query_one(
        "SELECT COUNT(*) AS n FROM marks_new WHERE assessment_id=?",
        (assessment_id,)
    ) or {}
    if has_marks.get("n", 0) > 0:
        return False, "Cannot delete — marks have been entered for this assessment."
    execute("DELETE FROM assessments WHERE id=?", (assessment_id,))
    return True, "Assessment deleted."


# ── Subject enrollments ───────────────────────────────────────
def get_enrolled_students(subject_id: int, class_id: int) -> list:
    """Students enrolled in this subject for this class."""
    return query(
        """
        SELECT s.id, s.full_name, s.admission_number, s.gender
        FROM subject_enrollments se
        JOIN students s ON se.student_id = s.id
        WHERE se.subject_id=? AND se.class_id=? AND s.status='active'
        ORDER BY s.full_name
        """,
        (subject_id, class_id),
    )


def get_all_class_students(class_id: int) -> list:
    return query(
        "SELECT id, full_name, admission_number, gender "
        "FROM students WHERE class_id=? AND status='active' "
        "ORDER BY full_name",
        (class_id,),
    )


def set_enrollments(subject_id: int, class_id: int,
                    student_ids: list[int]) -> None:
    execute(
        "DELETE FROM subject_enrollments WHERE subject_id=? AND class_id=?",
        (subject_id, class_id),
    )
    if student_ids:
        execute_many(
            "INSERT OR IGNORE INTO subject_enrollments "
            "(student_id, subject_id, class_id) VALUES (?,?,?)",
            [(sid, subject_id, class_id) for sid in student_ids],
        )


def is_enrolled(subject_id: int, class_id: int) -> bool:
    """True if any enrollment exists for this subject+class."""
    row = query_one(
        "SELECT COUNT(*) AS n FROM subject_enrollments "
        "WHERE subject_id=? AND class_id=?",
        (subject_id, class_id),
    ) or {}
    return row.get("n", 0) > 0


# ── Marks ─────────────────────────────────────────────────────
def get_marks(assessment_id: int, subject_id: int,
              class_id: int) -> dict:
    """Returns {student_id: {raw_score, percentage, grade}} for fast lookup."""
    rows = query(
        "SELECT student_id, raw_score, out_of, percentage, grade "
        "FROM marks_new WHERE assessment_id=? AND subject_id=? AND class_id=?",
        (assessment_id, subject_id, class_id),
    )
    return {r["student_id"]: dict(r) for r in rows}


def compute_grade(percentage: float) -> str:
    row = query_one(
        "SELECT grade FROM grading_scales "
        "WHERE ? BETWEEN min_score AND max_score LIMIT 1",
        (round(percentage, 1),),
    )
    return row["grade"] if row else "E"


def save_mark(assessment_id: int, subject_id: int,
              class_id: int, student_id: int,
              raw_score: float, out_of: float) -> tuple[bool, str]:
    if raw_score < 0 or raw_score > out_of:
        return False, f"Score must be between 0 and {out_of}."

    percentage = round((raw_score / out_of) * 100, 1) if out_of > 0 else 0
    grade      = compute_grade(percentage)
    user       = Session.get()
    entered_by = user["id"] if user else None

    execute(
        """
        INSERT INTO marks_new
            (student_id, assessment_id, subject_id, class_id,
             raw_score, out_of, percentage, grade, entered_by)
        VALUES (?,?,?,?,?,?,?,?,?)
        ON CONFLICT(student_id, assessment_id, subject_id)
        DO UPDATE SET
            raw_score=excluded.raw_score,
            out_of=excluded.out_of,
            percentage=excluded.percentage,
            grade=excluded.grade,
            entered_by=excluded.entered_by,
            updated_at=CURRENT_TIMESTAMP
        """,
        (student_id, assessment_id, subject_id, class_id,
         raw_score, out_of, percentage, grade, entered_by),
    )
    _audit("MARKS_ENTRY",
           f"student={student_id} assessment={assessment_id} "
           f"subject={subject_id} score={raw_score}/{out_of} ({percentage}%)")
    return True, grade


def _audit(action: str, details: str) -> None:
    user = Session.get()
    execute(
        "INSERT INTO audit_logs (user_id, action, details) VALUES (?,?,?)",
        (user["id"] if user else None, action, details),
    )
