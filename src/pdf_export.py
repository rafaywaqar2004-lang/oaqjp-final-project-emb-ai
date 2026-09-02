"""
Renders a CountryBrief (see country_brief.py) to a downloadable PDF using
reportlab -- pure Python, no system dependencies, so it works on Render's
free tier without extra build steps.
"""

from __future__ import annotations

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from country_brief import CountryBrief

INK = colors.HexColor("#1b1e22")
INK_SOFT = colors.HexColor("#52585f")
AMBER = colors.HexColor("#8a6416")
US_BLUE = colors.HexColor("#2454a6")
CHINA_RED = colors.HexColor("#a93a2e")
LINE = colors.HexColor("#c3c0b3")
PAPER_RAISED = colors.HexColor("#f2f1ea")

_CONFIDENCE_COLOR = {
    "High confidence": (AMBER, "#8a6416"),
    "Moderate confidence": (INK_SOFT, "#52585f"),
    "Low confidence": (INK_SOFT, "#52585f"),
    "Data gap": (CHINA_RED, "#a93a2e"),
}
_DEFAULT_CONFIDENCE_COLOR = (INK_SOFT, "#52585f")


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "eyebrow": ParagraphStyle("eyebrow", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=8, textColor=INK_SOFT, tracking=1, spaceAfter=6),
        "title": ParagraphStyle("title", parent=base["Title"], fontName="Times-Bold", fontSize=22, textColor=INK, leading=26, spaceAfter=4, alignment=0),
        "subtitle": ParagraphStyle("subtitle", parent=base["Normal"], fontName="Times-Italic", fontSize=12, textColor=INK_SOFT, spaceAfter=14),
        "section": ParagraphStyle("section", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=10, textColor=AMBER, spaceBefore=18, spaceAfter=8),
        "body": ParagraphStyle("body", parent=base["Normal"], fontName="Times-Roman", fontSize=10.5, leading=15, textColor=INK, alignment=TA_JUSTIFY, spaceAfter=8),
        "bluf": ParagraphStyle("bluf", parent=base["Normal"], fontName="Times-Roman", fontSize=11, leading=16, textColor=INK, alignment=TA_JUSTIFY),
        "confidence": ParagraphStyle("confidence", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=7.5, spaceAfter=2),
        "source": ParagraphStyle("source", parent=base["Normal"], fontName="Helvetica", fontSize=8, textColor=INK_SOFT, leading=11),
        "footer": ParagraphStyle("footer", parent=base["Normal"], fontName="Helvetica", fontSize=7.5, textColor=INK_SOFT, leading=11),
    }


def build_country_pdf(brief: CountryBrief) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=LETTER,
        leftMargin=0.9 * inch, rightMargin=0.9 * inch,
        topMargin=0.85 * inch, bottomMargin=0.85 * inch,
        title=f"{brief.country} -- Gulf AI & Tech-Bloc Alignment Brief",
    )
    s = _styles()
    story = []

    story.append(Paragraph("GULF AI &amp; TECH-BLOC ALIGNMENT TRACKER &middot; COUNTRY BRIEF", s["eyebrow"]))
    story.append(Paragraph(f"{brief.country}", s["title"]))
    story.append(Paragraph(f"AI/chip-bloc alignment assessment &mdash; as of {brief.as_of}", s["subtitle"]))
    story.append(HRFlowable(width="100%", thickness=1.4, color=LINE, spaceAfter=14))

    story.append(Paragraph("BOTTOM LINE UP FRONT", s["section"]))
    bluf_table = Table([[Paragraph(brief.bluf, s["bluf"])]], colWidths=[6.1 * inch])
    bluf_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PAPER_RAISED),
        ("LINEBEFORE", (0, 0), (0, -1), 3, AMBER),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(bluf_table)

    story.append(Paragraph("KEY JUDGMENTS", s["section"]))
    for i, j in enumerate(brief.key_judgments, start=1):
        color, hex_color = _CONFIDENCE_COLOR.get(j.confidence, _DEFAULT_CONFIDENCE_COLOR)
        conf_style = ParagraphStyle("conf_dyn", parent=s["confidence"], textColor=color)
        story.append(Paragraph(f"{i:02d} &nbsp;&nbsp; <font color='{hex_color}'>&#9679;</font> {j.confidence.upper()}", conf_style))
        story.append(Paragraph(j.text, s["body"]))

    story.append(Paragraph("SOURCES", s["section"]))
    if brief.sources:
        rows = [[Paragraph(f"<b>{src['topic']}</b>", s["source"]), Paragraph(f"{src['name']} ({src['date']})", s["source"])] for src in brief.sources]
        src_table = Table(rows, colWidths=[1.6 * inch, 4.5 * inch])
        src_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LINEBELOW", (0, 0), (-1, -2), 0.4, LINE),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(src_table)
    else:
        story.append(Paragraph("No sourced rows on file for this country.", s["body"]))

    story.append(Spacer(1, 18))
    story.append(HRFlowable(width="100%", thickness=0.6, color=LINE, spaceAfter=8))
    story.append(Paragraph(
        "Auto-generated from the Gulf AI &amp; Tech-Bloc Alignment Tracker's cited dataset "
        "(data/curated/*.csv). This is a research/portfolio product, not a commissioned or "
        "institutional assessment. Full sourcing, confidence ratings, and methodology: see the "
        "tracker's README and the companion brief, 'Gulf AI Ambitions and Geopolitical Risk.'",
        s["footer"],
    ))

    doc.build(story)
    return buf.getvalue()
