import pandas as pd
import pytest

from constants import COUNTRIES
from country_brief import generate_brief, load_curated
from investment_flow_engine import load_flows, per_country_summary
from pdf_export import build_country_pdf, build_executive_pdf, generate_investment_flow_brief, generate_sanctions_brief
from sanctions_engine import build_sanctions_composite
from scoring import build_composite
from strategic_risk_engine import assess_all


@pytest.fixture(scope="module")
def composite():
    return build_composite()


@pytest.fixture(scope="module")
def curated():
    return load_curated()


@pytest.mark.parametrize("country", list(COUNTRIES.keys()))
def test_build_country_pdf_minimal_call_produces_a_valid_pdf(country, composite, curated):
    """The original minimal call shape (brief only) must keep working --
    every optional section is skippable."""
    brief = generate_brief(country, curated=curated, composite=composite)
    pdf_bytes = build_country_pdf(brief)
    assert pdf_bytes[:4] == b"%PDF"
    assert len(pdf_bytes) > 500


@pytest.mark.parametrize("country", list(COUNTRIES.keys()))
def test_build_country_pdf_full_call_produces_a_valid_pdf(country, composite, curated):
    """The full intelligence-profile call shape (all optional sections
    supplied) must also succeed for every tracked country, including ones
    with empty deal/watch-item tables."""
    brief = generate_brief(country, curated=curated, composite=composite)
    row = composite[composite["country"] == country].iloc[0]

    key_drivers = pd.DataFrame([
        {"Axis": "US Integration Depth", "Component": "US Export-Control Tier", "Confidence": "High"},
    ])
    what_changed = [{"date": "2026-07-10", "title": "Test event"}]
    strategic_implications = {"policymakers": "Test policy text.", "investors": "Test investor text.", "corporates": "Test corporate text."}
    watch_items = pd.DataFrame([{"indicator": "Test indicator", "why_it_matters": "Test reason"}])
    data_quality = pd.DataFrame([{"Dimension": "Factor coverage", "Value": "5 of 5"}])

    pdf_bytes = build_country_pdf(
        brief,
        current_position={"Net Alignment Score": f"{row['net_alignment_score']:.0f}/100" if pd.notna(row["net_alignment_score"]) else "N/A"},
        key_drivers=key_drivers,
        what_changed=what_changed,
        strategic_implications=strategic_implications,
        watch_items=watch_items,
        data_quality=data_quality,
    )
    assert pdf_bytes[:4] == b"%PDF"
    assert len(pdf_bytes) > 500


def test_build_country_pdf_handles_empty_optional_tables(composite, curated):
    """An empty (but present) DataFrame for an optional section must not
    crash -- it should behave the same as omitting the section entirely."""
    brief = generate_brief("Qatar", curated=curated, composite=composite)
    pdf_bytes = build_country_pdf(
        brief,
        key_drivers=pd.DataFrame(),
        watch_items=pd.DataFrame(),
        data_quality=pd.DataFrame(),
        what_changed=[],
    )
    assert pdf_bytes[:4] == b"%PDF"


def test_build_executive_pdf_produces_a_valid_pdf(composite, curated):
    key_findings = {
        "bottom_line": "Test bottom line.", "key_judgment": "Test key judgment.",
        "confidence": "Moderate", "why_it_matters": "Test why it matters.",
    }
    what_changed = [{"date": "2026-07-10", "title": "Test event", "direction": "Loosening"}]
    risk_matrix = assess_all(composite, curated)
    pdf_bytes = build_executive_pdf(key_findings, composite, what_changed, risk_matrix)
    assert pdf_bytes[:4] == b"%PDF"
    assert len(pdf_bytes) > 500


def test_build_executive_pdf_handles_empty_what_changed_and_risk_matrix(composite):
    key_findings = {"bottom_line": "x", "key_judgment": "x", "confidence": "Moderate", "why_it_matters": "x"}
    pdf_bytes = build_executive_pdf(key_findings, composite, [], pd.DataFrame())
    assert pdf_bytes[:4] == b"%PDF"


def test_executive_pdf_includes_every_tracked_country_in_rankings(composite, curated):
    """The Country Rankings section must cover all 17 countries -- a
    silently dropped row here would be a real regression, not cosmetic."""
    key_findings = {"bottom_line": "x", "key_judgment": "x", "confidence": "Moderate", "why_it_matters": "x"}
    risk_matrix = assess_all(composite, curated)
    pdf_bytes = build_executive_pdf(key_findings, composite, [], risk_matrix)
    # A crude but real signal: the PDF's byte size scales with row count --
    # this at least confirms it isn't silently truncating to a handful of rows.
    small_pdf = build_executive_pdf(key_findings, composite.head(2), [], risk_matrix.head(2))
    assert len(pdf_bytes) > len(small_pdf)


def test_generate_sanctions_brief_produces_a_valid_pdf():
    df = build_sanctions_composite()
    pdf_bytes = generate_sanctions_brief(df, "Test BLUF.", "Test key judgment.", "Test why it matters.")
    assert pdf_bytes[:4] == b"%PDF"
    assert len(pdf_bytes) > 500


def test_generate_investment_flow_brief_produces_a_valid_pdf():
    flows = load_flows()
    summary = per_country_summary(flows)
    pdf_bytes = generate_investment_flow_brief(flows, summary, "Test BLUF.", "Test key judgment.", "Test why it matters.")
    assert pdf_bytes[:4] == b"%PDF"
    assert len(pdf_bytes) > 500


def test_generate_investment_flow_brief_handles_a_country_with_no_deals():
    """No tracked deals for a country must not crash the per-country
    capital-alignment table or the deal list."""
    flows = load_flows()
    empty_flows = flows.iloc[0:0]
    summary = per_country_summary(empty_flows)
    pdf_bytes = generate_investment_flow_brief(empty_flows, summary, "x", "x", "x")
    assert pdf_bytes[:4] == b"%PDF"


class TestFormatDealValue:
    """Regression coverage for the bug this project's own adversarial code
    review caught: an unconfirmed (NaN) deal value must render as
    "Unconfirmed value", never as the literal string "$nanM"."""

    def test_real_value_formats_as_currency(self):
        from pdf_export import _format_deal_value
        assert _format_deal_value(1500.0) == "$1,500M"

    def test_nan_value_renders_as_unconfirmed(self):
        from pdf_export import _format_deal_value
        assert _format_deal_value(float("nan")) == "Unconfirmed value"
        assert "nan" not in _format_deal_value(float("nan")).lower()
