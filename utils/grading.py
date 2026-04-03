from db.connection import query, query_one

# ── Default scales (fallback) ────────────────────────────────
_KCSE_DEFAULT = [
    (80, 100, "A",  12), (75, 79, "A-", 11), (70, 74, "B+", 10),
    (65, 69, "B",    9), (60, 64, "B-",  8), (55, 59, "C+",  7),
    (50, 54, "C",    6), (45, 49, "C-",  5), (40, 44, "D+",  4),
    (35, 39, "D",    3), (30, 34, "D-",  2), (0,  29, "E",    1),
]
_CBE_DEFAULT = [
    (75, 100, "EE", 4), (50, 74, "ME", 3),
    (25, 49,  "AE", 2), (0,  24, "BE", 1),
]


def _load_scale(prefix: str, defaults: list) -> list:
    """Load grading scale from settings, falling back to defaults."""
    from routes.settings import get_setting
    result = []
    for _, _, grade, _ in defaults:
        try:
            min_s = float(get_setting(f"{prefix}_{grade}_min", ""))
            max_s = float(get_setting(f"{prefix}_{grade}_max", ""))
            pts   = float(get_setting(f"{prefix}_{grade}_pts", ""))
            result.append((min_s, max_s, grade, int(pts)))
        except (ValueError, TypeError):
            # Fall back to default for this grade
            orig = next(d for d in defaults if d[2] == grade)
            result.append(orig)
    return result if result else defaults


def _get_kcse_scale():
    return _load_scale("kcse", _KCSE_DEFAULT)

def _get_cbe_scale():
    return _load_scale("cbe", _CBE_DEFAULT)

# Keep module-level names for backward compat
KCSE_SCALE = _KCSE_DEFAULT
CBE_SCALE  = _CBE_DEFAULT

LANGUAGE_SUBJECTS = {"english", "kiswahili", "english language",
                     "kiswahili language", "fasihi"}

CBE_CLASS_PREFIXES = {"grade 7", "grade 8", "grade 9",
                      "grade 10", "grade 11", "grade 12"}


def detect_curriculum(class_name: str) -> str:
    """Returns '8-4-4' or 'CBE' based on class name."""
    name = (class_name or "").lower().strip()
    for prefix in CBE_CLASS_PREFIXES:
        if name.startswith(prefix):
            return "CBE"
    return "8-4-4"


def grade_from_percentage(percentage: float, curriculum: str) -> tuple[str, int]:
    """Returns (grade_letter, points) using saved grading scale."""
    scale = _get_cbe_scale() if curriculum == "CBE" else _get_kcse_scale()
    for min_s, max_s, grade, points in scale:
        if min_s <= round(percentage, 1) <= max_s:
            return grade, points
    return ("BE" if curriculum == "CBE" else "E"), 1


def subject_comment(grade: str, curriculum: str) -> str:
    """Auto-comment based on grade."""
    kcse_comments = {
        "A":  "Outstanding performance. Exceptional ability demonstrated.",
        "A-": "Excellent performance. Very strong grasp of the subject.",
        "B+": "Very good performance. Above average understanding.",
        "B":  "Good performance. Solid understanding of the subject.",
        "B-": "Good performance. Continues to show good progress.",
        "C+": "Satisfactory performance. Some improvement needed.",
        "C":  "Fair performance. More effort and practice required.",
        "C-": "Below average. Needs to put in more effort consistently.",
        "D+": "Poor performance. Significant improvement needed.",
        "D":  "Poor performance. Must seek extra help immediately.",
        "D-": "Very poor performance. Urgent attention required.",
        "E":  "Fail. Must retake and put in maximum effort.",
    }
    cbe_comments = {
        "EE": "Exceeds expectations. Outstanding achievement.",
        "ME": "Meets expectations. Good and consistent performance.",
        "AE": "Approaches expectations. More effort needed to meet standards.",
        "BE": "Below expectations. Requires significant improvement and support.",
    }
    comments = cbe_comments if curriculum == "CBE" else kcse_comments
    return comments.get(grade, "")


def performance_band(mean_pct: float) -> str:
    if mean_pct >= 70:   return "excellent"
    if mean_pct >= 55:   return "good"
    if mean_pct >= 40:   return "average"
    return "below_average"


def select_best_7(subject_marks: list[dict]) -> list[dict]:
    """
    Apply KCSE best-7 rule:
      1. Mathematics (compulsory)
      2. Best language (English or Kiswahili)
      3. Best 5 from remaining subjects
    Total = 7. If fewer than 7 subjects exist, pad with zero-score
    placeholder subjects so the mean is correctly penalized.
    Returns exactly 7 entries.
    """
    remaining = list(subject_marks)
    selected  = []

    # 1. Mathematics — compulsory
    maths = next((s for s in remaining
                  if "math" in s["subject_name"].lower()), None)
    if maths:
        selected.append(maths)
        remaining.remove(maths)
    else:
        # No maths — add a zero placeholder
        selected.append(_zero_subject("Mathematics"))

    # 2. Best language
    languages = [s for s in remaining
                 if s["subject_name"].lower() in LANGUAGE_SUBJECTS]
    if languages:
        best_lang = max(languages, key=lambda x: x["percentage"])
        selected.append(best_lang)
        remaining.remove(best_lang)
    else:
        selected.append(_zero_subject("Language"))

    # 3. Best 5 from remaining
    remaining_sorted = sorted(remaining,
                               key=lambda x: x["percentage"], reverse=True)
    selected.extend(remaining_sorted[:5])

    # 4. Pad with zeros if fewer than 7 subjects
    while len(selected) < 7:
        selected.append(_zero_subject(f"Subject {len(selected)+1}"))

    return selected[:7]


def _zero_subject(name: str) -> dict:
    """Placeholder subject with 0% for padding."""
    return {
        "subject_name": name,
        "raw_score":    0,
        "out_of":       100,
        "percentage":   0.0,
        "grade":        "E",
        "points":       1,
        "comment":      "No marks entered.",
        "is_padding":   True,
    }


def compute_student_result(student_id: int, assessment_id: int,
                            class_name: str) -> dict:
    """
    Compute full result for one student:
    - All subject marks
    - Best 7 selection (8-4-4) or all subjects (CBE)
    - Aggregate mean, grade, points
    """
    curriculum = detect_curriculum(class_name)

    rows = query(
        """
        SELECT m.percentage, m.raw_score, m.out_of,
               s.name AS subject_name
        FROM marks_new m
        JOIN subjects s ON m.subject_id = s.id
        WHERE m.student_id = ? AND m.assessment_id = ?
        ORDER BY s.name
        """,
        (student_id, assessment_id),
    )

    if not rows:
        return {"subjects": [], "selected": [], "mean": 0,
                "grade": "—", "points": 0, "curriculum": curriculum}

    subject_marks = []
    for r in rows:
        pct   = round(r["percentage"] or 0, 1)
        grade, pts = grade_from_percentage(pct, curriculum)
        subject_marks.append({
            "subject_name": r["subject_name"],
            "raw_score":    r["raw_score"],
            "out_of":       r["out_of"],
            "percentage":   pct,
            "grade":        grade,
            "points":       pts,
            "comment":      subject_comment(grade, curriculum),
        })

    # Select subjects for aggregate
    if curriculum == "8-4-4":
        selected = select_best_7(subject_marks)
    else:
        selected = subject_marks  # CBE uses all subjects

    if selected:
        mean  = round(sum(s["percentage"] for s in selected) / len(selected), 1)
        grade, points = grade_from_percentage(mean, curriculum)
    else:
        mean, grade, points = 0, "—", 0

    return {
        "subjects":   selected,        # only selected 7 shown on report
        "all_subjects": subject_marks, # kept for reference
        "selected":   selected,
        "mean":       mean,
        "grade":      grade,
        "points":     points,
        "band":       performance_band(mean),
        "curriculum": curriculum,
    }


def compute_class_results(assessment_id: int, class_id: int) -> list[dict]:
    """
    Compute results for all students in a class, add position ranking.
    Returns list sorted by mean descending with position added.
    """
    students = query(
        "SELECT id, full_name, admission_number, gender "
        "FROM students WHERE class_id=? AND status='active' "
        "ORDER BY full_name",
        (class_id,),
    )

    cls = query_one("SELECT name FROM classes WHERE id=?", (class_id,)) or {}
    class_name = cls.get("name", "")

    results = []
    for s in students:
        result = compute_student_result(s["id"], assessment_id, class_name)
        results.append({
            "student_id":       s["id"],
            "full_name":        s["full_name"],
            "admission_number": s["admission_number"],
            "gender":           s.get("gender", ""),
            **result,
        })

    # Rank by mean descending
    results.sort(key=lambda x: x["mean"], reverse=True)
    pos = 1
    for i, r in enumerate(results):
        if i > 0 and r["mean"] < results[i-1]["mean"]:
            pos = i + 1
        r["position"] = pos

    return results
