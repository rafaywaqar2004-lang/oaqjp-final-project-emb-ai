"""
Renders a CountryBrief (see country_brief.py) to a downloadable per-country
PDF, and the regional composite scores to a downloadable executive PDF --
both via reportlab, pure Python, no system dependencies, so they work on
Render's free tier without extra build steps.
"""

from __future__ import annotations

from io import BytesIO

import pandas as pd
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


def _simple_table(rows: list[list[str]], col_widths: list[float], styles: dict) -> Table:
    data = [[Paragraph(str(cell), styles["source"]) for cell in row] for row in rows]
    table = Table(data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def build_country_pdf(
    brief: CountryBrief,
    current_position: dict | None = None,
    key_drivers: pd.DataFrame | None = None,
    what_changed: list[dict] | None = None,
    strategic_implications: dict | None = None,
    watch_items: pd.DataFrame | None = None,
    data_quality: pd.DataFrame | None = None,
) -> bytes:
    """The optional params add the Current Position / Key Drivers / Recent
    Developments / Strategic Implications / What to Watch / Data Quality
    sections a full intelligence-profile brief needs -- each is skipped
    silently if not supplied, so this still works as a plain BLUF+Key
    Judgments+Sources brief when called with only `brief`."""
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

    if current_position:
        story.append(Paragraph("CURRENT POSITION", s["section"]))
        pos_rows = [[k, v] for k, v in current_position.items()]
        story.append(_simple_table(pos_rows, [2.2 * inch, 3.9 * inch], s))

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

    if key_drivers is not None and not key_drivers.empty:
        story.append(Paragraph("KEY DRIVERS", s["section"]))
        header = list(key_drivers.columns)
        rows = [header] + key_drivers.astype(str).values.tolist()
        col_width = 6.1 * inch / len(header)
        story.append(_simple_table(rows, [col_width] * len(header), s))

    if what_changed:
        story.append(Paragraph("RECENT DEVELOPMENTS", s["section"]))
        for ev in what_changed:
            story.append(Paragraph(f"<b>{ev['date']}</b> &mdash; {ev['title']}", s["body"]))

    if strategic_implications:
        story.append(Paragraph("STRATEGIC IMPLICATIONS", s["section"]))
        for role in ("policymakers", "investors", "corporates"):
            if role in strategic_implications:
                story.append(Paragraph(f"<b>{role.title()}:</b> {strategic_implications[role]}", s["body"]))

    if watch_items is not None and not watch_items.empty:
        story.append(Paragraph("WHAT TO WATCH", s["section"]))
        for _, item in watch_items.iterrows():
            story.append(Paragraph(f"<b>{item['indicator']}</b> &mdash; {item['why_it_matters']}", s["body"]))

    if data_quality is not None and not data_quality.empty:
        story.append(Paragraph("DATA QUALITY", s["section"]))
        rows = data_quality.astype(str).values.tolist()
        story.append(_simple_table(rows, [1.8 * inch, 4.3 * inch], s))

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


def build_executive_pdf(
    key_findings: dict,
    composite: pd.DataFrame,
    what_changed: list[dict],
    risk_matrix: pd.DataFrame,
    as_of: str = "September 2026",
) -> bytes:
    """The regional executive brief: Executive Summary, Regional
    Positioning, Country Rankings, What Changed, Strategic Risk,
    Methodology, Sources -- built entirely from data already computed
    elsewhere in this tracker (key_findings from regional_dashboard's
    _key_findings(), composite from build_composite(), what_changed from
    the policy events feed, risk_matrix from strategic_risk.assess_all()).
    No Outlook section: this project's 12-Month Outlook is explicitly
    analyst judgment, not something to present as reproducible in a
    static export without its own caveats -- the app page is the
    canonical place to read it."""
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=LETTER,
        leftMargin=0.9 * inch, rightMargin=0.9 * inch,
        topMargin=0.85 * inch, bottomMargin=0.85 * inch,
        title="Gulf AI & Tech-Bloc Alignment -- Strategic Assessment",
    )
    s = _styles()
    story = []

    story.append(Paragraph("GULF AI &amp; TECHNOLOGY ALIGNMENT", s["eyebrow"]))
    story.append(Paragraph("Strategic Assessment", s["title"]))
    story.append(Paragraph(f"Regional executive brief &mdash; as of {as_of}", s["subtitle"]))
    story.append(HRFlowable(width="100%", thickness=1.4, color=LINE, spaceAfter=14))

    story.append(Paragraph("EXECUTIVE SUMMARY", s["section"]))
    bl_table = Table([[Paragraph(key_findings.get("bottom_line", ""), s["bluf"])]], colWidths=[6.1 * inch])
    bl_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PAPER_RAISED),
        ("LINEBEFORE", (0, 0), (0, -1), 3, AMBER),
        ("TOPPADDING", (0, 0), (-1, -1), 12), ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("LEFTPADDING", (0, 0), (-1, -1), 14), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(bl_table)
    story.append(Spacer(1, 8))
    story.append(Paragraph(f"<b>Key Judgment:</b> {key_findings.get('key_judgment', '')}", s["body"]))
    story.append(Paragraph(f"<b>Why It Matters:</b> {key_findings.get('why_it_matters', '')}", s["body"]))

    story.append(Paragraph("REGIONAL POSITIONING", s["section"]))
    scored = composite.dropna(subset=["net_alignment_score"])
    pos_summary = [
        ["Countries tracked", str(len(composite))],
        ["Countries scored", f"{len(scored)} / {len(composite)}"],
        ["Regional avg. Net Alignment", f"{scored['net_alignment_score'].mean():.0f}/100" if not scored.empty else "N/A"],
    ]
    story.append(_simple_table(pos_summary, [2.5 * inch, 3.6 * inch], s))

    story.append(Paragraph("COUNTRY RANKINGS", s["section"]))
    ranked = composite.sort_values("net_alignment_score", ascending=False, na_position="last")
    rank_rows = [["Country", "Net Alignment", "US Integration", "China Exposure"]]
    for _, row in ranked.iterrows():
        rank_rows.append([
            row["country"],
            f"{row['net_alignment_score']:.0f}" if pd.notna(row["net_alignment_score"]) else "N/A",
            f"{row['us_integration_depth']:.0f}" if pd.notna(row["us_integration_depth"]) else "N/A",
            f"{row['china_exposure_depth']:.0f}" if pd.notna(row["china_exposure_depth"]) else "N/A",
        ])
    story.append(_simple_table(rank_rows, [2.2 * inch, 1.3 * inch, 1.3 * inch, 1.3 * inch], s))

    if what_changed:
        story.append(Paragraph("WHAT CHANGED", s["section"]))
        for ev in what_changed[:8]:
            story.append(Paragraph(f"<b>{ev['date']}</b> &mdash; {ev['title']} ({ev.get('direction', '')})", s["body"]))

    if risk_matrix is not None and not risk_matrix.empty:
        story.append(Paragraph("STRATEGIC RISK", s["section"]))
        header = list(risk_matrix.columns)
        rows = [header] + risk_matrix.astype(str).values.tolist()
        col_width = 6.1 * inch / len(header)
        story.append(_simple_table(rows, [col_width] * len(header), s))

    story.append(Paragraph("METHODOLOGY", s["section"]))
    story.append(Paragraph(
        "Net Alignment Score = 50 + (US Integration Depth &minus; China Exposure Depth) / 2. US Integration "
        "Depth blends US export-control tier (40%), disclosed AI investment (30%), and disclosed compute "
        "capacity (30%). China Exposure Depth blends Chinese telecom penetration and Chinese AI/cloud/digital "
        "ties (50% each). Full rubrics, weights, and known limitations: see the Methodology page.",
        s["body"],
    ))

    story.append(Paragraph("SOURCES", s["section"]))
    story.append(Paragraph(
        "Every curated figure behind this report is individually cited (source name, URL, confidence, "
        "as-of date) in data/curated/*.csv -- see the Sources &amp; Data page for the full catalog.",
        s["body"],
    ))

    story.append(Spacer(1, 18))
    story.append(HRFlowable(width="100%", thickness=0.6, color=LINE, spaceAfter=8))
    story.append(Paragraph(
        "Gulf AI &amp; Tech-Bloc Alignment Tracker &middot; research/portfolio product, not a commissioned or "
        "institutional assessment. This report is a static export of a live, methodology-transparent tool -- "
        "see the app itself for interactive scenario testing and the full per-country intelligence profiles.",
        s["footer"],
    ))

    doc.build(story)
    return buf.getvalue()
