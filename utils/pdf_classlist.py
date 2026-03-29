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

from db.connection import query
from routes.settings import get_setting
from routes.students import get_classes, get_students
from routes.terms import get_current_term

# ── Palette ──────────────────────────────────────────────────
ACCENT_HEX = colors.HexColor("#4F46E5")
HEADER_BG  = colors.HexColor("#EEF2FF")
ROW_ALT    = colors.HexColor("#F9FAFB")
BORDER     = colors.HexColor("#E5E7EB")
TEXT_DARK  = colors.HexColor("#111827")
TEXT_MUTED = colors.HexColor("#6B7280")


def _styles():
    return {
        "school":  ParagraphStyle("school",  fontSize=18,
                                   fontName="Helvetica-Bold",
                                   textColor=ACCENT_HEX,
                                   alignment=TA_CENTER,
                                   spaceAfter=2),
        "motto":   ParagraphStyle("motto",   fontSize=10,
                                   fontName="Helvetica-Oblique",
                                   textColor=TEXT_MUTED,
                                   alignment=TA_CENTER,
                                   spaceAfter=2),
        "meta":    ParagraphStyle("meta",    fontSize=9,
                                   fontName="Helvetica",
                                   textColor=TEXT_MUTED,
                                   alignment=TA_CENTER,
                                   spaceAfter=2),
        "title":   ParagraphStyle("title",   fontSize=13,
                                   fontName="Helvetica-Bold",
                                   textColor=TEXT_DARK,
                                   alignment=TA_CENTER,
                                   spaceAfter=2),
    }


def _build_header(story, s, class_label, student_count):
    """Build page header — logo if available, else text."""
    school_name    = get_setting("school_name",    "GradeVault School")
    school_motto   = get_setting("school_motto",   "")
    school_contact = get_setting("school_contact", "")
    logo_path      = get_setting("school_logo",    "")

    term = get_current_term()
    term_str = f"Term {term['term']}, {term['year']}" if term else ""

    # If logo uploaded — show it only, skip all text (letterhead has everything)
    if logo_path and Path(logo_path).exists():
        try:
            img = Image(logo_path)
            max_h = 3.5 * cm
            max_w = 14 * cm
            ratio = img.imageWidth / img.imageHeight
            h = max_h
            w = h * ratio
            if w > max_w:
                w = max_w
                h = w / ratio
            img.drawWidth  = w
            img.drawHeight = h
            img.hAlign = "CENTER"
            story.append(img)
            story.append(Spacer(1, 0.1 * cm))
        except Exception:
            # Fallback to text if image fails to load
            story.append(Paragraph(school_name, s["school"]))
            if school_motto:
                story.append(Paragraph(school_motto, s["motto"]))
            if school_contact:
                story.append(Paragraph(school_contact, s["meta"]))
    else:
        # No logo — show text header
        story.append(Paragraph(school_name, s["school"]))
        if school_motto:
            story.append(Paragraph(school_motto, s["motto"]))
        if school_contact:
            story.append(Paragraph(school_contact, s["meta"]))

    # Divider line
    story.append(Spacer(1, 0.2 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5,
                             color=ACCENT_HEX, spaceAfter=6))

    # Document title
    story.append(Paragraph(f"Class List — {class_label}", s["title"]))
    parts = []
    if term_str:
        parts.append(term_str)
    parts.append(f"{student_count} student(s)")
    story.append(Paragraph("  ·  ".join(parts), s["meta"]))
    story.append(Spacer(1, 0.4 * cm))


def _class_table(students):
    col_widths = [2.4*cm, 7.0*cm, 3.2*cm, 2.0*cm]
    header = ["Adm. No.", "Full Name", "Class", "Gender"]
    rows   = [header]

    for s in students:
        # Build class label cleanly — no "None"
        stream = s.get("stream") or ""
        cls_name = s.get("class_name") or ""
        class_label = f"{cls_name} {stream}".strip() if stream else cls_name

        rows.append([
            s["admission_number"],
            s["full_name"],
            class_label,
            s.get("gender") or "—",
        ])

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
        ("GRID",          (0, 0), (-1, -1), 0.4, BORDER),
        ("ALIGN",         (0, 0), (-1, -1), "LEFT"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return t


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


def generate_class_list(output_path: str, class_id: int = None):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm,  bottomMargin=2.5*cm,
    )
    s       = _styles()
    story   = []
    classes = get_classes()

    if class_id:
        classes = [c for c in classes if c["id"] == class_id]

    for idx, cls in enumerate(classes):
        students = get_students(class_id=cls["id"])
        if not students:
            continue

        stream = cls.get("stream") or ""
        class_label = (f"{cls['name']} {stream}".strip()
                       if stream else cls["name"])

        _build_header(story, s, class_label, len(students))
        story.append(_class_table(students))

        # Signature line
        story.append(Spacer(1, 1.2 * cm))
        sig = Table(
            [["Class Teacher: ___________________________",
              "Date: _______________"]],
            colWidths=[10*cm, 5.7*cm],
        )
        sig.setStyle(TableStyle([
            ("FONTNAME",  (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE",  (0, 0), (-1, -1), 9),
            ("TEXTCOLOR", (0, 0), (-1, -1), TEXT_MUTED),
        ]))
        story.append(sig)

        if idx < len(classes) - 1:
            story.append(PageBreak())

    doc.build(story, onFirstPage=_page_footer, onLaterPages=_page_footer)
    return output_path
