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


def _styles():
    return {
        "school":   ParagraphStyle("school",   fontSize=16, fontName="Helvetica-Bold",
                                    textColor=ACCENT, alignment=TA_CENTER),
        "motto":    ParagraphStyle("motto",    fontSize=9,  fontName="Helvetica-Oblique",
                                    textColor=TEXT_MUTED, alignment=TA_CENTER),
        "heading":  ParagraphStyle("heading",  fontSize=11, fontName="Helvetica-Bold",
                                    textColor=TEXT_DARK, alignment=TA_CENTER),
        "normal":   ParagraphStyle("normal",   fontSize=9,  fontName="Helvetica",
                                    textColor=TEXT_DARK),
        "small":    ParagraphStyle("small",    fontSize=8,  fontName="Helvetica",
                                    textColor=TEXT_MUTED),
        "comment":  ParagraphStyle("comment",  fontSize=8,  fontName="Helvetica-Oblique",
                                    textColor=TEXT_DARK, leading=11),
        "bold":     ParagraphStyle("bold",     fontSize=9,  fontName="Helvetica-Bold",
                                    textColor=TEXT_DARK),
    }


def _page_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(TEXT_MUTED)
    canvas.drawCentredString(
        A4[0] / 2, 1.2 * cm,
        f"GradeVault  ·  Generated {date.today().strftime('%d %B %Y')}  ·  Page {doc.page}"
    )
    canvas.restoreState()


def _school_header(story, s):
    logo_path      = get_setting("school_logo",    "")
    school_name    = get_setting("school_name",    "School")
    school_motto   = get_setting("school_motto",   "")
    school_contact = get_setting("school_contact", "")

    if logo_path and Path(logo_path).exists():
        try:
            img = Image(logo_path)
            max_h, max_w = 2.8*cm, 14*cm
            ratio = img.imageWidth / img.imageHeight
            h = max_h
            w = h * ratio
            if w > max_w:
                w = max_w; h = w / ratio
            img.drawWidth, img.drawHeight = w, h
            img.hAlign = "CENTER"
            story.append(img)
            story.append(Spacer(1, 0.1*cm))
            return
        except Exception:
            pass

    story.append(Paragraph(school_name, s["school"]))
    if school_motto:
        story.append(Paragraph(school_motto, s["small"]))
    if school_contact:
        story.append(Paragraph(school_contact, s["small"]))


def _student_header_table(result, class_label, term, s):
    term_str = f"Term {term['term']}, {term['year']}" if term else ""
    data = [
        ["Name:", result["full_name"],
         "Adm. No.:", result["admission_number"]],
        ["Class:", class_label,
         "Term:", term_str],
        ["Gender:", result.get("gender") or "—",
         "Position:", f"{result['position']} in class"],
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
    selected_names = {sub["subject_name"] for sub in result["selected"]}
    curriculum     = result["curriculum"]
    is_cbe         = curriculum == "CBE"

    header = ["Subject", "Score", "Out of", "%", "Grade", "Comment"]
    col_w  = [4.5*cm, 1.6*cm, 1.6*cm, 1.6*cm, 1.4*cm, 5.5*cm]

    rows = [header]
    for sub in result["subjects"]:
        is_selected = sub["subject_name"] in selected_names
        comment = Paragraph(sub["comment"], s["comment"])
        rows.append([
            sub["subject_name"] + (" *" if is_selected else ""),
            f"{sub['raw_score']:.0f}" if sub["raw_score"] is not None else "—",
            f"{sub['out_of']:.0f}",
            f"{sub['percentage']:.1f}%",
            sub["grade"],
            comment,
        ])

    # Aggregate row
    rows.append([
        Paragraph("<b>Aggregate (Best 7)</b>" if not is_cbe
                  else "<b>Aggregate (All subjects)</b>",
                  s["normal"]),
        "", "", f"{result['mean']:.1f}%",
        result["grade"], ""
    ])

    t = Table(rows, colWidths=col_w, repeatRows=1)

    style = [
        # Header
        ("BACKGROUND",    (0, 0), (-1, 0), HEADER_BG),
        ("TEXTCOLOR",     (0, 0), (-1, 0), ACCENT),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("FONTNAME",      (0, 1), (-1, -1), "Helvetica"),
        ("GRID",          (0, 0), (-1, -1), 0.4, BORDER_C),
        ("ALIGN",         (1, 0), (4, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        # Aggregate row
        ("BACKGROUND",    (0, -1), (-1, -1), HEADER_BG),
        ("FONTNAME",      (0, -1), (-1, -1), "Helvetica-Bold"),
    ]

    # Alternating rows + highlight selected subjects
    for i, row in enumerate(rows[1:-1], start=1):
        subj_name = result["subjects"][i-1]["subject_name"]
        if subj_name in selected_names:
            style.append(("BACKGROUND", (0, i), (-1, i), SELECTED))
        elif i % 2 == 0:
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
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW",     (0, 0), (-1, -1), 0.3, BORDER_C),
    ]))
    return t


def generate_report_cards(output_path: str,
                           assessment_id: int,
                           class_id: int,
                           comments: dict) -> tuple[int, str]:
    """
    Generate PDF report cards for all students in a class.
    comments = {
      'principal_excellent': str,
      'principal_good': str,
      'principal_average': str,
      'principal_below_average': str,
      'teacher_excellent': str,
      'teacher_good': str,
      'teacher_average': str,
      'teacher_below_average': str,
    }
    Returns (student_count, output_path)
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
        leftMargin=1.8*cm, rightMargin=1.8*cm,
        topMargin=1.8*cm, bottomMargin=2*cm,
    )
    s     = _styles()
    story = []

    for idx, result in enumerate(results):
        band = result["band"]

        principal_comment = comments.get(f"principal_{band}", "")
        teacher_comment   = comments.get(f"teacher_{band}", "")

        card_elements = []

        # School header
        _school_header(card_elements, s)
        card_elements.append(Spacer(1, 0.2*cm))
        card_elements.append(HRFlowable(
            width="100%", thickness=0.5, color=ACCENT, spaceAfter=4))

        # Report card title
        term_str = f"Term {term['term']}, {term['year']}" if term else ""
        card_elements.append(Paragraph(
            f"STUDENT REPORT CARD — {term_str}", s["heading"]))
        card_elements.append(Spacer(1, 0.3*cm))

        # Student info
        card_elements.append(
            _student_header_table(result, class_label, term, s))
        card_elements.append(Spacer(1, 0.3*cm))

        # Marks table
        card_elements.append(_marks_table(result, s))

        if result["curriculum"] == "8-4-4":
            card_elements.append(Paragraph(
                "* Subjects marked with * are counted in the aggregate (Best 7 rule)",
                s["small"]))

        card_elements.append(Spacer(1, 0.4*cm))

        # Comments
        ct = _comment_block("Class Teacher", teacher_comment, s)
        if ct:
            card_elements.append(ct)

        pc = _comment_block("Principal", principal_comment, s)
        if pc:
            card_elements.append(pc)

        card_elements.append(Spacer(1, 0.5*cm))

        # Signature lines
        sig_data = [[
            "Class Teacher: _______________________",
            "Principal: _______________________",
            "Date: _______________",
        ]]
        sig = Table(sig_data, colWidths=[6*cm, 5.5*cm, 4.5*cm])
        sig.setStyle(TableStyle([
            ("FONTNAME",  (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE",  (0, 0), (-1, -1), 8),
            ("TEXTCOLOR", (0, 0), (-1, -1), TEXT_MUTED),
        ]))
        card_elements.append(sig)

        story.append(KeepTogether(card_elements))

        if idx < len(results) - 1:
            story.append(PageBreak())

    doc.build(story, onFirstPage=_page_footer, onLaterPages=_page_footer)
    return len(results), output_path
