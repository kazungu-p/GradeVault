from db.connection import query, query_one, execute, execute_many
from utils.session import Session


def get_marks(assessment_id: int) -> list:
    return [dict(r) for r in query(
        """
        SELECT m.*, s.full_name, s.admission_number
        FROM marks m
        JOIN students s ON m.student_id = s.id
        WHERE m.assessment_id = ?
        ORDER BY s.full_name
        """,
        (assessment_id,),
    )]


def upsert_mark(student_id: int, assessment_id: int,
                subject_id: int, score: float) -> tuple[bool, str]:
    if not (0 <= score <= 100):
        return False, "Score must be between 0 and 100."

    user = Session.get()
    entered_by = user["id"] if user else None

    execute(
        """
        INSERT INTO marks (student_id, assessment_id, subject_id, score, entered_by)
        VALUES (?,?,?,?,?)
        ON CONFLICT(student_id, assessment_id, subject_id)
        DO UPDATE SET score=excluded.score,
                      updated_at=CURRENT_TIMESTAMP,
                      entered_by=excluded.entered_by
        """,
        (student_id, assessment_id, subject_id, score, entered_by),
    )
    _audit("MARKS_ENTRY",
           f"student={student_id} assessment={assessment_id} subject={subject_id} score={score}")
    return True, "Mark saved."


def bulk_upsert_marks(marks: list[dict]) -> tuple[bool, str]:
    """marks: list of {student_id, assessment_id, subject_id, score}"""
    for m in marks:
        if not (0 <= m["score"] <= 100):
            return False, f"Invalid score {m['score']} for student {m['student_id']}."

    user = Session.get()
    entered_by = user["id"] if user else None

    execute_many(
        """
        INSERT INTO marks (student_id, assessment_id, subject_id, score, entered_by)
        VALUES (?,?,?,?,?)
        ON CONFLICT(student_id, assessment_id, subject_id)
        DO UPDATE SET score=excluded.score,
                      updated_at=CURRENT_TIMESTAMP,
                      entered_by=excluded.entered_by
        """,
        [(m["student_id"], m["assessment_id"], m["subject_id"], m["score"], entered_by)
         for m in marks],
    )
    _audit("MARKS_BULK", f"Bulk inserted {len(marks)} marks")
    return True, f"{len(marks)} marks saved."


def get_grade(score: float) -> tuple[str, float]:
    """Returns (grade_letter, points) for a given score using KCSE scale."""
    row = query_one(
        "SELECT grade, points FROM grading_scales "
        "WHERE ? BETWEEN min_score AND max_score LIMIT 1",
        (score,),
    )
    return (row["grade"], row["points"]) if row else ("E", 1)


def get_assessments(class_id: int = None, term_id: int = None) -> list:
    sql = "SELECT a.*, c.name AS class_name, c.stream, t.year, t.term AS term_number " \
          "FROM assessments a " \
          "JOIN classes c ON a.class_id = c.id " \
          "JOIN terms t ON a.term_id = t.id WHERE 1=1"
    params = []
    if class_id:
        sql += " AND a.class_id = ?"; params.append(class_id)
    if term_id:
        sql += " AND a.term_id = ?"; params.append(term_id)
    sql += " ORDER BY a.created_at DESC"
    return [dict(r) for r in query(sql, tuple(params))]


def get_subjects() -> list:
    return [dict(r) for r in query("SELECT * FROM subjects ORDER BY name")]


def _audit(action: str, details: str) -> None:
    user = Session.get()
    user_id = user["id"] if user else None
    execute(
        "INSERT INTO audit_logs (user_id, action, details) VALUES (?,?,?)",
        (user_id, action, details),
    )
