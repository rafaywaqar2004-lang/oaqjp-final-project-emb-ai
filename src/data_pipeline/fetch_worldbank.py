"""
Fetches the World Bank layer of the index: oil-rents (% GDP, used as an
inverse proxy for non-oil economic diversification) and FDI net inflows
(% GDP). This is the only automatable layer of the tracker -- everything
in data/curated/ is manually researched and cited, and is NOT touched by
this script. Run on a schedule by .github/workflows/refresh_worldbank_data.yml.

World Bank API v2 requires no key. Docs: https://datahelpdesk.worldbank.org/knowledgebase/articles/889392
"""

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from constants import COUNTRIES, WB_INDICATORS, WORLDBANK_DIR  # noqa: E402

API_BASE = "https://api.worldbank.org/v2/country/{iso3}/indicator/{indicator}"
MOST_RECENT_YEARS = 10
RETRY_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 2


def fetch_indicator(iso3: str, indicator: str) -> list[dict]:
    url = f"{API_BASE.format(iso3=iso3, indicator=indicator)}?format=json&per_page=100&mrnev={MOST_RECENT_YEARS}"
    last_error = None
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if not isinstance(payload, list) or len(payload) < 2 or payload[1] is None:
                return []
            return [
                {"iso3": iso3, "indicator": indicator, "year": int(row["date"]), "value": row["value"]}
                for row in payload[1]
                if row.get("value") is not None
            ]
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt < RETRY_ATTEMPTS:
                time.sleep(RETRY_BACKOFF_SECONDS * attempt)
    print(f"WARNING: failed to fetch {indicator} for {iso3} after {RETRY_ATTEMPTS} attempts: {last_error}", file=sys.stderr)
    return []


def most_recent_value(rows: list[dict]) -> dict | None:
    if not rows:
        return None
    return max(rows, key=lambda r: r["year"])


def main() -> None:
    out_dir = Path(WORLDBANK_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)

    all_rows = []
    summary_rows = []

    for country_name, iso3 in COUNTRIES.items():
        summary = {"country": country_name, "iso3": iso3}
        for label, indicator in WB_INDICATORS.items():
            rows = fetch_indicator(iso3, indicator)
            all_rows.extend(rows)
            latest = most_recent_value(rows)
            summary[f"{label}_value"] = latest["value"] if latest else None
            summary[f"{label}_year"] = latest["year"] if latest else None
        summary_rows.append(summary)

    # Non-oil diversification proxy: 100 - oil rents (% of GDP).
    # This is a standard analyst proxy (used e.g. in IMF Article IV GCC
    # coverage), NOT a literal "non-oil share of GDP" figure -- true
    # non-oil GDP accounts are reported inconsistently across these
    # countries' national statistics agencies and are not cleanly
    # available via the World Bank API for all tracked countries in this set.
    # This approximation is documented in the README's limitations section.
    for row in summary_rows:
        oil_rents = row.get("oil_rents_pct_gdp_value")
        row["non_oil_diversification_proxy"] = (100 - oil_rents) if oil_rents is not None else None

    timeseries_path = out_dir / "worldbank_timeseries.csv"
    summary_path = out_dir / "worldbank_latest.csv"

    _write_csv(timeseries_path, all_rows, ["iso3", "indicator", "year", "value"])
    _write_csv(
        summary_path,
        summary_rows,
        [
            "country", "iso3",
            "oil_rents_pct_gdp_value", "oil_rents_pct_gdp_year",
            "fdi_net_inflows_pct_gdp_value", "fdi_net_inflows_pct_gdp_year",
            "gdp_current_usd_value", "gdp_current_usd_year",
            "non_oil_diversification_proxy",
        ],
    )
    print(f"Wrote {len(all_rows)} timeseries rows to {timeseries_path}")
    print(f"Wrote {len(summary_rows)} summary rows to {summary_path}")


def _write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    import csv

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


if __name__ == "__main__":
    main()
