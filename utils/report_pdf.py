from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, PageBreak, Image, HRFlowable, KeepTogether,
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from datetime import date
from pathlib import Path

from routes.settings import get_setting
from routes.terms import get_current_term
from utils.grading import compute_class_results, performance_band

ACCENT     = colors.HexColor("#4F46E5")
HEADER_BG  = colors.HexColor("#EEF2FF")
ALT_ROW    = colors.HexColor("#F9FAFB")
BORDER_C   = colors.HexColor("#E5E7EB")
TEXT_DARK  = colors.HexColor("#111827")
TEXT_MUTED = colors.HexColor("#6B7280")
SELECTED   = colors.HexColor("#FEF9C3")   # highlight best-7 subjects

# Descriptive labels for CBC/ECDE primary grades
CBC_DESCRIPTIVE = {
    "EE2": "Exceeds Expectations (EE2)",
    "EE1": "Exceeds Expectations (EE1)",
    "ME2": "Meets Expectations (ME2)",
    "ME1": "Meets Expectations (ME1)",
    "AE2": "Approaches Expectations (AE2)",
    "AE1": "Approaches Expectations (AE1)",
    "BE2": "Below Expectations (BE2)",
    "BE1": "Below Expectations (BE1)",
    # backward compat
    "EE": "Exceeds Expectations (EE)",
    "ME": "Meets Expectations (ME)",
    "AE": "Approaches Expectations (AE)",
    "BE": "Below Expectations (BE)",
}



def _page_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(TEXT_MUTED)
    canvas.drawCentredString(
        A4[0] / 2, 0.7 * cm,
        f"GradeVault  ·  Generated {date.today().strftime('%d %B %Y')}  ·  Page {doc.page}"
    )
    canvas.restoreState()


def _draw_signatures(canvas, doc, left_margin=1.5*cm, bottom=1.8*cm):
    """Draw signature lines at an absolute fixed position near the bottom of the page."""
    canvas.saveState()
    canvas.setFont("Helvetica", 9)
    canvas.setFillColor(TEXT_MUTED)
    page_w = A4[0]
    usable = page_w - left_margin * 2

    labels = [
        ("Class Teacher: _______________________", 0),
        ("Principal: _______________________",     0.38),
        ("Date: _______________",                  0.76),
    ]
    for text, frac in labels:
        x = left_margin + frac * usable
        canvas.drawString(x, bottom, text)
    canvas.restoreState()


def _page_footer_with_sig(canvas, doc):
    _page_footer(canvas, doc)
    _draw_signatures(canvas, doc)



def _student_header_table(result, class_label, term, s,
                              class_total=0):
    term_str = f"Term {term['term']}, {term['year']}" if term else ""
    pos_str  = (f"{result['position']} / {class_total}"
                if class_total else str(result['position']))
    data = [
        ["Name:", result["full_name"],
         "Adm. No.:", result["admission_number"]],
        ["Class:", class_label,
         "Term:", term_str],
        ["Gender:", result.get("gender") or "—",
         "Position:", pos_str],
    ]
    t = Table(data, colWidths=[2*cm, 6*cm, 2.5*cm, 5*cm])
    t.setStyle(TableStyle([
        ("FONTNAME",  (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE",  (0, 0), (-1, -1), 9),
        ("FONTNAME",  (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME",  (2, 0), (2, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, 0), (-1, -1), TEXT_DARK),
        ("TOPPADDING",(0, 0), (-1, -1), 3),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 3),
    ]))
    return t


def _marks_table(result, s):
    curriculum    = result["curriculum"]
    is_cbe        = curriculum == "CBE"
    all_subjects  = result.get("all_subjects", result["subjects"])
    selected_names = {sub["subject_name"] for sub in result["selected"]
                      if not sub.get("is_padding")}

    # Faded style for the asterisk on selected subjects
    faded = ParagraphStyle("faded", fontSize=8, fontName="Helvetica",
                            textColor=colors.HexColor("#9CA3AF"))

    is_primary = curriculum in ("ECDE", "Lower Primary", "Upper Primary")
    if is_primary:
        header = ["Subject", "Teacher", "Score", "Out of", "Mean", "Grade", "Comment"]
        col_w  = [3.0*cm, 2.6*cm, 1.2*cm, 1.2*cm, 1.4*cm, 3.8*cm, 3.4*cm]
    else:
        header = ["Subject", "Teacher", "Score", "Out of", "Mean", "Grade", "Comment"]
        col_w  = [3.6*cm, 2.8*cm, 1.2*cm, 1.2*cm, 1.4*cm, 1.5*cm, 4.5*cm]

    rows   = [header]

    for sub in all_subjects:
        is_selected = sub["subject_name"] in selected_names
        comment     = Paragraph(sub["comment"], s["comment"])

        # Subject name with faded * for selected
        if is_selected:
            subj_cell = Paragraph(
                f"{sub['subject_name']} "
                f"<font color='#9CA3AF'>*</font>",
                s["normal"])
        else:
            subj_cell = sub["subject_name"]

        grade_display = (
            CBC_DESCRIPTIVE.get(sub["grade"], sub["grade"])
            if is_primary else sub["grade"]
        )
        grade_cell = (Paragraph(grade_display, s["small"])
                      if is_primary else grade_display)
        teacher_cell = Paragraph(
            sub.get("teacher_name", "") or "—", s["small"])
        rows.append([
            subj_cell,
            teacher_cell,
            f"{sub['raw_score']:.0f}" if sub["raw_score"] is not None else "—",
            f"{sub['out_of']:.0f}",
            f"{sub['percentage']:.1f}%",
            grade_cell,
            comment,
        ])

    # Padding rows if fewer than 7 selected
    selected_count = len([s for s in result["selected"] if not s.get("is_padding")])
    for pad in result["selected"]:
        if pad.get("is_padding"):
            rows.append([
                Paragraph(f"{pad['subject_name']} "
                          f"<font color='#9CA3AF'>*</font>", s["normal"]),
                "—", "—", "—", "0.0%", pad["grade"], Paragraph(pad["comment"], s["comment"])
            ])

    # Totals row — sum of raw scores and out_of for displayed subjects
    displayed = [sub for sub in all_subjects if not sub.get("is_padding")]
    total_raw = sum(
        sub["raw_score"] for sub in displayed
        if sub.get("raw_score") is not None)
    total_out = sum(
        sub["out_of"] for sub in displayed
        if sub.get("out_of") is not None)
    rows.append([
        Paragraph("<b>Total</b>", s["normal"]),
        "",
        Paragraph(f"<b>{total_raw:.0f}</b>", s["normal"]),
        Paragraph(f"<b>{total_out:.0f}</b>", s["normal"]),
        "", "", ""
    ])

    # Aggregate (mean) row
    if result.get("is_844"):
        agg_label = "Mean (Best 7)"
    elif is_primary:
        agg_label = "Overall Mean"
    else:
        agg_label = "Mean (All subjects)"

    agg_grade = (CBC_DESCRIPTIVE.get(result["grade"], result["grade"])
                 if result.get("is_cbc") else result["grade"])
    agg_grade_cell = (Paragraph(agg_grade, s["small"])
                      if is_primary else agg_grade)
    rows.append([
        Paragraph(f"<b>{agg_label}</b>", s["normal"]),
        "", "", "", f"{result['mean']:.1f}",
        agg_grade_cell, ""
    ])

    t = Table(rows, colWidths=col_w, repeatRows=1)
    style = [
        ("BACKGROUND",    (0, 0), (-1, 0), HEADER_BG),
        ("TEXTCOLOR",     (0, 0), (-1, 0), ACCENT),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 4),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
        ("FONTNAME",      (0, 1), (-1, -1), "Helvetica"),
        ("GRID",          (0, 0), (-1, -1), 0.4, BORDER_C),
        ("ALIGN",         (2, 0), (5, -1), "CENTER"),
        ("RIGHTPADDING",  (4, 0), (4, -1), 8),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND",    (0, -2), (-1, -1), HEADER_BG),
        ("FONTNAME",      (0, -2), (-1, -1), "Helvetica-Bold"),
    ]
    # Alternate row shading — exclude the last 2 summary rows
    for i in range(1, len(rows) - 2):
        if i % 2 == 0:
            style.append(("BACKGROUND", (0, i), (-1, i), ALT_ROW))

    t.setStyle(TableStyle(style))
    return t


def _comment_block(label, comment_text, s):
    if not comment_text:
        return None
    data = [[Paragraph(f"<b>{label}:</b>", s["bold"]),
             Paragraph(comment_text, s["comment"])]]
    t = Table(data, colWidths=[3.5*cm, 12.5*cm])
    t.setStyle(TableStyle([
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("LINEABOVE",     (0, 0), (-1,  0), 0.3, BORDER_C),
        ("LINEBELOW",     (0, 0), (-1, -1), 0.3, BORDER_C),
    ]))
    return t


def generate_report_cards(output_path: str,
                           assessment_id: int,
                           class_id: int,
                           comments: dict) -> tuple[int, str]:
    """
    Generate PDF report cards for all students in a class (single assessment).
    Returns (student_count, output_path).
    """
    from db.connection import query_one
    cls = query_one(
        "SELECT c.name, c.stream FROM classes c WHERE c.id=?", (class_id,)
    ) or {}
    stream      = cls.get("stream") or ""
    class_label = f"{cls.get('name', '')} {stream}".strip()
    term        = get_current_term()

    results = compute_class_results(assessment_id, class_id)
    if not results:
        return 0, "No marks found for this class and assessment."

    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=1.4*cm, rightMargin=1.4*cm,
        topMargin=1.2*cm, bottomMargin=1.4*cm,
    )
    s     = _styles_compact()
    story = []

    for idx, result in enumerate(results):
        band = result["band"]
        principal_comment = comments.get(f"principal_{band}", "")
        teacher_comment   = comments.get(f"teacher_{band}", "")

        card_elements = []

        # ── Header ────────────────────────────────────────────────
        _school_header_compact(card_elements, s)
        card_elements.append(HRFlowable(
            width="100%", thickness=0.5, color=ACCENT,
            spaceBefore=1, spaceAfter=1))

        term_str = f"Term {term['term']}, {term['year']}" if term else ""
        card_elements.append(Paragraph(
            f"STUDENT REPORT CARD — {term_str}", s["heading"]))
        card_elements.append(Spacer(1, 0.08*cm))

        card_elements.append(
            _student_header_table(result, class_label, term, s,
                                   class_total=len(results)))
        card_elements.append(Spacer(1, 0.08*cm))
        card_elements.append(_marks_table(result, s))

        if result.get("is_844"):
            card_elements.append(Paragraph(
                "* Subjects marked with * are included in the mean grade calculation (Best 7 rule).",
                s["small"]))
        elif result.get("is_cbc"):
            card_elements.append(Paragraph(
                "EE=Exceeds  ME=Meets  AE=Approaches  BE=Below",
                s["small"]))

        card_elements.append(Spacer(1, 0.08*cm))

        # ── Comments ──────────────────────────────────────────────
        ct = _comment_block("Class Teacher", teacher_comment, s)
        if ct:
            card_elements.append(ct)
        pc = _comment_block("Principal", principal_comment, s)
        if pc:
            card_elements.append(pc)

        # ── Chart ─────────────────────────────────────────────────
        chart = _single_exam_chart(result, assessment_id, class_id)
        if chart:
            card_elements.append(Spacer(1, 0.08*cm))
            chart_lbl_style = ParagraphStyle(
                "cl", fontSize=7, fontName="Helvetica-Bold",
                textColor=ACCENT)
            card_elements.append(
                Paragraph("Performance by Subject", chart_lbl_style))
            card_elements.append(chart)

        story.append(KeepTogether(card_elements))
        if idx < len(results) - 1:
            story.append(PageBreak())

    doc.build(story, onFirstPage=_page_footer_with_sig, onLaterPages=_page_footer_with_sig)
    return len(results), output_path


def generate_all_classes_report_cards(output_path: str,
                                       assessment_id: int,
                                       class_ids: list,
                                       comments: dict) -> tuple[int, str]:
    """
    Generate a single merged PDF of report cards for multiple classes.
    Each student gets one page. Returns (total_student_count, output_path).
    """
    from db.connection import query_one, query

    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=1.4*cm, rightMargin=1.4*cm,
        topMargin=1.2*cm, bottomMargin=1.4*cm,
    )
    s     = _styles_compact()
    story = []
    total = 0
    term  = get_current_term()

    # Bulk-fetch all class names
    _ph  = ",".join("?" * len(class_ids))
    _cls = {r["id"]: r for r in query(
        f"SELECT id, name, stream FROM classes WHERE id IN ({_ph})",
        tuple(class_ids)
    )} if class_ids else {}

    for class_idx, class_id in enumerate(class_ids):
        cls = _cls.get(class_id) or {}
        stream      = cls.get("stream") or ""
        class_label = f"{cls.get('name', '')} {stream}".strip()

        results = compute_class_results(assessment_id, class_id)
        if not results:
            continue

        for idx, result in enumerate(results):
            band = result["band"]
            principal_comment = comments.get(f"principal_{band}", "")
            teacher_comment   = comments.get(f"teacher_{band}", "")

            card_elements = []

            # ── Header (same compact style as single-class reports) ────
            _school_header_compact(card_elements, s)
            card_elements.append(HRFlowable(
                width="100%", thickness=0.5, color=ACCENT,
                spaceBefore=1, spaceAfter=1))

            term_str = f"Term {term['term']}, {term['year']}" if term else ""
            card_elements.append(Paragraph(
                f"STUDENT REPORT CARD — {term_str}", s["heading"]))
            card_elements.append(Spacer(1, 0.08*cm))

            card_elements.append(
                _student_header_table(result, class_label, term, s,
                                       class_total=len(results)))
            card_elements.append(Spacer(1, 0.08*cm))
            card_elements.append(_marks_table(result, s))

            if result.get("is_844"):
                card_elements.append(Paragraph("* Best 7 rule applied.", s["small"]))
            elif result.get("is_cbc"):
                card_elements.append(Paragraph(
                    "EE=Exceeds  ME=Meets  AE=Approaches  BE=Below", s["small"]))

            card_elements.append(Spacer(1, 0.08*cm))

            ct = _comment_block("Class Teacher", teacher_comment, s)
            if ct:
                card_elements.append(ct)
            pc = _comment_block("Principal", principal_comment, s)
            if pc:
                card_elements.append(pc)

            # ── Chart ─────────────────────────────────────────────────
            chart = _single_exam_chart(result, assessment_id, class_id)
            if chart:
                card_elements.append(Spacer(1, 0.08*cm))
                chart_lbl_style = ParagraphStyle(
                    "cl", fontSize=7, fontName="Helvetica-Bold",
                    textColor=ACCENT)
                card_elements.append(
                    Paragraph("Performance by Subject", chart_lbl_style))
                card_elements.append(chart)

            story.append(KeepTogether(card_elements))

            is_last_student = (idx == len(results) - 1)
            is_last_class   = (class_idx == len(class_ids) - 1)
            if not (is_last_student and is_last_class):
                story.append(PageBreak())

        total += len(results)

    if not story:
        return 0, "No marks found for any class."

    doc.build(story, onFirstPage=_page_footer_with_sig, onLaterPages=_page_footer_with_sig)
    return total, output_path


# Palette for line chart — distinct colours for up to 8 subjects
_LINE_COLOURS = [
    "#4F46E5",  # indigo
    "#EF4444",  # red
    "#10B981",  # green
    "#F59E0B",  # amber
    "#8B5CF6",  # purple
    "#EC4899",  # pink
    "#06B6D4",  # cyan
    "#F97316",  # orange
]


def _abbr_subject(name: str) -> str:
    """Abbreviate a subject name for chart labels."""
    KNOWN = {
        "mathematics": "Maths", "english": "Eng",
        "kiswahili": "Kisw", "biology": "Bio",
        "chemistry": "Chem", "physics": "Phys",
        "history": "Hist", "geography": "Geo",
        "christian religious education": "CRE",
        "islamic religious education": "IRE",
        "hindu religious education": "HRE",
        "computer studies": "Comp",
        "business studies": "BST",
        "agriculture": "Agri", "home science": "HSci",
        "art and design": "Art", "music": "Music",
        "physical education": "PE",
        "community service learning": "CSL",
        "creative arts": "C.Arts", "social studies": "S.Std",
        "integrated science": "I.Sci", "english language": "Eng",
        "kiswahili language": "Kisw",
    }
    lo = name.lower().strip()
    if lo in KNOWN:
        return KNOWN[lo]
    words = name.split()
    if len(words) >= 3:
        return "".join(w[0].upper() for w in words[:4])
    if len(words) == 2:
        return words[0][:5].title()
    return name[:6]


def _per_exam_chart(student_id: int, assessment_ids: list,
                    assessment_names: list, class_id: int, s) -> object:
    """
    Line chart per student on the combined report card.
    X axis  = subjects (abbreviated, e.g. Maths, CRE, Bio)
    Y axis  = marks 0-100
    Lines   = one coloured line per assessment
              (red = exam 1, yellow/amber = exam 2, green = exam 3 …)
    Returns a ReportLab Drawing or None if no data.
    """
    from reportlab.graphics.shapes import Drawing, Line, Circle, String, Rect
    from reportlab.lib import colors as rcolors
    from db.connection import query as _q

    # Assessment line colours — distinct, printable
    EXAM_COLOURS = [
        "#EF4444",  # red
        "#F59E0B",  # amber
        "#10B981",  # green
        "#3B82F6",  # blue
        "#8B5CF6",  # purple
        "#EC4899",  # pink
    ]

    # ── Fetch scores: for each assessment, get this student's subject scores ──
    # Structure: subject_id → {asmt_idx: pct, "name": str}
    subj_data = {}   # subject_id → {"name": str, scores: [pct|None, ...]}

    for ai, asmt_id in enumerate(assessment_ids):
        rows = _q("""
            SELECT m.subject_id, s.name AS subject_name,
                   ROUND(m.percentage, 1) AS pct
            FROM marks_new m
            JOIN subjects s ON m.subject_id = s.id
            WHERE m.student_id = ? AND m.assessment_id = ?
        """, (student_id, asmt_id))
        for r in (rows or []):
            sid = r["subject_id"]
            if sid not in subj_data:
                subj_data[sid] = {
                    "name": r["subject_name"],
                    "scores": [None] * len(assessment_ids)
                }
            subj_data[sid]["scores"][ai] = r["pct"]

    if not subj_data:
        return None

    # Sort subjects alphabetically, keep only those with ≥1 score
    subjects = sorted(
        [(sid, d["name"], d["scores"]) for sid, d in subj_data.items()
         if any(v is not None for v in d["scores"])],
        key=lambda x: x[1]
    )
    if not subjects:
        return None

    n_subjs = len(subjects)
    n_asmts = len(assessment_ids)

    # ── Layout — always use full usable page width ───────────────
    PAGE_PX  = 510  # ~18.2cm usable width at 1.4cm margins
    col_w    = max(28, min(60, (PAGE_PX - 50) // max(n_subjs, 1)))
    chart_w  = PAGE_PX  # always stretch to full width
    legend_h = max(11, ((n_asmts - 1) // 4 + 1) * 12)
    plot_h   = 72          # compact for single-page combined card
    pad_l    = 34
    pad_r    = 10
    pad_b    = 24          # subject labels
    pad_t    = 8
    chart_h  = pad_t + plot_h + pad_b + legend_h + 4

    grey  = rcolors.HexColor("#E5E7EB")
    muted = rcolors.HexColor("#9CA3AF")
    dark  = rcolors.HexColor("#374151")

    d = Drawing(chart_w, chart_h)
    # y=0 of plot in drawing coords (above legend + x labels)
    origin_y = legend_h + pad_b

    # ── Y-axis: gridlines + labels at 0, 25, 50, 75, 100 ─────────
    for pct in (0, 25, 50, 75, 100):
        y = origin_y + int(pct / 100 * plot_h)
        d.add(Line(pad_l, y, chart_w - pad_r, y,
                   strokeColor=grey, strokeWidth=0.4))
        d.add(String(pad_l - 3, y - 3, str(pct),
                     fontSize=6, fillColor=muted, textAnchor="end"))

    # ── X-axis: subject labels ────────────────────────────────────
    plot_w = chart_w - pad_l - pad_r  # actual drawable plot area

    def x_of(si):
        """Centre X for subject slot si — evenly distributed."""
        if n_subjs == 1:
            return pad_l + plot_w // 2
        return pad_l + int((si + 0.5) * plot_w / n_subjs)

    for si, (sid, sname, _) in enumerate(subjects):
        x = x_of(si)
        abbr = _abbr_subject(sname)
        d.add(String(x, origin_y - 16, abbr,
                     fontSize=6.5, fillColor=dark, textAnchor="middle"))
        # Vertical dotted tick
        d.add(Line(x, origin_y, x, origin_y - 4,
                   strokeColor=muted, strokeWidth=0.5))

    # ── Plot one line per assessment ──────────────────────────────
    for ai, (asmt_id, asmt_name) in enumerate(
            zip(assessment_ids, assessment_names)):
        col = rcolors.HexColor(EXAM_COLOURS[ai % len(EXAM_COLOURS)])
        pts = []  # (x, y, pct) for dots + values

        for si, (sid, sname, scores) in enumerate(subjects):
            pct = scores[ai]
            if pct is not None:
                x = x_of(si)
                y = origin_y + int(pct / 100 * plot_h)
                pts.append((x, y, pct))
            else:
                pts.append(None)

        # Draw connecting line (skip None gaps)
        prev = None
        for pt in pts:
            if pt and prev:
                d.add(Line(prev[0], prev[1], pt[0], pt[1],
                           strokeColor=col, strokeWidth=1.6))
            if pt:
                prev = pt
            else:
                prev = None

        # Draw dots and value labels
        for pt in pts:
            if pt is None:
                continue
            x, y, pct = pt
            d.add(Circle(x, y, 2.8,
                         fillColor=col,
                         strokeColor=rcolors.white,
                         strokeWidth=0.6))
            d.add(String(x, y + 4.5, f"{pct:.0f}",
                         fontSize=5.5, fillColor=col,
                         textAnchor="middle"))

    # ── Legend: one entry per assessment ─────────────────────────
    cols_leg = min(4, n_asmts)
    cell_w   = chart_w // max(cols_leg, 1)
    for ai, asmt_name in enumerate(assessment_names):
        col   = rcolors.HexColor(EXAM_COLOURS[ai % len(EXAM_COLOURS)])
        col_i = ai % cols_leg
        row_i = ai // cols_leg
        lx = col_i * cell_w + 4
        ly = legend_h - 11 - row_i * 13
        # Colour dash swatch
        d.add(Line(lx, ly + 3, lx + 14, ly + 3,
                   strokeColor=col, strokeWidth=2.5))
        d.add(Circle(lx + 7, ly + 3, 2.5,
                     fillColor=col,
                     strokeColor=rcolors.white,
                     strokeWidth=0.5))
        # Assessment name
        short = asmt_name[:18] + "…" if len(asmt_name) > 19 else asmt_name
        d.add(String(lx + 18, ly, short,
                     fontSize=6.5, fillColor=dark, textAnchor="start"))

    return d


def _single_exam_chart(result: dict, assessment_id: int, class_id: int) -> object:
    """
    Line chart for a single-assessment report card.
    Two lines: student score (indigo) and class mean (grey) across subjects.
    Y-axis = marks (percentage), X-axis = subjects.
    Full page width, same style as the combined card chart.
    Returns a ReportLab Drawing or None if no data.
    """
    from reportlab.graphics.shapes import Drawing, Line, Circle, String
    from reportlab.lib import colors as rcolors
    from db.connection import query as _q

    subjects = result.get("all_subjects", result.get("subjects", []))
    if not subjects:
        return None
    subjects = [s for s in subjects
                if s.get("raw_score") is not None and s.get("out_of")]
    if not subjects:
        return None

    # Fetch class mean per subject for this assessment
    rows = _q("""
        SELECT subject_id, ROUND(AVG(percentage), 1) AS mean_pct
        FROM marks_new
        WHERE assessment_id = ? AND class_id = ?
        GROUP BY subject_id
    """, (assessment_id, class_id))
    class_means = {r["subject_id"]: r["mean_pct"] for r in (rows or [])}

    # Layout — identical proportions to _per_exam_chart
    PAGE_PX  = 510
    n_subjs  = len(subjects)
    pad_l    = 34
    pad_r    = 10
    pad_b    = 24   # subject labels
    pad_t    = 8
    plot_h   = 80
    legend_h = 14
    plot_w   = PAGE_PX - pad_l - pad_r
    chart_h  = pad_t + plot_h + pad_b + legend_h + 4

    grey   = rcolors.HexColor("#E5E7EB")
    muted  = rcolors.HexColor("#9CA3AF")
    dark   = rcolors.HexColor("#374151")
    blue   = rcolors.HexColor("#4F46E5")
    ltgrey = rcolors.HexColor("#9CA3AF")

    d        = Drawing(PAGE_PX, chart_h)
    origin_y = legend_h + pad_b

    # Y-axis gridlines + labels at 0, 25, 50, 75, 100
    for pct in (0, 25, 50, 75, 100):
        y = origin_y + int(pct / 100 * plot_h)
        d.add(Line(pad_l, y, PAGE_PX - pad_r, y,
                   strokeColor=grey, strokeWidth=0.4))
        d.add(String(pad_l - 3, y - 3, str(pct),
                     fontSize=6, fillColor=muted, textAnchor="end"))

    def x_of(si):
        if n_subjs == 1:
            return pad_l + plot_w // 2
        return pad_l + int((si + 0.5) * plot_w / n_subjs)

    # X-axis subject labels
    for si, sub in enumerate(subjects):
        x    = x_of(si)
        abbr = _abbr_subject(sub["subject_name"])
        d.add(String(x, origin_y - 16, abbr,
                     fontSize=6.5, fillColor=dark, textAnchor="middle"))
        d.add(Line(x, origin_y, x, origin_y - 4,
                   strokeColor=muted, strokeWidth=0.5))

    # ── Student line (indigo) ──────────────────────────────────
    s_pts = []
    for si, sub in enumerate(subjects):
        pct = sub["percentage"]
        s_pts.append((x_of(si), origin_y + int(pct / 100 * plot_h), pct))

    prev = None
    for pt in s_pts:
        if prev:
            d.add(Line(prev[0], prev[1], pt[0], pt[1],
                       strokeColor=blue, strokeWidth=1.6))
        prev = pt
    for x, y, pct in s_pts:
        d.add(Circle(x, y, 2.8,
                     fillColor=blue,
                     strokeColor=rcolors.white,
                     strokeWidth=0.6))
        d.add(String(x, y + 4.5, f"{pct:.0f}",
                     fontSize=5.5, fillColor=blue, textAnchor="middle"))

    # ── Class mean line (grey) ─────────────────────────────────
    c_pts = []
    for si, sub in enumerate(subjects):
        sid = sub.get("subject_id")
        pct = class_means.get(sid, sub["percentage"])
        c_pts.append((x_of(si), origin_y + int(pct / 100 * plot_h), pct))

    prev = None
    for pt in c_pts:
        if prev:
            d.add(Line(prev[0], prev[1], pt[0], pt[1],
                       strokeColor=ltgrey, strokeWidth=1.2,
                       strokeDashArray=[3, 2]))
        prev = pt
    for x, y, pct in c_pts:
        d.add(Circle(x, y, 2.2,
                     fillColor=ltgrey,
                     strokeColor=rcolors.white,
                     strokeWidth=0.5))

    # ── Legend ────────────────────────────────────────────────
    lx, ly = pad_l, 2
    d.add(Line(lx, ly + 3, lx + 14, ly + 3,
               strokeColor=blue, strokeWidth=2.5))
    d.add(Circle(lx + 7, ly + 3, 2.5,
                 fillColor=blue, strokeColor=rcolors.white, strokeWidth=0.5))
    d.add(String(lx + 18, ly, "Student",
                 fontSize=6.5, fillColor=dark, textAnchor="start"))

    d.add(Line(lx + 70, ly + 3, lx + 84, ly + 3,
               strokeColor=ltgrey, strokeWidth=2.0,
               strokeDashArray=[3, 2]))
    d.add(Circle(lx + 77, ly + 3, 2.2,
                 fillColor=ltgrey, strokeColor=rcolors.white, strokeWidth=0.5))
    d.add(String(lx + 88, ly, "Class Mean",
                 fontSize=6.5, fillColor=dark, textAnchor="start"))

    return d


def _styles_compact():
    """Reduced font sizes for combined report to fit on one page."""
    return {
        "school":   ParagraphStyle("school_c",  fontSize=13, fontName="Helvetica-Bold",
                                    textColor=ACCENT, alignment=TA_CENTER),
        "motto":    ParagraphStyle("motto_c",   fontSize=8,  fontName="Helvetica-Oblique",
                                    textColor=TEXT_MUTED, alignment=TA_CENTER),
        "heading":  ParagraphStyle("heading_c", fontSize=9,  fontName="Helvetica-Bold",
                                    textColor=TEXT_DARK, alignment=TA_CENTER),
        "normal":   ParagraphStyle("normal_c",  fontSize=8,  fontName="Helvetica",
                                    textColor=TEXT_DARK),
        "small":    ParagraphStyle("small_c",   fontSize=7,  fontName="Helvetica",
                                    textColor=TEXT_MUTED),
        "comment":  ParagraphStyle("comment_c", fontSize=7.5,fontName="Helvetica-Oblique",
                                    textColor=TEXT_DARK, leading=10),
        "bold":     ParagraphStyle("bold_c",    fontSize=8,  fontName="Helvetica-Bold",
                                    textColor=TEXT_DARK),
    }


def _school_header_compact(story, s):
    """Full-width school header for combined report."""
    logo_path      = get_setting("school_logo",    "")
    school_name    = get_setting("school_name",    "School")
    school_motto   = get_setting("school_motto",   "")
    school_contact = get_setting("school_contact", "")

    if logo_path and Path(logo_path).exists():
        try:
            img = Image(logo_path)
            ratio = img.imageWidth / img.imageHeight
            # Full page width, capped at 3cm tall
            w = 17*cm
            h = w / ratio
            if h > 3*cm:
                h = 3*cm
                w = h * ratio
            img.drawWidth, img.drawHeight = w, h
            img.hAlign = "CENTER"
            story.append(img)
            return
        except Exception:
            pass
    story.append(Paragraph(school_name, s["school"]))
    if school_motto:
        story.append(Paragraph(school_motto, s["small"]))


def generate_combined_report_cards(output_path: str,
                                    assessment_ids: list,
                                    assessment_names: list,
                                    class_id: int,
                                    comments: dict) -> tuple[int, str]:
    """
    Generate report cards where each subject mark is the mean
    across multiple assessments (e.g. Opener + Midterm + Endterm).
    assessment_names is used in the report header.
    """
    from db.connection import query_one
    from utils.grading import compute_class_results_combined

    cls = query_one(
        "SELECT c.name, c.stream FROM classes c WHERE c.id=?", (class_id,)
    ) or {}
    stream      = cls.get("stream") or ""
    class_label = f"{cls.get('name', '')} {stream}".strip()
    term        = get_current_term()

    results = compute_class_results_combined(assessment_ids, class_id)
    if not results:
        return 0, "No marks found for this class and assessments."

    combined_label = " + ".join(assessment_names)

    # Tighter margins for combined — need to fit marks + chart + comments
    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=1.4*cm, rightMargin=1.4*cm,
        topMargin=1.2*cm, bottomMargin=1.4*cm,
    )
    s     = _styles_compact()   # compact font sizes
    story = []

    for idx, result in enumerate(results):
        band = result["band"]
        principal_comment = comments.get(f"principal_{band}", "")
        teacher_comment   = comments.get(f"teacher_{band}", "")

        card_elements = []

        # ── Compact header ─────────────────────────────────────
        _school_header_compact(card_elements, s)
        card_elements.append(HRFlowable(
            width="100%", thickness=0.5, color=ACCENT,
            spaceBefore=1, spaceAfter=1))

        term_str = f"Term {term['term']}, {term['year']}" if term else ""
        card_elements.append(Paragraph(
            f"STUDENT REPORT CARD — {term_str}  ·  Combined: {combined_label}",
            s["heading"]))
        card_elements.append(Spacer(1, 0.08*cm))

        card_elements.append(
            _student_header_table(result, class_label, term, s,
                                   class_total=len(results)))
        card_elements.append(Spacer(1, 0.08*cm))
        card_elements.append(_marks_table(result, s))

        if result.get("is_844"):
            card_elements.append(Paragraph(
                "* Best 7: means across all selected assessments.",
                s["small"]))
        elif result.get("is_cbc"):
            card_elements.append(Paragraph(
                "EE=Exceeds  ME=Meets  AE=Approaches  BE=Below  "
                "(means across all assessments)",
                s["small"]))

        card_elements.append(Spacer(1, 0.08*cm))

        # ── Chart first — above comments ──────────────────────
        chart = _per_exam_chart(
            result["student_id"], assessment_ids,
            assessment_names, class_id, s)
        if chart:
            chart_lbl_style = ParagraphStyle(
                "cl", fontSize=7, fontName="Helvetica-Bold",
                textColor=ACCENT)
            card_elements.append(
                Paragraph("Performance across assessments", chart_lbl_style))
            card_elements.append(chart)
            card_elements.append(Spacer(1, 0.08*cm))

        # ── Comments — one row each ────────────────────────────
        if teacher_comment:
            ct_data = [[
                Paragraph("<b>Class Teacher:</b>", s["bold"]),
                Paragraph(teacher_comment, s["comment"]),
            ]]
            ct_tbl = Table(ct_data, colWidths=[3.5*cm, 12.5*cm])
            ct_tbl.setStyle(TableStyle([
                ("FONTSIZE",      (0,0), (-1,-1), 8),
                ("TOPPADDING",    (0,0), (-1,-1), 8),
                ("BOTTOMPADDING", (0,0), (-1,-1), 8),
                ("VALIGN",        (0,0), (-1,-1), "TOP"),
                ("LINEABOVE",     (0,0), (-1,0),  0.3, BORDER_C),
                ("LINEBELOW",     (0,0), (-1,-1), 0.3, BORDER_C),
            ]))
            card_elements.append(ct_tbl)

        if principal_comment:
            pc_data = [[
                Paragraph("<b>Principal:</b>", s["bold"]),
                Paragraph(principal_comment, s["comment"]),
            ]]
            pc_tbl = Table(pc_data, colWidths=[3.5*cm, 12.5*cm])
            pc_tbl.setStyle(TableStyle([
                ("FONTSIZE",      (0,0), (-1,-1), 8),
                ("TOPPADDING",    (0,0), (-1,-1), 8),
                ("BOTTOMPADDING", (0,0), (-1,-1), 8),
                ("VALIGN",        (0,0), (-1,-1), "TOP"),
                ("LINEABOVE",     (0,0), (-1,0),  0.3, BORDER_C),
                ("LINEBELOW",     (0,0), (-1,-1), 0.3, BORDER_C),
            ]))
            card_elements.append(pc_tbl)

        story.append(KeepTogether(card_elements))
        if idx < len(results) - 1:
            story.append(PageBreak())

    doc.build(story, onFirstPage=_page_footer_with_sig, onLaterPages=_page_footer_with_sig)
    return len(results), output_path