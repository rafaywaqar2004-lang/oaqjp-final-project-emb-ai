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
from investment_flow_engine import bloc_totals, capital_alignment_ratio, unconfirmed_value_count
from sanctions_engine import heatmap_matrix, severity_band

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


def generate_sanctions_brief(
    df: pd.DataFrame, bluf: str, key_judgment: str, why_it_matters: str, as_of: str = "September 2026",
) -> bytes:
    """Regional Sanctions & Entity List Exposure brief. `df` must already be
    sanctions_engine.build_sanctions_composite()'s output -- the same
    DataFrame the live page renders. Covers every tracked country, matching
    the page's own scope: the page has no per-country selector to narrow a
    single-country export to, so this mirrors it rather than inventing a
    narrower cut the UI doesn't otherwise support."""
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=LETTER,
        leftMargin=0.9 * inch, rightMargin=0.9 * inch,
        topMargin=0.85 * inch, bottomMargin=0.85 * inch,
        title="Gulf AI & Tech-Bloc Alignment -- Sanctions Brief",
    )
    s = _styles()
    story = []

    story.append(Paragraph("GULF AI &amp; TECH-BLOC ALIGNMENT TRACKER &middot; SANCTIONS BRIEF", s["eyebrow"]))
    story.append(Paragraph("Sanctions &amp; Entity List Exposure", s["title"]))
    story.append(Paragraph(f"Regional assessment &mdash; as of {as_of}", s["subtitle"]))
    story.append(HRFlowable(width="100%", thickness=1.4, color=LINE, spaceAfter=14))

    story.append(Paragraph("BOTTOM LINE UP FRONT", s["section"]))
    bluf_table = Table([[Paragraph(bluf, s["bluf"])]], colWidths=[6.1 * inch])
    bluf_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PAPER_RAISED),
        ("LINEBEFORE", (0, 0), (0, -1), 3, AMBER),
        ("TOPPADDING", (0, 0), (-1, -1), 12), ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("LEFTPADDING", (0, 0), (-1, -1), 14), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(bluf_table)
    story.append(Spacer(1, 8))
    story.append(Paragraph(f"<b>Key Judgment:</b> {key_judgment}", s["body"]))
    story.append(Paragraph(f"<b>Why It Matters:</b> {why_it_matters}", s["body"]))

    story.append(Paragraph("COUNTRY RANKINGS", s["section"]))
    ranked = df.sort_values("sanctions_exposure_score", ascending=False, na_position="last")
    rank_rows = [["Country", "Sanctions Exposure Score", "Factors Available", "Severity Band"]]
    for _, row in ranked.iterrows():
        score = row["sanctions_exposure_score"]
        available = row.get("sanctions_factors_available")
        rank_rows.append([
            row["country"],
            f"{score:.0f}/100" if pd.notna(score) else "Insufficient data",
            f"{int(available)}/6" if pd.notna(available) else "0/6",
            severity_band(score),
        ])
    story.append(_simple_table(rank_rows, [1.9 * inch, 1.7 * inch, 1.3 * inch, 1.2 * inch], s))

    story.append(Paragraph("FACTOR SEVERITY BY COUNTRY", s["section"]))
    matrix = heatmap_matrix(df)
    header = ["Country"] + list(matrix.columns)
    band_rows = [header] + [[country] + list(row) for country, row in matrix.iterrows()]
    col_width = 6.1 * inch / len(header)
    story.append(_simple_table(band_rows, [col_width] * len(header), s))

    story.append(Paragraph("SANCTIONS EXPOSURE VS. NET ALIGNMENT", s["section"]))
    scored = df.dropna(subset=["sanctions_exposure_score", "net_alignment_score"])
    pos_rows = [["Country", "Net Alignment Score", "Sanctions Exposure Score"]]
    for _, row in scored.sort_values("sanctions_exposure_score", ascending=False).iterrows():
        pos_rows.append([row["country"], f"{row['net_alignment_score']:.0f}/100", f"{row['sanctions_exposure_score']:.0f}/100"])
    story.append(_simple_table(pos_rows, [2.1 * inch, 2.0 * inch, 2.0 * inch], s))
    if len(scored) < len(df):
        story.append(Paragraph(
            f"{len(df) - len(scored)} of {len(df)} tracked countries omitted above: insufficient verified "
            "sanctions and/or net-alignment data to place on this table.", s["footer"],
        ))

    story.append(Paragraph("METHODOLOGY", s["section"]))
    story.append(Paragraph(
        "Sanctions Exposure Score = weighted average of six 0-100 sub-scores (Entity List count 25%, BIS tier "
        "restrictiveness 20%, OFAC active programs 20%, CAATSA status 10%, secondary sanctions risk 15%, "
        "evasion risk 10%), renormalized over whichever factors have verified data for a given country -- a "
        "missing factor is excluded, never scored as zero. Full rubric: see the Sanctions Exposure page's "
        "\"View Calculation\" panel.",
        s["body"],
    ))

    story.append(Paragraph("SOURCES", s["section"]))
    story.append(Paragraph(
        "Every curated figure behind this report is individually cited (source name, URL, confidence, "
        "as-of date) in data/curated/sanctions_data.csv -- see the Sources &amp; Data page for the full catalog.",
        s["body"],
    ))

    story.append(Spacer(1, 18))
    story.append(HRFlowable(width="100%", thickness=0.6, color=LINE, spaceAfter=8))
    story.append(Paragraph(
        "Gulf AI &amp; Tech-Bloc Alignment Tracker &middot; research/portfolio product, not a commissioned or "
        "institutional assessment. This report is a static export of a live, methodology-transparent tool -- "
        "see the app itself for the interactive heatmap and positioning scatter.",
        s["footer"],
    ))

    doc.build(story)
    return buf.getvalue()


def generate_investment_flow_brief(
    flows_df: pd.DataFrame, summary_df: pd.DataFrame, bluf: str, key_judgment: str, why_it_matters: str,
    as_of: str = "September 2026",
) -> bytes:
    """Sovereign AI Investment Flow Tracker brief. `flows_df` must already be
    investment_flow_engine.load_flows()'s output and `summary_df` its
    per_country_summary() -- the same DataFrames the live page renders.
    Covers every tracked deal and country, matching the page's own scope."""
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=LETTER,
        leftMargin=0.9 * inch, rightMargin=0.9 * inch,
        topMargin=0.85 * inch, bottomMargin=0.85 * inch,
        title="Gulf AI & Tech-Bloc Alignment -- Investment Flow Brief",
    )
    s = _styles()
    story = []

    story.append(Paragraph("GULF AI &amp; TECH-BLOC ALIGNMENT TRACKER &middot; INVESTMENT FLOW BRIEF", s["eyebrow"]))
    story.append(Paragraph("Sovereign AI Investment Flow Tracker", s["title"]))
    story.append(Paragraph(f"Regional assessment &mdash; as of {as_of}", s["subtitle"]))
    story.append(HRFlowable(width="100%", thickness=1.4, color=LINE, spaceAfter=14))

    story.append(Paragraph("BOTTOM LINE UP FRONT", s["section"]))
    bluf_table = Table([[Paragraph(bluf, s["bluf"])]], colWidths=[6.1 * inch])
    bluf_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PAPER_RAISED),
        ("LINEBEFORE", (0, 0), (0, -1), 3, AMBER),
        ("TOPPADDING", (0, 0), (-1, -1), 12), ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("LEFTPADDING", (0, 0), (-1, -1), 14), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(bluf_table)
    story.append(Spacer(1, 8))
    story.append(Paragraph(f"<b>Key Judgment:</b> {key_judgment}", s["body"]))
    story.append(Paragraph(f"<b>Why It Matters:</b> {why_it_matters}", s["body"]))

    story.append(Paragraph("SUMMARY", s["section"]))
    totals = bloc_totals(flows_df)
    us_total = totals.get("US", 0.0)
    china_total = totals.get("China", 0.0)
    combined = us_total + china_total
    ratio = capital_alignment_ratio(us_total, china_total)
    unconfirmed = unconfirmed_value_count(flows_df)
    kpi_rows = [
        ["Total tracked investment", f"${combined:,.0f}M (confirmed-value cross-border deals)"],
        ["US-bound investment", f"${us_total:,.0f}M" + (f" ({us_total / combined * 100:.0f}% of total)" if combined else "")],
        ["China-bound investment", f"${china_total:,.0f}M" + (f" ({china_total / combined * 100:.0f}% of total)" if combined else "")],
        ["Capital Alignment Ratio", f"{ratio:.0f}%" if ratio is not None else "N/A"],
        ["Deals with unconfirmed value", f"{unconfirmed} of {len(flows_df)} (excluded from totals above, not treated as zero)"],
    ]
    story.append(_simple_table(kpi_rows, [2.4 * inch, 3.7 * inch], s))

    story.append(Paragraph("CAPITAL ALIGNMENT RATIO BY COUNTRY", s["section"]))
    ranked = summary_df.sort_values("capital_alignment_ratio", ascending=False, na_position="last")
    country_rows = [["Country", "US-bound ($M)", "China-bound ($M)", "Capital Alignment Ratio"]]
    for _, row in ranked.iterrows():
        r = row["capital_alignment_ratio"]
        country_rows.append([
            row["country"], f"{row['us_total_usd_millions']:,.0f}", f"{row['china_total_usd_millions']:,.0f}",
            f"{r:.0f}%" if pd.notna(r) else "Insufficient data",
        ])
    story.append(_simple_table(country_rows, [1.9 * inch, 1.5 * inch, 1.6 * inch, 1.1 * inch], s))

    story.append(Paragraph("TRACKED DEALS", s["section"]))
    deal_rows = []
    for _, row in flows_df.sort_values("date").iterrows():
        value = str(row["deal_value_usd_millions"]).strip()
        try:
            value_disp = f"${float(value):,.0f}M"
        except ValueError:
            value_disp = "Unconfirmed value"
        left = f"<b>{row['date']}</b> -- {row['source_fund']} ({row['source_country']}) -&gt; {row['destination_company']} ({row['destination_country']})"
        right = f"{value_disp} &middot; {row['bloc_affiliation']}-bound &middot; {row['source_url']}"
        deal_rows.append([left, right])
    story.append(_simple_table(deal_rows, [3.0 * inch, 3.1 * inch], s))

    story.append(Paragraph("METHODOLOGY", s["section"]))
    story.append(Paragraph(
        "Capital Alignment Ratio = US-bound / (US-bound + China-bound), over confirmed-value cross-border "
        "deals with bloc_affiliation in {US, China} only. Same-country (\"sovereign launch\") deals are "
        "domestic buildouts, not cross-border flows, and are excluded from every total above -- shown "
        "separately in the deal list. Deals with an unconfirmed dollar value are excluded from every total, "
        "never treated as zero. Full rubric: see src/investment_flow_engine.py's module docstring.",
        s["body"],
    ))

    story.append(Paragraph("SOURCES", s["section"]))
    story.append(Paragraph(
        "Every curated deal above is individually cited (source URL, notes) in "
        "data/curated/investment_flows.csv -- see the Sources &amp; Data page for the full catalog.",
        s["body"],
    ))

    story.append(Spacer(1, 18))
    story.append(HRFlowable(width="100%", thickness=0.6, color=LINE, spaceAfter=8))
    story.append(Paragraph(
        "Gulf AI &amp; Tech-Bloc Alignment Tracker &middot; research/portfolio product, not a commissioned or "
        "institutional assessment. This report is a static export of a live, methodology-transparent tool -- "
        "see the app itself for the interactive Sankey diagram and positioning scatter.",
        s["footer"],
    ))

    doc.build(story)
    return buf.getvalue()
