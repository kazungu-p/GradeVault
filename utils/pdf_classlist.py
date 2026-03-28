from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, PageBreak,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from datetime import date
from db.connection import query
from routes.students import get_classes, get_students


# ── Palette ──────────────────────────────────────────────────
ACCENT_HEX  = colors.HexColor("#4F46E5")
HEADER_BG   = colors.HexColor("#EEF2FF")
ROW_ALT     = colors.HexColor("#F9FAFB")
BORDER      = colors.HexColor("#E5E7EB")
TEXT_DARK   = colors.HexColor("#111827")
TEXT_MUTED  = colors.HexColor("#6B7280")


def _styles():
    base = getSampleStyleSheet()
    return {
        "school": ParagraphStyle("school", fontSize=18, fontName="Helvetica-Bold",
                                  textColor=ACCENT_HEX, alignment=TA_CENTER),
        "title":  ParagraphStyle("title", fontSize=13, fontName="Helvetica-Bold",
                                  textColor=TEXT_DARK, alignment=TA_CENTER, spaceAfter=2),
        "meta":   ParagraphStyle("meta", fontSize=9, fontName="Helvetica",
                                  textColor=TEXT_MUTED, alignment=TA_CENTER, spaceAfter=4),
        "footer": ParagraphStyle("footer", fontSize=8, fontName="Helvetica",
                                  textColor=TEXT_MUTED, alignment=TA_CENTER),
    }


def _class_table(students):
    """Build a platypus Table for a list of students."""
    col_widths = [2.2*cm, 6.5*cm, 3.0*cm, 2.0*cm]

    # Header row
    header = ["Adm. No.", "Full Name", "Class & Stream", "Gender"]
    rows = [header]

    for i, s in enumerate(students, start=1):
        class_stream = f"{s.get('class_name', '')} {s.get('stream', '')}".strip()
        rows.append([
            s["admission_number"],
            s["full_name"],
            class_stream,
            s.get("gender") or "—",
        ])

    t = Table(rows, colWidths=col_widths, repeatRows=1)
    style = TableStyle([
        # Header
        ("BACKGROUND",   (0, 0), (-1, 0), HEADER_BG),
        ("TEXTCOLOR",    (0, 0), (-1, 0), ACCENT_HEX),
        ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, 0), 9),
        ("BOTTOMPADDING",(0, 0), (-1, 0), 6),
        ("TOPPADDING",   (0, 0), (-1, 0), 6),
        # Body
        ("FONTNAME",     (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",     (0, 1), (-1, -1), 9),
        ("TOPPADDING",   (0, 1), (-1, -1), 5),
        ("BOTTOMPADDING",(0, 1), (-1, -1), 5),
        # Alternating rows
        *[("BACKGROUND", (0, i), (-1, i), ROW_ALT)
          for i in range(2, len(rows), 2)],
        # Grid
        ("GRID",         (0, 0), (-1, -1), 0.4, BORDER),
        ("ROWBACKGROUNDS", (0, 0), (-1, 0), [HEADER_BG]),
        ("ALIGN",        (0, 0), (-1, -1), "LEFT"),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
    ])
    t.setStyle(style)
    return t


def _page_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(TEXT_MUTED)
    canvas.drawCentredString(
        A4[0] / 2, 1.5 * cm,
        f"GradeVault  ·  Printed {date.today().strftime('%d %B %Y')}  ·  Page {doc.page}"
    )
    canvas.restoreState()


def generate_class_list(output_path: str, class_id: int = None):
    """
    Generate a PDF class list.
    - class_id=None  → all classes, one per page
    - class_id=int   → single class
    """
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2.5*cm,
    )
    s = _styles()
    story = []

    classes = get_classes()
    if class_id:
        classes = [c for c in classes if c["id"] == class_id]

    for idx, cls in enumerate(classes):
        students = get_students(class_id=cls["id"])
        if not students:
            continue

        class_label = f"{cls['name']} {cls['stream']}"

        # Page header
        story.append(Paragraph("St. Mary's High School", s["school"]))
        story.append(Spacer(1, 0.2*cm))
        story.append(Paragraph(f"Class List — {class_label}", s["title"]))
        story.append(Paragraph(
            f"Term 1, 2026  ·  {len(students)} student(s)",
            s["meta"]
        ))
        story.append(Spacer(1, 0.4*cm))

        story.append(_class_table(students))

        # Signature block
        story.append(Spacer(1, 1.2*cm))
        sig_data = [
            ["Class Teacher: ___________________________",
             "Date: _______________"],
        ]
        sig_table = Table(sig_data, colWidths=[10*cm, 5.7*cm])
        sig_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("TEXTCOLOR",(0, 0), (-1, -1), TEXT_MUTED),
        ]))
        story.append(sig_table)

        # Page break between classes (not after last)
        if idx < len(classes) - 1:
            story.append(PageBreak())

    doc.build(story, onFirstPage=_page_footer, onLaterPages=_page_footer)
    return output_path
