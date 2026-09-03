import pandas as pd
import pytest

from investment_flow_engine import (
    TRACKED_SOURCE_COUNTRIES,
    _is_research_needed,
    _parse_value,
    bloc_totals,
    by_quarter,
    by_sector,
    capital_alignment_ratio,
    cross_border_flows,
    domestic_sovereign_deals,
    load_flows,
    per_country_summary,
    sankey_data,
    unconfirmed_value_count,
    with_parsed_value,
)


@pytest.fixture(scope="module")
def flows():
    return load_flows()


def test_csv_has_no_bare_na_lookalike_cells():
    """Regression guard, same class of bug caught in sanctions_data.csv:
    pandas silently reads a bare 'None'/'N/A' cell as NaN under default
    na_values."""
    default_na = {
        "", "#N/A", "#N/A N/A", "#NA", "-1.#IND", "-1.#QNAN", "-NaN", "-nan",
        "1.#IND", "1.#QNAN", "<NA>", "N/A", "NA", "NULL", "NaN", "None", "n/a", "nan", "null",
    }
    df = pd.read_csv("data/curated/investment_flows.csv", keep_default_na=False, dtype=str)
    for col in df.columns:
        assert df[df[col].isin(default_na)].empty, f"column {col!r} has a bare NA-lookalike cell"


def test_csv_uses_canonical_country_names(flows):
    """source_country must match this project's canonical names (the same
    ones in src/constants.py's COUNTRIES dict), not an abbreviation like
    'UAE' -- otherwise per-country aggregation and the net_alignment_score
    join silently drop rows."""
    from constants import COUNTRIES
    assert set(flows["source_country"]) <= set(COUNTRIES.keys())


class TestIsResearchNeeded:
    def test_recognizes_research_needed(self):
        assert _is_research_needed("RESEARCH_NEEDED") is True

    def test_recognizes_real_values(self):
        assert _is_research_needed("1500") is False

    def test_non_string_is_research_needed(self):
        assert _is_research_needed(float("nan")) is True


class TestParseValue:
    def test_research_needed_is_nan(self):
        assert pd.isna(_parse_value("RESEARCH_NEEDED"))

    def test_numeric_string_parses(self):
        assert _parse_value("1500") == pytest.approx(1500.0)


class TestCrossBorderFlows:
    def test_excludes_same_country_deals(self, flows):
        cb = cross_border_flows(flows)
        assert (cb["source_country"] != cb["destination_country"]).all()

    def test_domestic_deals_are_the_complement(self, flows):
        cb = cross_border_flows(flows)
        dom = domestic_sovereign_deals(flows)
        assert len(cb) + len(dom) == len(flows)

    def test_humain_sovereign_launch_is_domestic(self, flows):
        dom = domestic_sovereign_deals(flows)
        assert "003" in set(dom["deal_id"])


class TestUnconfirmedValueCount:
    def test_counts_research_needed_values(self, flows):
        assert unconfirmed_value_count(flows) == int(
            flows["deal_value_usd_millions"].apply(_is_research_needed).sum()
        )

    def test_empty_dataframe_returns_zero(self, flows):
        empty = flows.iloc[0:0]
        assert unconfirmed_value_count(empty) == 0


class TestCapitalAlignmentRatio:
    def test_all_us_is_100(self):
        assert capital_alignment_ratio(100.0, 0.0) == pytest.approx(100.0)

    def test_all_china_is_0(self):
        assert capital_alignment_ratio(0.0, 100.0) == pytest.approx(0.0)

    def test_even_split_is_50(self):
        assert capital_alignment_ratio(50.0, 50.0) == pytest.approx(50.0)

    def test_no_data_is_none(self):
        assert capital_alignment_ratio(0.0, 0.0) is None
        assert capital_alignment_ratio(None, None) is None


class TestPerCountrySummary:
    def test_returns_a_row_per_tracked_source_country(self, flows):
        summary = per_country_summary(flows)
        assert set(summary["country"]) == set(TRACKED_SOURCE_COUNTRIES)
        assert len(summary) == len(TRACKED_SOURCE_COUNTRIES)

    def test_ratio_is_within_0_100_or_nan(self, flows):
        summary = per_country_summary(flows)
        for _, row in summary.iterrows():
            r = row["capital_alignment_ratio"]
            assert pd.isna(r) or (0 <= r <= 100)

    def test_country_with_no_confirmed_deals_has_nan_ratio(self, flows):
        summary = per_country_summary(flows)
        bahrain = summary[summary["country"] == "Bahrain"].iloc[0]
        assert bahrain["n_deals"] == 0
        assert pd.isna(bahrain["capital_alignment_ratio"])

    def test_net_alignment_score_joined_in(self, flows):
        summary = per_country_summary(flows)
        assert "net_alignment_score" in summary.columns
        assert summary["net_alignment_score"].notna().sum() > 0


class TestByQuarterAndSector:
    def test_by_quarter_has_us_and_china_columns(self, flows):
        result = by_quarter(flows)
        assert "US" in result.columns
        assert "China" in result.columns

    def test_by_quarter_excludes_unconfirmed_and_domestic(self, flows):
        result = by_quarter(flows)
        # Only 3 of 10 deals have a confirmed value AND a confirmed date AND
        # are cross-border with a US/China bloc: Microsoft->G42 ($1500M US),
        # SCAI->SenseTime ($206.54M China), and the Pakistan-China fiber
        # loan ($44M China).
        assert result["US"].sum() == pytest.approx(1500.0)
        assert result["China"].sum() == pytest.approx(250.54)

    def test_by_sector_has_no_unconfirmed_totals(self, flows):
        result = by_sector(flows)
        assert result["total_usd_millions"].notna().all()


class TestSankeyData:
    def test_labels_cover_every_country_in_links(self, flows):
        sd = sankey_data(flows)
        max_index = max(sd["links"]["source"] + sd["links"]["target"])
        assert max_index < len(sd["labels"])

    def test_excludes_domestic_deals(self, flows):
        sd = sankey_data(flows)
        # HUMAIN's domestic sovereign launch (Saudi Arabia -> Saudi Arabia)
        # should never appear as a self-loop link.
        for s, t in zip(sd["links"]["source"], sd["links"]["target"]):
            assert s != t
