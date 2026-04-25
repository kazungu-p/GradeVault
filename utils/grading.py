from db.connection import query, query_one

# ── Default scales (fallback) ────────────────────────────────
_KCSE_DEFAULT = [
    (80, 100, "A",  12), (75, 79, "A-", 11), (70, 74, "B+", 10),
    (65, 69, "B",    9), (60, 64, "B-",  8), (55, 59, "C+",  7),
    (50, 54, "C",    6), (45, 49, "C-",  5), (40, 44, "D+",  4),
    (35, 39, "D",    3), (30, 34, "D-",  2), (0,  29, "E",    1),
]
_CBE_DEFAULT = [
    (90, 100, "EE2", 4), (75, 89, "EE1", 4),
    (65,  74, "ME2", 3), (50, 64, "ME1", 3),
    (35,  49, "AE2", 2), (25, 34, "AE1", 2),
    (10,  24, "BE2", 1), (0,   9, "BE1", 1),
]

# Simplified 4-band CBC scale (used for settings display)
_CBE_BANDS = [
    (75, 100, "EE", 4),
    (50,  74, "ME", 3),
    (25,  49, "AE", 2),
    (0,   24, "BE", 1),
]



# ── In-memory scale cache ─────────────────────────────────────
_scale_cache: dict = {}

def invalidate_scale_cache():
    """Call this when grading scales are saved in settings."""
    global _scale_cache
    _scale_cache.clear()

def _load_scale(prefix: str, defaults: list) -> list:
    """Load grading scale from settings with in-memory cache."""
    global _scale_cache
    if prefix in _scale_cache:
        return _scale_cache[prefix]
    try:
        from routes.settings import get_setting
        result = []
        for min_def, max_def, grade, pts_def in defaults:
            try:
                saved_min = get_setting(f"{prefix}_{grade}_min", "")
                saved_max = get_setting(f"{prefix}_{grade}_max", "")
                saved_pts = get_setting(f"{prefix}_{grade}_pts", "")
                min_s = float(saved_min) if saved_min else float(min_def)
                max_s = float(saved_max) if saved_max else float(max_def)
                pts   = int(float(saved_pts)) if saved_pts else int(pts_def)
                result.append((min_s, max_s, grade, pts))
            except (ValueError, TypeError):
                result.append((min_def, max_def, grade, pts_def))
        scale = result if result else defaults
        _scale_cache[prefix] = scale
        return scale
    except Exception:
        return defaults


def _get_kcse_scale():
    return _load_scale("kcse", _KCSE_DEFAULT)

def _get_cbe_scale():
    return _load_scale("cbe", _CBE_DEFAULT)

# Keep module-level names for backward compat
KCSE_SCALE = _KCSE_DEFAULT
CBE_SCALE  = _CBE_DEFAULT

LANGUAGE_SUBJECTS = {"english", "kiswahili", "english language",
                     "kiswahili language", "fasihi"}

def detect_curriculum(class_name: str) -> str:
    """
    Detect curriculum from class name.
    Uses word-boundary matching to avoid "grade 1" matching "grade 10".
    """
    import re
    name = (class_name or "").lower().strip()
    # Extract first word + number e.g. "grade 10" from "grade 10 east"
    m = re.match(r"^(pp\d+|grade\s+\d+|form\s+\d+)", name)
    base = m.group(1).strip() if m else name

    if base in ("pp1", "pp2"):
        return "ECDE"
    if base in ("grade 1", "grade 2", "grade 3"):
        return "Lower Primary"
    if base in ("grade 4", "grade 5", "grade 6"):
        return "Upper Primary"
    if base in ("grade 7", "grade 8", "grade 9",
                "grade 10", "grade 11", "grade 12"):
        return "CBC"
    return "8-4-4"


def grade_from_percentage(percentage: float, curriculum: str) -> tuple[str, int]:
    """Returns (grade_letter, points) using saved grading scale."""
    if curriculum in ("ECDE", "Lower Primary", "Upper Primary", "CBC"):
        scale = _get_cbe_scale()
        fallback = ("BE", 1)
    else:
        scale = _get_kcse_scale()
        fallback = ("E", 1)

    pct = round(float(percentage), 1)
    # Sort scale by min_s descending so highest matching wins
    sorted_scale = sorted(scale, key=lambda x: x[0], reverse=True)
    for min_s, max_s, grade, points in sorted_scale:
        if pct >= min_s:
            return grade, points
    return fallback


def subject_comment(grade: str, curriculum: str) -> str:
    """Auto-comment based on grade."""
    # CBC used for ECDE, Lower Primary, Upper Primary and CBC secondary
    is_cbc = curriculum in ("ECDE", "Lower Primary", "Upper Primary", "CBC")
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
        "EE2": "Exceeds expectations. Outstanding achievement.",
        "EE1": "Exceeds expectations. Outstanding achievement.",
        "ME2": "Meets expectations. Good and consistent performance.",
        "ME1": "Meets expectations. Good and consistent performance.",
        "AE2": "Approaches expectations. More effort needed to meet standards.",
        "AE1": "Approaches expectations. More effort needed to meet standards.",
        "BE2": "Below expectations. Requires significant improvement and support.",
        "BE1": "Below expectations. Requires significant improvement and support.",
        # Keep base grades for backward compat
        "EE": "Exceeds expectations. Outstanding achievement.",
        "ME": "Meets expectations. Good and consistent performance.",
        "AE": "Approaches expectations. More effort needed to meet standards.",
        "BE": "Below expectations. Requires significant improvement and support.",
    }
    comments = cbe_comments if is_cbc else kcse_comments
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
        "teacher_name": "",
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
               s.name AS subject_name, m.subject_id,
               m.class_id
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

    # Build subject_id -> teacher name map for this class
    teacher_map = {}
    if rows:
        class_id = rows[0]["class_id"]
        t_rows = query(
            """
            SELECT ta.subject_id, u.full_name
            FROM teacher_assignments ta
            JOIN users u ON ta.user_id = u.id
            WHERE ta.class_id = ?
            """,
            (class_id,),
        )
        for t in (t_rows or []):
            teacher_map[t["subject_id"]] = t["full_name"]

    subject_marks = []
    for r in rows:
        pct   = round(r["percentage"] or 0, 1)
        grade, pts = grade_from_percentage(pct, curriculum)
        subject_marks.append({
            "subject_name":  r["subject_name"],
            "raw_score":     r["raw_score"],
            "out_of":        r["out_of"],
            "percentage":    pct,
            "grade":         grade,
            "points":        pts,
            "comment":       subject_comment(grade, curriculum),
            "teacher_name":  teacher_map.get(r["subject_id"], ""),
        })

    # Select subjects for aggregate
    if curriculum == "8-4-4":
        selected = select_best_7(subject_marks)
    else:
        # CBC/ECDE/Primary — use all subjects
        selected = subject_marks

    if selected:
        mean  = round(sum(s["percentage"] for s in selected) / len(selected), 1)
        grade, points = grade_from_percentage(mean, curriculum)
    else:
        mean, grade, points = 0, "—", 0

    return {
        "subjects":     selected,
        "all_subjects": subject_marks,
        "selected":     selected,
        "mean":         mean,
        "grade":        grade,
        "points":       points,
        "band":         performance_band(mean),
        "curriculum":   curriculum,
        "is_844":       curriculum == "8-4-4",
        "is_cbc":       curriculum in ("ECDE", "Lower Primary",
                                        "Upper Primary", "CBC"),
    }


def compute_class_results(assessment_id: int, class_id: int) -> list[dict]:
    """
    Compute results for all students in a class, add position ranking.
    Bulk-fetches all marks in a single query for performance.
    Returns list sorted by mean descending with position added.
    """
    cls = query_one("SELECT name FROM classes WHERE id=?", (class_id,)) or {}
    class_name = cls.get("name", "")
    curriculum = detect_curriculum(class_name)

    students = query(
        "SELECT id, full_name, admission_number, gender "
        "FROM students WHERE class_id=? AND status='active' "
        "ORDER BY full_name",
        (class_id,),
    )
    if not students:
        return []

    # ── Bulk fetch: all marks for this class+assessment in ONE query ──
    all_marks = query(
        """
        SELECT m.student_id, m.subject_id, m.percentage,
               m.raw_score, m.out_of,
               s.name AS subject_name
        FROM marks_new m
        JOIN subjects s ON m.subject_id = s.id
        WHERE m.assessment_id = ? AND m.class_id = ?
        ORDER BY m.student_id, s.name
        """,
        (assessment_id, class_id),
    )

    # ── Bulk fetch: teacher assignments for this class ──
    teacher_map = {
        r["subject_id"]: r["full_name"]
        for r in (query(
            """
            SELECT ta.subject_id, u.full_name
            FROM teacher_assignments ta
            JOIN users u ON ta.user_id = u.id
            WHERE ta.class_id = ?
            """,
            (class_id,),
        ) or [])
    }

    # Group marks by student
    from collections import defaultdict
    marks_by_student = defaultdict(list)
    for m in all_marks:
        marks_by_student[m["student_id"]].append(m)

    results = []
    for s in students:
        sid = s["id"]
        rows = marks_by_student.get(sid, [])

        if not rows:
            continue

        subject_marks = []
        for r in rows:
            pct   = round(r["percentage"] or 0, 1)
            grade, pts = grade_from_percentage(pct, curriculum)
            subject_marks.append({
                "subject_name":  r["subject_name"],
                "raw_score":     r["raw_score"],
                "out_of":        r["out_of"],
                "percentage":    pct,
                "grade":         grade,
                "points":        pts,
                "comment":       subject_comment(grade, curriculum),
                "teacher_name":  teacher_map.get(r["subject_id"], ""),
            })

        if curriculum == "8-4-4":
            selected = select_best_7(subject_marks)
        else:
            selected = subject_marks

        if selected:
            mean  = round(sum(x["percentage"] for x in selected) / len(selected), 1)
            grade, points = grade_from_percentage(mean, curriculum)
        else:
            mean, grade, points = 0, "—", 0

        results.append({
            "student_id":       sid,
            "full_name":        s["full_name"],
            "admission_number": s["admission_number"],
            "gender":           s.get("gender", ""),
            "subjects":         selected,
            "all_subjects":     subject_marks,
            "selected":         selected,
            "mean":             mean,
            "grade":            grade,
            "points":           points,
            "band":             performance_band(mean),
            "curriculum":       curriculum,
            "is_844":           curriculum == "8-4-4",
            "is_cbc":           curriculum in ("ECDE", "Lower Primary",
                                               "Upper Primary", "CBC"),
        })

    # Rank by mean descending
    results.sort(key=lambda x: x["mean"], reverse=True)
    pos = 1
    for i, r in enumerate(results):
        if i > 0 and r["mean"] < results[i-1]["mean"]:
            pos = i + 1
        r["position"] = pos

    return results


def compute_student_result_combined(student_id: int,
                                     assessment_ids: list,
                                     class_name: str) -> dict:
    """
    Compute result for one student across multiple assessments.
    Each subject's score is the mean of their scores across all assessments.
    Returns the same structure as compute_student_result.
    """
    curriculum = detect_curriculum(class_name)

    # Fetch all marks for this student across the selected assessments
    placeholders = ",".join("?" * len(assessment_ids))
    rows = query(
        f"""
        SELECT m.subject_id, s.name AS subject_name,
               m.out_of, m.raw_score, m.percentage, m.class_id
        FROM marks_new m
        JOIN subjects s ON m.subject_id = s.id
        WHERE m.student_id = ? AND m.assessment_id IN ({placeholders})
        ORDER BY s.name
        """,
        (student_id, *assessment_ids),
    )

    if not rows:
        return {"subjects": [], "selected": [], "mean": 0,
                "grade": "—", "points": 0, "curriculum": curriculum}

    # Build teacher map in ONE query using IN clause
    teacher_map = {}
    class_ids_seen = list({r["class_id"] for r in rows if r["class_id"]})
    if class_ids_seen:
        placeholders = ",".join("?" * len(class_ids_seen))
        t_rows = query(
            f"""
            SELECT ta.subject_id, u.full_name
            FROM teacher_assignments ta
            JOIN users u ON ta.user_id = u.id
            WHERE ta.class_id IN ({placeholders})
            """,
            tuple(class_ids_seen),
        )
        for t in (t_rows or []):
            teacher_map[t["subject_id"]] = t["full_name"]

    # Group by subject and compute mean percentage across assessments
    from collections import defaultdict
    subj_data = defaultdict(lambda: {"name": "", "pcts": [],
                                      "raw_scores": [], "out_ofs": [],
                                      "subject_id": None})
    for r in rows:
        sid = r["subject_id"]
        subj_data[sid]["name"]       = r["subject_name"]
        subj_data[sid]["subject_id"] = sid
        subj_data[sid]["pcts"].append(r["percentage"] or 0)
        if r["raw_score"] is not None:
            subj_data[sid]["raw_scores"].append(r["raw_score"])
        if r["out_of"]:
            subj_data[sid]["out_ofs"].append(r["out_of"])

    subject_marks = []
    for sid, d in subj_data.items():
        pct   = round(sum(d["pcts"]) / len(d["pcts"]), 1)
        grade, pts = grade_from_percentage(pct, curriculum)
        # For display: show mean raw score / mean out_of if available
        raw   = round(sum(d["raw_scores"]) / len(d["raw_scores"]), 1)                 if d["raw_scores"] else None
        out   = round(sum(d["out_ofs"]) / len(d["out_ofs"]), 1)                 if d["out_ofs"] else 100
        subject_marks.append({
            "subject_name":  d["name"],
            "raw_score":     raw,
            "out_of":        out,
            "percentage":    pct,
            "grade":         grade,
            "points":        pts,
            "comment":       subject_comment(grade, curriculum),
            "teacher_name":  teacher_map.get(sid, ""),
            "asmt_count":    len(d["pcts"]),  # how many assessments contributed
        })

    subject_marks.sort(key=lambda x: x["subject_name"])

    if curriculum == "8-4-4":
        selected = select_best_7(subject_marks)
    else:
        selected = subject_marks

    if selected:
        mean  = round(sum(s["percentage"] for s in selected) / len(selected), 1)
        grade, points = grade_from_percentage(mean, curriculum)
    else:
        mean, grade, points = 0, "—", 0

    return {
        "subjects":     selected,
        "all_subjects": subject_marks,
        "selected":     selected,
        "mean":         mean,
        "grade":        grade,
        "points":       points,
        "band":         performance_band(mean),
        "curriculum":   curriculum,
        "is_844":       curriculum == "8-4-4",
        "is_cbc":       curriculum in ("ECDE", "Lower Primary",
                                        "Upper Primary", "CBC"),
    }


def compute_class_results_combined(assessment_ids: list,
                                    class_id: int) -> list:
    """
    Compute combined results for all students in a class
    across multiple assessments. Returns list sorted by mean desc with position.
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
        result = compute_student_result_combined(
            s["id"], assessment_ids, class_name)
        if not result["subjects"]:
            continue
        results.append({
            "student_id":       s["id"],
            "full_name":        s["full_name"],
            "admission_number": s["admission_number"],
            "gender":           s.get("gender", ""),
            **result,
        })

    results.sort(key=lambda x: x["mean"], reverse=True)
    pos = 1
    for i, r in enumerate(results):
        if i > 0 and r["mean"] < results[i-1]["mean"]:
            pos = i + 1
        r["position"] = pos

    return results
