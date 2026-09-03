import pandas as pd
import pytest

from constants import COUNTRIES
from sanctions_engine import (
    ENTITY_LIST_CEILING,
    SANCTIONS_WEIGHTS,
    _bis_tier_score,
    _caatsa_score,
    _entity_list_score,
    _is_research_needed,
    _ofac_score,
    _severity_score,
    build_sanctions_composite,
    heatmap_matrix,
    load_sanctions,
    severity_band,
)


@pytest.fixture(scope="module")
def sanctions():
    return build_sanctions_composite()


def test_weights_sum_to_one():
    assert sum(SANCTIONS_WEIGHTS.values()) == pytest.approx(1.0)


def test_csv_has_a_row_per_tracked_country():
    df = load_sanctions()
    assert set(df["country"]) == set(COUNTRIES.keys())
    assert len(df) == len(COUNTRIES)


def test_csv_has_no_bare_na_lookalike_cells():
    """Regression guard: pandas silently reads a bare 'None'/'N/A' cell as
    NaN under default na_values, which previously turned two countries'
    caatsa_status into a missing value instead of the real text 'None on
    file'. Every cell in the curated CSV must avoid the exact NA-lookalike
    tokens pandas treats as missing by default."""
    default_na = {
        "", "#N/A", "#N/A N/A", "#NA", "-1.#IND", "-1.#QNAN", "-NaN", "-nan",
        "1.#IND", "1.#QNAN", "<NA>", "N/A", "NA", "NULL", "NaN", "None", "n/a", "nan", "null",
    }
    df = pd.read_csv("data/curated/sanctions_data.csv", keep_default_na=False)
    for col in df.columns:
        assert df[df[col].isin(default_na)].empty, f"column {col!r} has a bare NA-lookalike cell"


class TestIsResearchNeeded:
    def test_recognizes_research_needed(self):
        assert _is_research_needed("RESEARCH_NEEDED") is True
        assert _is_research_needed("research_needed (no source found)") is True

    def test_recognizes_real_values(self):
        assert _is_research_needed("None (country level)") is False
        assert _is_research_needed("IRAN; IRGC; SDN") is False

    def test_non_string_is_research_needed(self):
        assert _is_research_needed(float("nan")) is True


class TestEntityListScore:
    def test_research_needed_is_nan(self):
        assert pd.isna(_entity_list_score("RESEARCH_NEEDED"))

    def test_zero_maps_to_zero(self):
        assert _entity_list_score("0") == pytest.approx(0.0)

    def test_ceiling_maps_to_hundred(self):
        assert _entity_list_score(str(ENTITY_LIST_CEILING)) == pytest.approx(100.0)

    def test_above_ceiling_clips_at_hundred(self):
        assert _entity_list_score(str(ENTITY_LIST_CEILING * 5)) == pytest.approx(100.0)


class TestBisTierScore:
    def test_most_favorable_tier_scores_lowest(self):
        assert _bis_tier_score(5) == pytest.approx(0.0)

    def test_least_favorable_tier_scores_highest(self):
        assert _bis_tier_score(0) == pytest.approx(100.0)

    def test_nan_passes_through(self):
        assert pd.isna(_bis_tier_score(float("nan")))


class TestOfacScore:
    def test_research_needed_is_nan(self):
        assert pd.isna(_ofac_score("RESEARCH_NEEDED"))

    def test_none_scores_zero(self):
        assert _ofac_score("None (country level)") == pytest.approx(0.0)

    def test_one_program_scores_fifty(self):
        assert _ofac_score("IRAN") == pytest.approx(50.0)

    def test_two_programs_scores_hundred(self):
        assert _ofac_score("IRAN; IRGC") == pytest.approx(100.0)

    def test_many_programs_clips_at_hundred(self):
        assert _ofac_score("A; B; C; D; E") == pytest.approx(100.0)


class TestCaatsaScore:
    def test_research_needed_is_nan(self):
        assert pd.isna(_caatsa_score("RESEARCH_NEEDED"))

    def test_none_on_file_scores_zero(self):
        assert _caatsa_score("None on file") == pytest.approx(0.0)

    def test_none_found_with_extra_text_scores_zero(self):
        assert _caatsa_score("None found") == pytest.approx(0.0)

    def test_threatened_scores_fifty(self):
        assert _caatsa_score("None on file -- CAATSA sanctions were explicitly threatened in 2019 but never imposed") == pytest.approx(50.0)

    def test_active_designation_scores_hundred(self):
        assert _caatsa_score("CAATSA Section 231 sanctions imposed 14 Dec 2020") == pytest.approx(100.0)


class TestSeverityScore:
    def test_research_needed_is_nan(self):
        mapping = {"low": 0.0, "moderate": 50.0, "high": 100.0}
        assert pd.isna(_severity_score("RESEARCH_NEEDED", mapping))

    def test_prefix_match_with_trailing_explanation(self):
        mapping = {"low": 0.0, "moderate": 50.0, "high": 100.0}
        assert _severity_score("Moderate (Iran trade/border exposure)", mapping) == pytest.approx(50.0)


class TestSeverityBand:
    def test_nan_is_insufficient_data(self):
        assert severity_band(float("nan")) == "Insufficient data"

    def test_zero_is_none_band(self):
        assert severity_band(0) == "None"

    def test_hundred_is_severe_band(self):
        assert severity_band(100) == "Severe"

    @pytest.mark.parametrize("score,expected", [(10, "None"), (30, "Low"), (50, "Moderate"), (70, "High"), (90, "Severe")])
    def test_band_boundaries(self, score, expected):
        assert severity_band(score) == expected


class TestBuildSanctionsComposite:
    def test_returns_a_row_per_country(self, sanctions):
        assert len(sanctions) == len(COUNTRIES)

    def test_score_is_within_0_100_or_nan(self, sanctions):
        for _, row in sanctions.iterrows():
            score = row["sanctions_exposure_score"]
            assert pd.isna(score) or (0 <= score <= 100)

    def test_factors_available_never_exceeds_six(self, sanctions):
        assert (sanctions["sanctions_factors_available"] <= 6).all()

    def test_bis_tier_never_missing(self, sanctions):
        """bis_tier_score_100 is reused from this project's own always-populated
        export_control_tier.csv -- every country should have it, unlike the
        research-pending factors."""
        assert sanctions["bis_tier_score_100"].notna().all()

    def test_net_alignment_score_joined_in(self, sanctions):
        assert "net_alignment_score" in sanctions.columns
        assert sanctions["net_alignment_score"].notna().sum() > 0

    def test_iran_and_syria_score_higher_than_uae(self, sanctions):
        """A sanity check on directionality: countries under comprehensive
        BIS/OFAC restriction should score a materially higher Sanctions
        Exposure Score than a country with a favorable Country Group and no
        disclosed CAATSA/OFAC exposure."""
        by_country = sanctions.set_index("country")["sanctions_exposure_score"]
        assert by_country["Iran"] > by_country["United Arab Emirates"]
        assert by_country["Syria"] > by_country["United Arab Emirates"]

    def test_every_country_has_at_least_five_of_six_factors(self, sanctions):
        """secondary_sanctions_risk/sanctions_evasion_risk were extended to
        all 17 countries (derived transparently from the OFAC/EU/CAATSA
        facts already on file, never a fresh unsourced claim) -- only
        entity_list_count should still be missing anywhere."""
        assert (sanctions["sanctions_factors_available"] >= 5).all()

    def test_no_country_has_research_needed_judgment_fields(self):
        """Regression guard: every country's secondary_sanctions_risk and
        sanctions_evasion_risk should be a real judgment, not the
        RESEARCH_NEEDED placeholder, now that all 17 have been populated."""
        df = load_sanctions()
        assert not df["secondary_sanctions_risk"].str.upper().str.startswith("RESEARCH_NEEDED").any()
        assert not df["sanctions_evasion_risk"].str.upper().str.startswith("RESEARCH_NEEDED").any()


class TestHeatmapMatrix:
    def test_has_a_row_per_country_and_expected_columns(self, sanctions):
        matrix = heatmap_matrix(sanctions)
        assert len(matrix) == len(COUNTRIES)
        assert set(matrix.columns) == {"Entity List", "BIS Tier", "OFAC Programs", "CAATSA", "Secondary Sanctions Risk", "Evasion Risk"}

    def test_every_cell_is_a_recognized_band(self, sanctions):
        matrix = heatmap_matrix(sanctions)
        valid_bands = {"Insufficient data", "None", "Low", "Moderate", "High", "Severe"}
        for col in matrix.columns:
            assert set(matrix[col].unique()) <= valid_bands
