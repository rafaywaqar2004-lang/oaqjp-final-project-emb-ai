import datetime

import pandas as pd
import pytest

from candidate_review import pending_candidates, record_review, REVIEW_LOG_COLUMNS
from fetch_candidate_events import (
    match_tracked_countries,
    parse_federal_register_response,
    parse_ofac_recent_actions_html,
)

# A real Federal Register API response snippet, captured this session --
# not a fabricated/simplified shape, the actual field set the live API
# returns for the fields this project requests.
_FR_SAMPLE = {
    "results": [
        {
            "title": "Revisions to the Entity List",
            "publication_date": "2026-08-24",
            "html_url": "https://www.federalregister.gov/documents/2026/08/24/2026-17231/revisions-to-the-entity-list",
            "abstract": "In this rule, the Bureau of Industry and Security (BIS) revises the Export Administration Regulations (EAR) ... under the destination of China.",
            "document_number": "2026-17231",
        },
        {
            "title": "Removal From the Entity List",
            "publication_date": "2026-08-24",
            "html_url": "https://www.federalregister.gov/documents/2026/08/24/2026-17230/removal-from-the-entity-list",
            "abstract": "In this rule, the Bureau of Industry and Security (BIS) amends the Export Administration Regulations (EAR) by removing one entity from the Entity List under the destination of Turkey.",
            "document_number": "2026-17230",
        },
    ]
}

# A real snippet of OFAC's Recent Actions page HTML, captured this session.
_OFAC_SAMPLE_HTML = """
<div class="margin-bottom-4 search-result views-row"><div><div class="font-sans-lg margin-bottom-05 margin-top-1 text-no-underline"><a href="https://ofac.treasury.gov/recent-actions/20260904" hreflang="en">Iran-related Designations; Issuance of Iran-related General License</a></div></div><div><div class="margin-top-1 font-sans-2xs line-height-sans-3 margin-bottom-1">September 04, 2026 -
<a href="https://ofac.treasury.gov/recent-actions/sanctions-list-updates">Sanctions List Updates</a></div></div></div>
    <div class="margin-bottom-4 search-result views-row"><div><div class="font-sans-lg margin-bottom-05 margin-top-1 text-no-underline"><a href="https://ofac.treasury.gov/recent-actions/20260824" hreflang="en">Removal of Syria's designation as a State Sponsor of Terrorism</a></div></div><div><div class="margin-top-1 font-sans-2xs line-height-sans-3 margin-bottom-1">August 24, 2026 -
<a href="https://ofac.treasury.gov/recent-actions/sanctions-list-updates">Sanctions List Updates</a></div></div></div>
"""


class TestMatchTrackedCountries:
    def test_matches_a_tracked_country_case_insensitively(self):
        assert match_tracked_countries("a rule affecting saudi arabia") == "Saudi Arabia"

    def test_matches_multiple_countries(self):
        result = match_tracked_countries("Iran and Syria were both named")
        assert "Iran" in result and "Syria" in result

    def test_no_match_returns_empty_string(self):
        assert match_tracked_countries("a rule about aluminum tariffs") == ""

    def test_empty_text_returns_empty_string(self):
        assert match_tracked_countries("") == ""
        assert match_tracked_countries(None) == ""


class TestParseFederalRegisterResponse:
    def test_parses_real_sample_shape(self):
        result = parse_federal_register_response(_FR_SAMPLE)
        assert len(result) == 2
        assert result[0]["source"] == "Federal Register (BIS)"
        assert result[0]["external_id"] == "2026-17231"
        assert result[0]["date"] == "2026-08-24"
        assert result[0]["title"] == "Revisions to the Entity List"
        assert result[0]["url"].startswith("https://www.federalregister.gov/")

    def test_entity_list_removal_matches_its_named_country(self):
        result = parse_federal_register_response(_FR_SAMPLE)
        removal = next(r for r in result if r["external_id"] == "2026-17230")
        assert removal["matched_countries"] == "Turkey"

    def test_missing_results_key_returns_empty_list(self):
        assert parse_federal_register_response({}) == []

    def test_null_abstract_does_not_crash(self):
        payload = {"results": [{"title": "x", "publication_date": "2026-01-01", "html_url": "u", "abstract": None, "document_number": "1"}]}
        result = parse_federal_register_response(payload)
        assert result[0]["summary"] == ""


class TestParseOfacRecentActionsHtml:
    def test_parses_real_sample_html(self):
        result = parse_ofac_recent_actions_html(_OFAC_SAMPLE_HTML, datetime.date(2026, 1, 1))
        assert len(result) == 2
        assert result[0]["source"] == "OFAC"
        assert result[0]["external_id"] == "20260904"
        assert result[0]["date"] == "2026-09-04"
        assert "Iran-related Designations" in result[0]["title"]
        assert result[0]["matched_countries"] == "Iran"

    def test_apostrophe_in_title_is_preserved(self):
        result = parse_ofac_recent_actions_html(_OFAC_SAMPLE_HTML, datetime.date(2026, 1, 1))
        syria_entry = next(r for r in result if r["external_id"] == "20260824")
        assert "Syria's" in syria_entry["title"]
        assert "Syria" in syria_entry["matched_countries"]

    def test_entries_older_than_since_date_are_dropped(self):
        result = parse_ofac_recent_actions_html(_OFAC_SAMPLE_HTML, datetime.date(2026, 9, 1))
        assert len(result) == 1
        assert result[0]["external_id"] == "20260904"

    def test_malformed_html_returns_empty_list_not_a_crash(self):
        assert parse_ofac_recent_actions_html("<html><body>no matches here</body></html>", datetime.date(2020, 1, 1)) == []


class TestPendingCandidates:
    @pytest.fixture
    def candidates(self):
        return pd.DataFrame([
            {"source": "OFAC", "external_id": "1", "date": "2026-09-01", "title": "a", "summary": "", "url": "u", "matched_countries": ""},
            {"source": "OFAC", "external_id": "2", "date": "2026-09-02", "title": "b", "summary": "", "url": "u", "matched_countries": ""},
            {"source": "Federal Register (BIS)", "external_id": "1", "date": "2026-09-03", "title": "c", "summary": "", "url": "u", "matched_countries": ""},
        ])

    def test_no_review_log_returns_all_candidates_newest_first(self, candidates):
        empty_log = pd.DataFrame(columns=REVIEW_LOG_COLUMNS)
        result = pending_candidates(candidates, empty_log)
        assert list(result["date"]) == ["2026-09-03", "2026-09-02", "2026-09-01"]

    def test_reviewed_candidate_is_excluded(self, candidates):
        log = pd.DataFrame([{"source": "OFAC", "external_id": "1", "status": "rejected", "reviewed_at": "x"}])
        result = pending_candidates(candidates, log)
        assert "1" not in result[result["source"] == "OFAC"]["external_id"].values

    def test_same_external_id_different_source_is_not_confused(self, candidates):
        """OFAC external_id '1' and Federal Register external_id '1' are
        different documents -- reviewing one must not hide the other."""
        log = pd.DataFrame([{"source": "OFAC", "external_id": "1", "status": "rejected", "reviewed_at": "x"}])
        result = pending_candidates(candidates, log)
        assert "1" in result[result["source"] == "Federal Register (BIS)"]["external_id"].values

    def test_empty_candidates_returns_empty(self):
        empty = pd.DataFrame(columns=["source", "external_id", "date", "title", "summary", "url", "matched_countries"])
        assert pending_candidates(empty, pd.DataFrame(columns=REVIEW_LOG_COLUMNS)).empty


class TestRecordReview:
    def test_record_review_appends_and_persists(self, tmp_path, monkeypatch):
        import candidate_review
        log_path = tmp_path / "review_log.csv"
        monkeypatch.setattr(candidate_review, "REVIEW_LOG_PATH", log_path)

        record_review("OFAC", "20260904", "confirmed")
        log = candidate_review.load_review_log()
        assert len(log) == 1
        assert log.iloc[0]["source"] == "OFAC"
        assert log.iloc[0]["status"] == "confirmed"

        record_review("Federal Register (BIS)", "2026-17231", "rejected")
        log = candidate_review.load_review_log()
        assert len(log) == 2
