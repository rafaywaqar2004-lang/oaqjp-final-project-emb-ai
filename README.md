# Gulf AI & Tech-Bloc Alignment Tracker

A companion piece to the [MENASA Risk Monitor](#): tracks how Gulf states -- plus Pakistan and Turkey as
smaller-scale, non-Gulf comparators -- are navigating the US-China AI/chip competition, and what that
means for regional stability and Western strategic interests.

**Status: all four phases built** -- composite index, choropleth map, radar/bar comparison view, a
chronological sourced feed of chip-policy events, per-country deep-dive pages with an auto-generated
analyst brief and downloadable PDF, and a live scenario-reweighting explorer.
This repo's `briefs/` folder also holds three written analytic pieces produced alongside this dashboard:
[`gulf-ai-ambitions-and-geopolitical-risk.md`](briefs/gulf-ai-ambitions-and-geopolitical-risk.md) (this
project's own companion brief), plus two pieces that belong to the MENASA Risk Monitor project instead --
[`sovereign-debt-and-political-instability.md`](briefs/sovereign-debt-and-political-instability.md) and
[`mena-geopolitical-risk-brief-issue-01.md`](briefs/mena-geopolitical-risk-brief-issue-01.md) -- written here
only because this was the session's one writable repo; see `PROGRESS.md` for why and where they should move.
See [`PROGRESS.md`](PROGRESS.md) for what's built, what's next, and open questions for the project owner.

---

## What this is (and isn't)

This is a research/portfolio project aimed at analyst roles (CIA, CFR, CSIS, PIIE, Oxford Analytica-type
work) and geopolitical/economic risk consulting. It is **not** a forecasting tool, an investment signal, or
an authoritative government assessment. Where public data was too thin to responsibly support a number,
that gap is shown explicitly (`"insufficient public data"`) rather than filled with an estimate presented
as fact -- the same principle the MENASA Risk Monitor applies to Iran-sanctions data gaps.

## Country set

**Gulf (6):** Saudi Arabia, United Arab Emirates, Qatar, Bahrain, Kuwait, Oman
**Non-Gulf comparators (2):** Pakistan, Turkey -- both navigating similar US/China balancing acts on a
smaller scale (Pakistan via CPEC/Huawei telecom integration alongside a new, cabinet-approved National AI
Policy; Turkey via a decades-long Huawei/Turkcell partnership alongside NATO membership and the 2020 CAATSA
sanctions precedent over its S-400 purchase from Russia).

## Methodology

### Two axes, not one score pretending to be simple

A Gulf state maximizing ties with **both** Washington and Beijing simultaneously (the empirically observed
pattern -- e.g. the UAE running the most US-favorable chip-export status in the region while also running
Huawei radio equipment on live 5G networks) is not "confused" or "neutral" -- it's hedging, and that is
exactly the story this tracker exists to show. A single linear score collapses that signal. So the index is
built in two layers:

1. **US Integration Depth** (0-100) -- a weighted average of:
   - **US export-control access tier** (0-5 ordinal, curated) -- weight 0.40
   - **Disclosed in-country AI infrastructure investment** ($bn, log-scaled) -- weight 0.30
   - **Disclosed/under-development compute capacity** (MW, log-scaled) -- weight 0.30

2. **China Exposure Depth** (0-100) -- currently a single factor:
   - **Chinese tech penetration** (0-5 ordinal, curated; chiefly Huawei's telecom/cloud footprint)

3. **Net Alignment Score** (0-100, 50 = neutral), *derived*, not independently weighted:
   ```
   Net Alignment Score = 50 + (US Integration Depth - China Exposure Depth) / 2
   ```
   Higher = more US-integrated relative to Chinese exposure. Lower = more Chinese-exposed relative to US
   integration. **50 does not mean "inactive"** -- a country maxing out both axes and a country doing
   little on either can both land near 50. Always read the two sub-scores (visible in the country ranking
   list and the comparison table) alongside the headline number.

Two more factors are tracked but deliberately **not folded into the alignment score** -- they measure state
capacity, not bloc alignment, and a mature AI regulator or a diversified economy doesn't inherently signal
pro-US or pro-China:

- **AI governance maturity** (0-5 ordinal, curated) -- existence of a national AI strategy, a dedicated
  authority/regulator, and binding sectoral rules.
- **Non-oil economic diversification** (World Bank, live-refreshed) -- see [Data sources](#data-sources).

### Why 6 factors, not 8-10

The original brief allowed 6-8 factors. Research (documented per-country in `data/curated/*.csv`) confirmed
all 6 of the brief's original factors are sourceable for at least the Gulf's two AI leaders, but data depth
drops off sharply for Qatar, Bahrain, Kuwait, Oman, Pakistan, and Turkey -- a methodologically sound 6-factor
index beat padding to 8 with factors that would be mostly `N/A` outside Saudi Arabia and the UAE.

### Why log-scale, fixed-ceiling normalization (not dataset min-max)

Investment and compute figures are normalized with `log10(x+1) / log10(ceiling+1) * 100`, clipped to
[0, 100] -- **not** dataset-relative min-max. With only 2-3 countries carrying any disclosed investment/
compute figure at all, min-max normalization would stretch a modest real gap (Saudi Arabia's $34.2bn vs.
the UAE's $15.2bn in scored deals) into an artificial 100-vs-0 spread, misrepresenting two countries that
are both genuinely substantial. Fixed ceilings (`INVESTMENT_CEILING_USD_BN = 50`, `COMPUTE_CEILING_MW =
6000` in `src/scoring.py`) keep scores stable as new deals are disclosed and make "what it would take to
score 100" an explicit, documented choice instead of an artifact of who else happens to be in the data set
this month. Both ceilings are grounded in the data itself (the ceiling sits just above Saudi Arabia's
current scored total; the compute ceiling matches Saudi Arabia's own disclosed 2034 national target).

### Missing-data handling

A country missing one of the three US Integration Depth inputs still gets a score -- the weighted average
renormalizes over whichever factors are available (tracked in `us_integration_factors_available`). A
country with **zero** available inputs for an axis shows `N/A` for that axis and for the derived Net
Alignment Score, and is rendered gray on the map rather than silently defaulted to a floor score. This
mirrors how the MENASA Risk Monitor handles the Iran sanctions/missing-data problem.

### Ordinal (0-5) factors: not a clean pulled number, and that's disclosed

The **US export-control access tier** and **Chinese tech penetration** factors are scored on a documented
0-5 rubric rather than a single clean public number, because none exists at this granularity. This is a
deliberate, disclosed methodology choice (an analyst-desk judgment call, same as a country-risk analyst
would make), not an attempt to disguise a soft estimate as a hard figure. The full rubric, the specific
source(s) behind every country's score, and a `confidence` rating (High/Medium/Low) are all in
`data/curated/export_control_tier.csv` and `data/curated/chinese_tech_penetration.csv`. **Several `Low`
confidence entries are explicitly flagged for follow-up research** -- see [Known limitations](#known-limitations).

#### US export-control access tier rubric

| Score | Meaning |
|---|---|
| 0 | Comprehensively restricted / arms-embargoed (Country Group D:5 equivalent) |
| 1 | No bilateral framework; standard case-by-case EAR licensing |
| 2 | Some licensing accommodation, no formal bilateral deal or approved-entity status |
| 3 | Bespoke, entity-specific authorization for a capped chip volume |
| 4 | Formal bilateral AI cooperation framework; license-free access for BIS-approved entities |
| 5 | Full closest-ally treatment; broad license-free access, no entity-specific cap |

As of this research pass, only the UAE (4) and Saudi Arabia (3) have any disclosed bilateral arrangement at
all -- both dated within the last year (UAE: BIS Country Group A:5 upgrade, 10 Jul 2026; Saudi Arabia:
HUMAIN/G42 35,000-GB300-equivalent authorization, 19 Nov 2025). This space is moving fast: the Biden-era "AI
Diffusion Rule" (would have imposed a worldwide license requirement) was rescinded by the Trump
administration on 13 May 2025 in favor of exactly this kind of bilateral, government-to-government
dealmaking, so this factor should be re-verified before any presentation of this project, not treated as
static.

#### Chinese tech penetration rubric

| Score | Meaning |
|---|---|
| 0 | No significant Chinese ICT vendor presence |
| 1 | Minimal, isolated non-core relationships |
| 2 | Moderate -- a few Huawei contracts, non-core |
| 3 | Significant -- Huawei is a major/core RAN vendor for at least one major carrier |
| 4 | Deep -- Huawei core RAN across multiple major carriers, plus cloud/enterprise expansion |
| 5 | Extensive -- Huawei is the leading/sole 5G vendor across all major carriers, plus deep economic ties |

## Data sources

| Layer | Type | Refresh cadence | Where |
|---|---|---|---|
| Non-oil diversification proxy, FDI net inflows | **Live, automated** | Weekly (GitHub Actions, Mondays) | World Bank API v2, `src/data_pipeline/fetch_worldbank.py` → `data/worldbank/` |
| US export-control tier, Chinese tech penetration, AI governance maturity | **Manually curated** | Ad hoc, as bilateral deals/policy events are disclosed | `data/curated/*.csv`, one row per country with `source_name`, `source_url`, `confidence`, `as_of_date`, `rationale` |
| AI investment deals, compute-capacity deals | **Manually curated**, long-format (one row per deal) | Ad hoc | `data/curated/ai_investment_deals.csv`, `data/curated/compute_capacity_deals.csv` |

**The manually curated layer is never touched by the scheduled GitHub Actions refresh.** Only
`data/worldbank/` and the recomputed `data/computed/composite_scores.csv` are auto-committed. Updating a
curated figure is a deliberate, sourced edit to a CSV row -- exactly the distinction the project brief asked
for between "automatable" and "requires manual research/curation."

### Non-oil diversification: a documented proxy, not a literal figure

The World Bank does not cleanly expose "non-oil share of GDP" as a single indicator across all 8 countries.
This tracker uses **`100 - Oil rents (% of GDP)`** (`NY.GDP.PETR.RT.ZS`) as a standard analyst proxy (the
same approximation used in IMF Article IV coverage of GCC economies) -- it is *not* a literal non-oil GDP
share, and is labeled as a proxy everywhere it appears in the app and the data files.

### Investment figures: disclosed commitments only, never aspirational headlines

Every investment figure that feeds the score is a specific, dated, sourced deal. Headline ambition figures
(Saudi Arabia's "$100bn AI company," the UAE's globally-anchored $100bn MGX/Microsoft/BlackRock/GIP fund,
outbound portfolio stakes like MGX's OpenAI equity or QIA's Anthropic/Databricks/Cresta stakes) are recorded
in `data/curated/ai_investment_deals.csv` with `counted_in_score = FALSE` and a note explaining why --
visible for context, excluded from the number, so ambition is never silently counted as commitment.

## Repository structure

```
app.py                              # Streamlit entry point (Overview: index, map, ranking)
pages/
  1_Country_Comparison.py           # Radar + bar comparison across all 6 factors
  2_Country_Deep_Dive.py            # Per-country auto-generated brief + timelines + PDF export
  3_Policy_Event_Tracker.py         # Chronological, sourced feed of chip-policy events
  4_Scenario_Explorer.py            # Live reweighting of the methodology (never touches curated data)
  5_Methodology.py                  # In-app weights/rubrics/limitations reference (mirrors this README)
src/
  constants.py                      # Country list, ISO3 codes, World Bank indicator codes
  scoring.py                        # Composite scoring -- the methodology above, in code
  mapping.py                        # Custom choropleth renderer (see note below)
  country_brief.py                  # Templates a BLUF + key-judgments brief from cited data (no LLM call)
  pdf_export.py                     # Renders a CountryBrief to PDF via reportlab (pure Python)
  ui.py                             # Shared theme CSS, KPI cards, confidence pills, footer (see note below)
  data_pipeline/fetch_worldbank.py  # The one automated data pipeline
data/
  curated/                          # Manually researched, cited, dated
    policy_events.csv               # The Policy Event Tracker's sourced event record
  worldbank/                        # Auto-refreshed by GitHub Actions
  computed/                         # Recomputed composite_scores.csv
  geo/region_countries.geojson      # Bundled country boundaries: 8 tracked + 9 regional-context (see note below)
briefs/
  gulf-ai-ambitions-and-geopolitical-risk.md   # Standalone region-wide written analytic brief
  sovereign-debt-and-political-instability.md  # Case-study brief (Pakistan/Sri Lanka/Bangladesh), MENASA-linked
  mena-geopolitical-risk-brief-issue-01.md     # Monthly digest series, Issue No. 1, MENASA-linked
.streamlit/config.toml              # Custom theme -- paper/ink palette shared with the briefs
tests/                              # pytest suite -- see "Running tests" below
.github/workflows/refresh_worldbank_data.yml
.github/workflows/test.yml
render.yaml                         # Render deployment config
```

### The per-country brief is templated, not free-generated

`src/country_brief.py` builds each country's Bottom-Line-Up-Front and Key Judgments by filling sentence
templates with values pulled directly from `data/curated/*.csv` and the computed scores -- there is no LLM
call at runtime, and no free-form text generation. This means the brief is deterministic (same data always
produces the same brief), stays in sync automatically when a curated figure is corrected or updated, and
every sentence is traceable to a specific cited row. Confidence tags on each judgment are pulled straight
from that row's `confidence` column rather than invented separately. `src/pdf_export.py` renders the same
`CountryBrief` object to a downloadable PDF via `reportlab` (pure Python, no system dependencies, so it
works on Render's free tier without extra build steps).

### Why a custom choropleth renderer instead of `plotly.express.choropleth`

Plotly's built-in geo trace fetches its world-atlas topojson from `cdn.plot.ly` at render time -- even when
a custom GeoJSON is supplied and the base map is set invisible, in the Plotly.js version this project runs
against. That's an external runtime dependency this project deliberately avoids, for the same reason the
brief ruled out ArcGIS: it should run on Render with no external auth or network dependency it doesn't
control. `src/mapping.py` renders the choropleth as filled `go.Scatter` polygons directly from the bundled
`data/geo/region_countries.geojson` (sourced from the `datasets/geo-countries` public-domain Natural Earth
derivative) -- zero runtime network calls, verified in a fully network-restricted sandbox during
development.

The bundled GeoJSON carries 17 countries, not just the 8 this index scores: Iran, Iraq, Syria, Jordan,
Lebanon, Israel, Yemen, Egypt, and Afghanistan are included purely as unscored geographic context (rendered
in a muted, unbordered gray, with a hover label that says explicitly they aren't tracked), so the Overview
map reads as a contiguous regional map instead of three disconnected landmasses (Turkey / the Gulf
peninsula / Pakistan) floating in empty space. `build_choropleth_figure()`'s `context_ids` parameter is
what distinguishes "not tracked at all" (light, unbordered gray) from "tracked but the data was too thin to
score" (the darker, bordered gray used for a real data gap among the 8 scored countries) -- the map
shouldn't make those two very different situations look the same.

### Visual design: matching the standalone briefs, not default Streamlit

`.streamlit/config.toml` sets a custom theme (warm paper background, `#2454a6` blue accent, `Source Serif 4`
headings, `Public Sans` body, `IBM Plex Mono` code) -- the same palette and type system used in the three
standalone briefs in `briefs/`, so the dashboard and the briefs read as one portfolio rather than two
disconnected projects with different default styling. `src/ui.py` centralizes the rest: it hides Streamlit's
default hamburger menu/footer/"Made with Streamlit" badge, and provides `kpi_card()`/`kpi_row()` for the
Overview page's metric cards, `confidence_pill()` for color-coded (not plain-emoji) confidence badges, and a
consistent `footer()` every page calls at the bottom. This exists because the underlying analysis and default
Streamlit chrome were, before this pass, visually indistinguishable from an unstyled homework submission --
see PROGRESS.md for the before/after reasoning.

## Running locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

To refresh the World Bank layer and recompute scores:

```bash
python src/data_pipeline/fetch_worldbank.py
PYTHONPATH=src python src/scoring.py
```

### Running tests

```bash
pip install -r requirements-dev.txt
python -m pytest tests/ -v
```

`tests/` covers the scoring methodology (normalization bounds, the missing-data-as-NaN-not-zero rule, the
Net Alignment formula, weight renormalization when a factor is unavailable) and the country-brief generator
(every country produces a valid brief; a country with no scored deals gets an explicit "Data gap" judgment,
never a silently wrong number). Runs automatically on every push via `.github/workflows/test.yml`, and as a
gate before the scheduled World Bank refresh commits anything (`.github/workflows/refresh_worldbank_data.yml`)
-- a broken data change should fail CI before it reaches `main`, not get auto-committed by the weekly job.

## Known limitations

- **China Exposure Depth is a single-factor axis.** It currently rests entirely on Chinese tech
  penetration (Huawei). A stronger version would add a second, independent China-tie factor (e.g.
  disclosed Chinese AI model deployments, BRI/CPEC-style financing tied to digital infrastructure) if and
  when that data becomes available with the same sourcing bar as the rest of this project.
- **A dedicated follow-up research pass closed some, not all, of the original `Low`-confidence gaps.**
  Turkey's governance-maturity score and Saudi Arabia's Chinese-tech-penetration score were upgraded to
  `Medium` confidence with fresh, country-specific 2025/2026 sources. Bahrain's Chinese-tech-penetration
  score was corrected (down from 3 to 2) once a Bahrain-specific source showed its current 5G vendor is
  Ericsson, with Huawei only in early-stage 6G talks -- a case of better sourcing changing the actual score,
  not just the confidence label. **Qatar, Bahrain, Kuwait, and Oman's export-control tier remains `Low`
  confidence** -- a follow-up attempt to check BIS's own Country Group table directly (`bis.gov`,
  `beta.bis.gov`) was blocked by this session's network policy (`EGRESS_BLOCKED`), not resolved either way.
  The working inference (documented in each row's rationale) is that these four most likely remain in the
  same Country Group D:3/D:4 bucket the UAE was confirmed removed from in July 2026, but this is not
  independently verified. Turkey's export-control tier is likewise still `Low` confidence. See the
  `confidence` and `rationale` columns in `data/curated/*.csv` for the current state of every row.
- **Investment and compute figures are undercounts, by design.** Only deals this research could attribute
  to a specific country with a specific dollar/MW figure and a citable source are scored. Qatar, Bahrain,
  Kuwait, Oman, Pakistan, and Turkey show `N/A` on these two factors not because nothing is happening, but
  because nothing at this level of specificity was found in this research pass -- see the `not_found` rows
  in `data/curated/ai_investment_deals.csv` and `compute_capacity_deals.csv` for exactly what was checked.
- **This is a fast-moving policy space.** The two BIS decisions this index's export-control tier is built
  around (UAE, Saudi Arabia) are both less than a year old at time of writing (Sept 2026), and the framework
  itself only stabilized after the AI Diffusion Rule's rescission in May 2025. Treat the export-control
  tier and the Policy Event Tracker (Phase 2) as the two most time-sensitive parts of this project.
- **The choropleth's bundled GeoJSON uses simplified public-domain boundaries.** Fine for this project's
  purpose (color-by-country at a regional zoom level); not suitable for any use requiring precise or
  politically sensitive boundary accuracy.

## Roadmap

See [`PROGRESS.md`](PROGRESS.md) for full detail. All four phases from the original brief are built:

- **Phase 1:** Composite index, choropleth, radar/bar comparison. ✅
- **Phase 3:** Country deep-dive pages -- auto-generated brief, investment/compute timelines, downloadable
  PDF brief. ✅ (built ahead of Phase 2 -- see `PROGRESS.md` for why)
- **Phase 2:** Policy Event Tracker tab -- a chronological, sourced feed of 8 chip-policy events (the AI
  Diffusion Rule's issuance and rescission, the Chip Security Act's introduction and committee markup, the
  Nov 2025 Saudi/UAE chip authorizations, the March 2026 smuggling indictments, the UAE's July 2026 Country
  Group upgrade). ✅
- **Phase 4:** Scenario Explorer -- live reweighting of the US Integration Depth sub-weights and the
  US-vs-China axis balance, with 5 named presets each carrying a stated analytical rationale (mirrors the
  MENASA Risk Monitor's own Scenario Explorer). Operates purely on `build_composite()`'s in-memory output;
  never writes to `data/curated/*.csv`. ✅

### How the Scenario Explorer stays honest

`src/scoring.py`'s `build_composite()` takes optional weight-override parameters (`tier_weight`,
`investment_weight`, `compute_weight`, `axis_balance`), all defaulting to the exact values used everywhere
else in this tracker -- calling it with no arguments is guaranteed identical to the scored methodology
(covered by a dedicated test). The Scenario Explorer page is the only caller that ever passes overrides.
Presets are named, dated design choices with a stated rationale shown inline (e.g. "Export-control-centric"
weights BIS status at 70% because an analyst might treat the regulatory label as stickier than capital
commitments) -- not arbitrary slider positions, and never a claim that any one configuration is more
"correct" than the scored default.
