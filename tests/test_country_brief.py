import pandas as pd
import pytest

from constants import COUNTRIES
from country_brief import Judgment, generate_brief, load_curated
from scoring import build_composite

VALID_CONFIDENCE_LABELS = {"High confidence", "Moderate confidence", "Low confidence", "Data gap"}


@pytest.fixture(scope="module")
def curated():
    return load_curated()


@pytest.fixture(scope="module")
def composite():
    return build_composite()


@pytest.mark.parametrize("country", list(COUNTRIES.keys()))
def test_generate_brief_for_every_country(country, curated, composite):
    brief = generate_brief(country, curated=curated, composite=composite)

    assert brief.country == country
    assert brief.iso3 == COUNTRIES[country]
    assert isinstance(brief.bluf, str) and len(brief.bluf) > 20
    assert isinstance(brief.key_judgments, list) and len(brief.key_judgments) >= 3

    for judgment in brief.key_judgments:
        assert isinstance(judgment, Judgment)
        assert judgment.confidence in VALID_CONFIDENCE_LABELS
        assert len(judgment.text) > 20
        # every judgment must actually mention the country -- a template bug
        # elsewhere (e.g. a copy-pasted country name) would show up as a
        # judgment that doesn't reference its own subject
        assert country in judgment.text


def test_data_gap_judgment_for_country_with_no_investment_deals(curated, composite):
    """Qatar has no scored investment/compute deals in the curated data --
    its brief must say so explicitly (confidence == 'Data gap'), not silently
    omit the topic or claim a number that isn't there."""
    brief = generate_brief("Qatar", curated=curated, composite=composite)
    gap_judgments = [j for j in brief.key_judgments if j.confidence == "Data gap"]
    assert len(gap_judgments) == 1
    assert "no disclosed" in gap_judgments[0].text.lower()


def test_well_sourced_country_has_no_data_gap_judgment(curated, composite):
    """Saudi Arabia has scored investment and compute deals -- its brief
    should report real figures, not a data-gap judgment."""
    brief = generate_brief("Saudi Arabia", curated=curated, composite=composite)
    gap_judgments = [j for j in brief.key_judgments if j.confidence == "Data gap"]
    assert len(gap_judgments) == 0
    investment_judgments = [j for j in brief.key_judgments if "disclosed, in-country AI infrastructure investment" in j.text]
    assert len(investment_judgments) == 1
    assert "$" in investment_judgments[0].text


def test_sources_are_deduplicated_by_row_not_missing(curated, composite):
    """Every country with curated tier/china/governance rows should carry
    at least those 3 sources (plus any investment/compute deal sources)."""
    brief = generate_brief("Saudi Arabia", curated=curated, composite=composite)
    topics = {s["topic"] for s in brief.sources}
    assert {"Export control", "Chinese tech penetration", "Governance"}.issubset(topics)
