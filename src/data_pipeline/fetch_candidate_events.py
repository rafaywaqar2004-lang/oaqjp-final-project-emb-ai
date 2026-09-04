"""
Fetches candidate policy events from two official, free, public sources --
the Federal Register API (BIS documents) and OFAC's Recent Actions page --
and writes them to data/candidate_events/candidates.csv for human review.

This is NOT an auto-ingest pipeline. Nothing this script fetches is ever
written to data/curated/policy_events.csv directly -- a human reviews each
candidate on the Candidate Events page and decides whether to add it,
exactly like every other curated fact in this project. See that page's
docstring and src/candidate_events.py for the review-queue logic.

Run on a schedule by .github/workflows/refresh_candidate_events.yml.
Uses only the standard library (urllib, re, json), matching
fetch_worldbank.py's no-new-dependencies approach -- OFAC's Recent Actions
page has no public JSON/RSS API (its RSS feed was retired), so it's parsed
with a regex tuned to its current, stable, repeated HTML block structure.
That parser is deliberately defensive: a change to OFAC's page layout
should degrade to zero OFAC candidates (logged as a warning), never crash
the whole pipeline -- the Federal Register half is independent and must
keep working either way.
"""

import csv
import json
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from constants import CANDIDATE_EVENTS_DIR, COUNTRIES  # noqa: E402

FEDERAL_REGISTER_URL = "https://www.federalregister.gov/api/v1/documents.json"
BIS_AGENCY_SLUG = "industry-and-security-bureau"
OFAC_RECENT_ACTIONS_URL = "https://ofac.treasury.gov/recent-actions"
RETRY_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 2
REQUEST_TIMEOUT_SECONDS = 30
USER_AGENT = "Mozilla/5.0 (compatible; GulfAITechBlocTracker/1.0; research tool, not a bot/crawler)"

_OFAC_ENTRY_RE = re.compile(
    r'<a href="(https://ofac\.treasury\.gov/recent-actions/(\d{8}))"[^>]*>(.*?)</a>'
    r'.*?<a href="[^"]*">([^<]*)</a>',
    re.DOTALL,
)


def _http_get(url: str) -> str | None:
    """GET with retries, returning the response body as text or None on
    total failure. Shared by both fetchers so a network hiccup is handled
    identically -- warn to stderr, never raise."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    last_error = None
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                return response.read().decode("utf-8", errors="replace")
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
            last_error = exc
            if attempt < RETRY_ATTEMPTS:
                time.sleep(RETRY_BACKOFF_SECONDS * attempt)
    print(f"WARNING: failed to fetch {url} after {RETRY_ATTEMPTS} attempts: {last_error}", file=sys.stderr)
    return None


def match_tracked_countries(text: str) -> str:
    """Best-effort substring match of this project's tracked country names
    within a candidate's title/summary -- semicolon-joined, empty string if
    none match. A global rule (e.g. an Entity List revision naming no
    country) can still be a real candidate even with no match here; this is
    a helper for the reviewer's attention, not a filter."""
    if not text:
        return ""
    lower = text.lower()
    return "; ".join(name for name in COUNTRIES if name.lower() in lower)


def parse_federal_register_response(payload: dict) -> list[dict]:
    """Pure parsing logic, separated from the HTTP call so it's directly
    unit-testable against a fixed sample payload."""
    results = payload.get("results")
    if not isinstance(results, list):
        return []
    out = []
    for doc in results:
        title = doc.get("title") or ""
        abstract = doc.get("abstract") or ""
        out.append({
            "source": "Federal Register (BIS)",
            "external_id": doc.get("document_number", ""),
            "date": doc.get("publication_date", ""),
            "title": title,
            "summary": abstract,
            "url": doc.get("html_url", ""),
            "matched_countries": match_tracked_countries(f"{title} {abstract}"),
        })
    return out


def fetch_federal_register(days_back: int) -> list[dict]:
    since = (datetime.now(timezone.utc) - timedelta(days=days_back)).date().isoformat()
    query = (
        f"?conditions[agencies][]={BIS_AGENCY_SLUG}"
        f"&conditions[publication_date][gte]={since}"
        "&order=newest&per_page=100"
        "&fields[]=title&fields[]=publication_date&fields[]=html_url"
        "&fields[]=abstract&fields[]=document_number"
    )
    body = _http_get(FEDERAL_REGISTER_URL + query)
    if body is None:
        return []
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        print(f"WARNING: Federal Register response was not valid JSON: {exc}", file=sys.stderr)
        return []
    return parse_federal_register_response(payload)


def parse_ofac_recent_actions_html(html: str, since_date) -> list[dict]:
    """Pure parsing logic, separated from the HTTP call so it's directly
    unit-testable against a fixed sample HTML snippet. `since_date` is a
    datetime.date; entries older than it are dropped. The page's own URL
    slug encodes the date as YYYYMMDD, which is more reliable than parsing
    the human-readable "September 04, 2026" text next to each entry."""
    out = []
    for match in _OFAC_ENTRY_RE.finditer(html):
        url, date_slug, title_html, category = match.groups()
        try:
            entry_date = datetime.strptime(date_slug, "%Y%m%d").date()
        except ValueError:
            continue
        if entry_date < since_date:
            continue
        title = re.sub(r"<[^>]+>", "", title_html).strip()
        if not title:
            continue
        out.append({
            "source": "OFAC",
            "external_id": date_slug,
            "date": entry_date.isoformat(),
            "title": title,
            "summary": f"OFAC category: {category.strip()}" if category else "",
            "url": url,
            "matched_countries": match_tracked_countries(title),
        })
    return out


def fetch_ofac_recent_actions(days_back: int) -> list[dict]:
    html = _http_get(OFAC_RECENT_ACTIONS_URL)
    if html is None:
        return []
    since_date = (datetime.now(timezone.utc) - timedelta(days=days_back)).date()
    candidates = parse_ofac_recent_actions_html(html, since_date)
    if not candidates:
        print("WARNING: parsed zero OFAC candidates -- the page layout may have changed", file=sys.stderr)
    return candidates


def main() -> None:
    days_back = 45
    federal_register = fetch_federal_register(days_back)
    ofac = fetch_ofac_recent_actions(days_back)
    all_candidates = federal_register + ofac
    all_candidates.sort(key=lambda c: c["date"], reverse=True)

    out_dir = Path(CANDIDATE_EVENTS_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "candidates.csv"
    fieldnames = ["source", "external_id", "date", "title", "summary", "url", "matched_countries"]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_candidates)

    print(f"Wrote {len(all_candidates)} candidates ({len(federal_register)} Federal Register, {len(ofac)} OFAC) to {out_path}")


if __name__ == "__main__":
    main()
