from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, PageBreak, Image, HRFlowable,
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from datetime import date
from pathlib import Path

from routes.settings import get_setting
from routes.students import get_classes, get_students
from routes.terms import get_current_term

ACCENT_HEX = colors.HexColor("#4F46E5")
HEADER_BG  = colors.HexColor("#EEF2FF")
ROW_ALT    = colors.HexColor("#F9FAFB")
BORDER     = colors.HexColor("#E5E7EB")
TEXT_DARK  = colors.HexColor("#111827")
TEXT_MUTED = colors.HexColor("#6B7280")


def _styles():
    return {
        "school": ParagraphStyle("school", fontSize=18,
                                  fontName="Helvetica-Bold",
                                  textColor=ACCENT_HEX,
                                  alignment=TA_CENTER, spaceAfter=2),
        "motto":  ParagraphStyle("motto",  fontSize=10,
                                  fontName="Helvetica-Oblique",
                                  textColor=TEXT_MUTED,
                                  alignment=TA_CENTER, spaceAfter=2),
        "meta":   ParagraphStyle("meta",   fontSize=9,
                                  fontName="Helvetica",
                                  textColor=TEXT_MUTED,
                                  alignment=TA_CENTER, spaceAfter=2),
        "title":  ParagraphStyle("title",  fontSize=13,
                                  fontName="Helvetica-Bold",
                                  textColor=TEXT_DARK,
                                  alignment=TA_CENTER, spaceAfter=2),
    }


def _build_header(story, s, doc_title, student_count):
    logo_path      = get_setting("school_logo",    "")
    school_name    = get_setting("school_name",    "GradeVault School")
    school_motto   = get_setting("school_motto",   "")
    school_contact = get_setting("school_contact", "")
    term           = get_current_term()
    term_str       = f"Term {term['term']}, {term['year']}" if term else ""

    if logo_path and Path(logo_path).exists():
        try:
            img = Image(logo_path)
            max_h, max_w = 3.5 * cm, 14 * cm
            ratio = img.imageWidth / img.imageHeight
            h = max_h
            w = h * ratio
            if w > max_w:
                w = max_w
                h = w / ratio
            img.drawWidth, img.drawHeight = w, h
            img.hAlign = "CENTER"
            story.append(img)
            story.append(Spacer(1, 0.1 * cm))
        except Exception:
            story.append(Paragraph(school_name, s["school"]))
            if school_motto:   story.append(Paragraph(school_motto,   s["motto"]))
            if school_contact: story.append(Paragraph(school_contact, s["meta"]))
    else:
        story.append(Paragraph(school_name, s["school"]))
        if school_motto:   story.append(Paragraph(school_motto,   s["motto"]))
        if school_contact: story.append(Paragraph(school_contact, s["meta"]))

    story.append(Spacer(1, 0.2 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5,
                             color=ACCENT_HEX, spaceAfter=6))
    story.append(Paragraph(doc_title, s["title"]))
    parts = []
    if term_str: parts.append(term_str)
    parts.append(f"{student_count} student(s)")
    story.append(Paragraph("  ·  ".join(parts), s["meta"]))
    story.append(Spacer(1, 0.4 * cm))


def _class_table(students, show_class_col=True):
    """
    show_class_col: False when printing a single class
                    (class is already in the title, no need for a column).
    """
    if show_class_col:
        col_widths = [2.4*cm, 6.0*cm, 3.2*cm, 2.0*cm]
        header     = ["Adm. No.", "Full Name", "Class", "Gender"]
    else:
        col_widths = [2.4*cm, 9.2*cm, 2.0*cm]
        header     = ["Adm. No.", "Full Name", "Gender"]

    rows = [header]
    for s in students:
        stream    = s.get("stream") or ""
        cls_name  = s.get("class_name") or ""
        class_lbl = f"{cls_name} {stream}".strip() if stream else cls_name
        gender    = s.get("gender") or "—"

        if show_class_col:
            rows.append([s["admission_number"], s["full_name"], class_lbl, gender])
        else:
            rows.append([s["admission_number"], s["full_name"], gender])

    t = Table(rows, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), HEADER_BG),
        ("TEXTCOLOR",     (0, 0), (-1, 0), ACCENT_HEX),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 9),
        ("TOPPADDING",    (0, 0), (-1, 0), 7),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 7),
        ("FONTNAME",      (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",      (0, 1), (-1, -1), 9),
        ("TOPPADDING",    (0, 1), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
        *[("BACKGROUND",  (0, i), (-1, i), ROW_ALT)
          for i in range(2, len(rows), 2)],
        ("GRID",   (0, 0), (-1, -1), 0.4, BORDER),
        ("ALIGN",  (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return t


def _sig_block():
    sig = Table(
        [["Class Teacher: ___________________________", "Date: _______________"]],
        colWidths=[10*cm, 5.7*cm],
    )
    sig.setStyle(TableStyle([
        ("FONTNAME",  (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE",  (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (-1, -1), TEXT_MUTED),
    ]))
    return sig


def _page_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(TEXT_MUTED)
    canvas.drawCentredString(
        A4[0] / 2, 1.4 * cm,
        f"GradeVault  ·  Printed {date.today().strftime('%d %B %Y')}"
        f"  ·  Page {doc.page}",
    )
    canvas.restoreState()


def generate_class_list(output_path: str,
                         class_id: int = None,
                         class_name_filter: str = None,
                         gender_filter: str = None):
    """
    class_id=None, class_name_filter=None  → all classes (show Class column)
    class_id=int                            → single stream class (no Class column)
    class_name_filter="Grade 10"           → all streams of that class merged (no Class column)
    """
    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm,  bottomMargin=2.5*cm,
    )
    s       = _styles()
    story   = []
    classes = get_classes()

    # ── Single stream ────────────────────────────────────────
    if class_id:
        cls = next((c for c in classes if c["id"] == class_id), None)
        if not cls:
            return output_path
        students = get_students(class_id=cls["id"])
        if not students:
            return output_path
        stream    = cls.get("stream") or ""
        lbl       = f"{cls['name']} {stream}".strip() if stream else cls["name"]
        _build_header(story, s, f"Class List — {lbl}", len(students))
        story.append(_class_table(students, show_class_col=False))
        story.append(Spacer(1, 1.2 * cm))
        story.append(_sig_block())

    # ── All streams of one class name (e.g. all Grade 10) ───
    elif class_name_filter:
        matched = [c for c in classes if c["name"] == class_name_filter]
        all_students = []
        for c in matched:
            all_students.extend(get_students(class_id=c["id"]))
        if gender_filter:
            all_students = [s for s in all_students if s.get("gender") == gender_filter]
        if not all_students:
            return output_path
        _build_header(story, s,
                      f"Class List — {class_name_filter} (All streams)",
                      len(all_students))
        story.append(_class_table(all_students, show_class_col=len(matched) > 1))
        story.append(Spacer(1, 1.2 * cm))
        story.append(_sig_block())

    # ── All classes ──────────────────────────────────────────
    else:
        for idx, cls in enumerate(classes):
            students = get_students(class_id=cls["id"])
            if not students:
                continue
            stream = cls.get("stream") or ""
            lbl    = f"{cls['name']} {stream}".strip() if stream else cls["name"]
            _build_header(story, s, f"Class List — {lbl}", len(students))
            story.append(_class_table(students, show_class_col=True))
            story.append(Spacer(1, 1.2 * cm))
            story.append(_sig_block())
            if idx < len(classes) - 1:
                story.append(PageBreak())

    doc.build(story, onFirstPage=_page_footer, onLaterPages=_page_footer)
    return output_path
