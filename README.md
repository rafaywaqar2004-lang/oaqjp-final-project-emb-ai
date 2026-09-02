# Gulf AI & Tech-Bloc Alignment Tracker

A companion piece to the [MENASA Risk Monitor](#): tracks how Gulf states -- plus a wider set of 11
non-Gulf regional states and comparators -- are navigating the US-China AI/chip competition, and what that
means for regional stability and Western strategic interests. Started as an 8-country Gulf-focused tracker
and later grew to 17 countries so the Overview map's neighboring states, originally shown only as unscored
gray context, are properly scored too -- see "Country set" below for exactly which countries were added
when and why.

**Status: all four phases built** -- composite index, choropleth map, radar/bar comparison view, a
chronological sourced feed of chip-policy events, per-country deep-dive pages with an auto-generated
analyst brief and downloadable PDF, and a live scenario-reweighting explorer.
This repo's `briefs/` folder holds this project's own written analytic companion piece:
[`gulf-ai-ambitions-and-geopolitical-risk.md`](briefs/gulf-ai-ambitions-and-geopolitical-risk.md). Two other
briefs were drafted here early on but are grounded in the *MENASA Risk Monitor's* data, not this tracker's
-- they've since moved to that project's own repo
([`rafaywaqar2004-lang/overeign-risk-index`](https://github.com/rafaywaqar2004-lang/overeign-risk-index)),
where they now actually belong; see `PROGRESS.md` for the history.
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
**Original non-Gulf comparators (2):** Pakistan, Turkey -- both navigating similar US/China balancing acts
on a smaller scale (Pakistan via CPEC/Huawei telecom integration alongside a new, cabinet-approved National
AI Policy; Turkey via a decades-long Huawei/Turkcell partnership alongside NATO membership and the 2020
CAATSA sanctions precedent over its S-400 purchase from Russia).
**Regional (9), added later:** Israel, Egypt, Jordan, Iraq, Lebanon, Syria, Iran, Yemen, Afghanistan.

### Why the regional 9 were added

The Overview map's GeoJSON originally held only the 8 tracked countries, so Turkey, the Gulf peninsula, and
Pakistan rendered as three disconnected landmasses on the map with the space between them -- Iran, Iraq,
Syria, etc. -- left empty. A first fix added those 9 countries to the map as unscored gray "geographic
context only" filler, purely so the map read as one contiguous region. The project owner's direct follow-up
("include data for all those countries as well") turned that filler into 9 more fully scored countries,
researched and cited to the same standard as the original 8 -- not a cosmetic map fix, an actual expansion
of what this tracker measures. Every one of the 9 new countries' rows in `data/curated/*.csv` carries the
same dated source, confidence tag (High/Medium/Low), and rationale format as the original 8; nothing was
estimated or invented, and several sub-factors are honestly marked `not_found`/`N/A` where no qualifying
disclosed figure exists (exactly the discipline the original 8 already applied to Qatar/Bahrain/Kuwait/
Oman's thin investment and compute data).

This changes what "Gulf AI & Tech-Bloc Alignment Tracker" measures in practice: it is now a wider
Middle-East/South-Asia tracker with a Gulf core, not a Gulf-only tool. The name and portfolio branding were
kept as-is (this is a live, linked, shared project) rather than renamed mid-stream -- worth knowing if a
reader expects "Gulf" to mean strictly the 6 GCC states.

Two of the 9 needed real judgment calls worth flagging explicitly:
- **Israel** scores the highest Net Alignment in the whole set (US Integration Depth from a Dec 2025 "Pax
  Silica" multilateral chip-supply declaration and zero Chinese telecom-vendor presence -- Huawei/ZTE were
  structurally excluded from Israel's core networks under direct US pressure in 2019), which is a genuinely
  different profile from every Gulf state in this dataset and worth sanity-checking against the Country
  Comparison page's raw factor table before citing.
- **Syria** required reading a live, two-sided 2025-2026 sanctions picture rather than assuming its
  pre-Assad-fall comprehensive-embargo status still holds: most Syria sanctions were lifted in 2025 (EO
  14312, OFAC delisting, Caesar Act repeal), but BIS guidance dated 31 May 2026 explicitly confirmed the
  advanced-computing/AI-chip license requirement (Country Group D:5) remains in force regardless -- so
  Syria still scores a 0 on export-control tier specifically, not because the research is stale, but because
  that particular restriction did not move even as the broader sanctions regime did.

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

2. **China Exposure Depth** (0-100) -- a weighted average of two independent factors:
   - **Chinese telecom penetration** (0-5 ordinal, curated; Huawei/ZTE's core telecom/RAN footprint) -- weight 0.50
   - **Chinese AI/cloud/digital-infrastructure ties** (0-5 ordinal, curated; Chinese cloud regions, AI-model
     deployments, and China-linked financing of digital infrastructure) -- weight 0.50

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

### Why 7 factors, not 8-10

The original brief allowed 6-8 factors. Research (documented per-country in `data/curated/*.csv`) confirmed
6 of the brief's original factors are sourceable for at least the Gulf's two AI leaders, but data depth
drops off sharply for Qatar, Bahrain, Kuwait, Oman, Pakistan, and Turkey -- a methodologically sound 6-factor
index beat padding to 8 with factors that would be mostly `N/A` outside Saudi Arabia and the UAE. A 7th
factor -- **Chinese AI/cloud/digital-infrastructure ties** -- was added in a dedicated research pass across
all 17 tracked countries once China Exposure Depth's single-factor limitation (see the original "Known
limitations" note in earlier revisions of this README) had a data source that met the same sourcing bar as
the rest of this project: a specific, dated, cited rubric row per country, never an inferred or aggregated
score.

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

The **US export-control access tier**, **Chinese telecom penetration**, and **Chinese AI/cloud/digital
ties** factors are scored on a documented 0-5 rubric rather than a single clean public number, because none
exists at this granularity. This is a deliberate, disclosed methodology choice (an analyst-desk judgment
call, same as a country-risk analyst would make), not an attempt to disguise a soft estimate as a hard
figure. The full rubric, the specific source(s) behind every country's score, and a `confidence` rating
(High/Medium/Low) are all in `data/curated/export_control_tier.csv`, `data/curated/chinese_tech_penetration.csv`,
and `data/curated/chinese_digital_ties.csv`. **Several `Low` confidence entries are explicitly flagged for
follow-up research** -- see [Known limitations](#known-limitations).

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

#### Chinese telecom penetration rubric

| Score | Meaning |
|---|---|
| 0 | No significant Chinese ICT vendor presence |
| 1 | Minimal, isolated non-core relationships |
| 2 | Moderate -- a few Huawei contracts, non-core |
| 3 | Significant -- Huawei is a major/core RAN vendor for at least one major carrier |
| 4 | Deep -- Huawei core RAN across multiple major carriers, plus cloud/enterprise expansion |
| 5 | Extensive -- Huawei is the leading/sole 5G vendor across all major carriers, plus deep economic ties |

#### Chinese AI/cloud/digital-infrastructure ties rubric

| Score | Meaning |
|---|---|
| 0 | No disclosed Chinese AI/cloud infrastructure presence or financing found |
| 1 | Minimal -- an isolated MOU, marketing presence, or announcement, with no confirmed active deployment or financing |
| 2 | Moderate -- an actively marketed/launched Chinese cloud service, but no AI-model deployment and no digital-infrastructure financing |
| 3 | Significant -- confirmed active Chinese AI-model deployment OR confirmed Chinese financing of digital infrastructure (not both) |
| 4 | Deep -- confirmed active Chinese AI-model/cloud deployment AND confirmed Chinese financing of digital infrastructure |
| 5 | Extensive -- primary/state-level Chinese digital backbone plus multiple, distinct financing ties |

This factor was added in a dedicated research pass across all 17 tracked countries (three parallel research
sweeps, one per country subset) specifically to close China Exposure Depth's original single-factor
limitation. It deliberately measures something telecom penetration doesn't: AI-model deployment and cloud
partnerships, which sit closer to the AI stack than legacy 5G/fiber vendor choice and can move independently
of it -- e.g. Saudi Arabia's digital-ties score (4/5, "Deep") exceeds its telecom-penetration score (3/5,
"Significant"), while Iraq shows the reverse (telecom 4/5 vs. digital ties 1/5). One candidate source
surfaced during this research (a specific-dollar-figure Egypt financing claim from a low-credibility outlet)
was deliberately excluded for carrying hallmarks of a fabricated financial press release -- Egypt's digital-
ties score instead reflects the mainstream-reported, still-unresolved Huawei/iFlytek AI-data-center bid.

## Data sources

| Layer | Type | Refresh cadence | Where |
|---|---|---|---|
| Non-oil diversification proxy, FDI net inflows | **Live, automated** | Weekly (GitHub Actions, Mondays) | World Bank API v2, `src/data_pipeline/fetch_worldbank.py` → `data/worldbank/` |
| US export-control tier, Chinese telecom penetration, Chinese AI/cloud/digital ties, AI governance maturity | **Manually curated** | Ad hoc, as bilateral deals/policy events are disclosed | `data/curated/*.csv`, one row per country with `source_name`, `source_url`, `confidence`, `as_of_date`, `rationale` |
| AI investment deals, compute-capacity deals | **Manually curated**, long-format (one row per deal) | Ad hoc | `data/curated/ai_investment_deals.csv`, `data/curated/compute_capacity_deals.csv` |
| Map reference layers: major cities, named AI/compute hub sites | **Manually curated** (map display only, not scored) | Ad hoc | `data/curated/major_cities.csv`, `data/curated/ai_hubs.csv` |

**The manually curated layer is never touched by the scheduled GitHub Actions refresh.** Only
`data/worldbank/` and the recomputed `data/computed/composite_scores.csv` are auto-committed. Updating a
curated figure is a deliberate, sourced edit to a CSV row -- exactly the distinction the project brief asked
for between "automatable" and "requires manual research/curation."

### Non-oil diversification: a documented proxy, not a literal figure

The World Bank does not cleanly expose "non-oil share of GDP" as a single indicator across all countries in this set.
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
app.py                              # Thin router: grouped st.navigation() only, no page content
app_pages/
  regional_dashboard.py             # Flagship page: key findings, KPIs, US-China scatterplot, map, ranking, watch next, executive PDF
  country_comparison.py             # Radar + bar comparison across all 6 scored factors
  country_deep_dive.py              # Country intelligence profile: drivers, trend, what changed, implications, watch, full PDF export
  policy_events.py                  # Chronological, sourced feed of chip-policy events + direction + model-impact links
  scenario_lab.py                   # Live reweighting (incl. China Exposure sub-weights) + robustness / rank-stability analysis
  strategic_risk.py                 # Regional risk matrix (4 dimensions) + per-country transmission-channel implications
  outlook.py                        # 12-Month Outlook: Base Case / Alternative Case, analyst-judgment probability bands
  methodology.py                    # In-app weights/rubrics/limitations reference (mirrors this README)
  economic_analysis.py              # The one serious empirical economic-analysis module (QUESTION/DATA/.../LIMITATION)
  sources_data.py                   # Research data catalog -- every dataset, computed live, with CSV downloads
src/
  constants.py                      # Country list, ISO3 codes, World Bank indicator codes
  scoring.py                        # Composite scoring -- the methodology above, in code
  momentum.py                       # Score Momentum -- honest "Insufficient data" until >=2 dated snapshots exist
  watch_next.py                     # Loads/filters data/curated/watch_indicators.csv for the Watch Next component
  economic_analysis_engine.py       # Correlation logic backing the Economic Analysis page (no regression fit)
  strategic_risk_engine.py          # The 4-dimension risk-rating logic backing the Strategic Risk page
  outlook_engine.py                 # Base Case / Alternative Case construction backing the 12-Month Outlook page
  data_catalog.py                   # Builds the Sources & Data page's dataset registry from the actual files
  data_validation.py                # Structural sanity checks (duplicates, out-of-range scores, malformed dates, ...)
  mapping.py                        # Custom choropleth renderer (see note below)
  country_brief.py                  # Templates a BLUF + key-judgments brief from cited data (no LLM call)
  pdf_export.py                     # Renders a country brief AND the regional executive assessment to PDF via reportlab
  ui.py                             # Design tokens, page header, KPI/evidence/key-findings/watch cards, chart-color tokens, footer
  data_pipeline/fetch_worldbank.py  # The one automated data pipeline
data/
  curated/                          # Manually researched, cited, dated
    policy_events.csv               # The Policy Event Tracker's sourced event record (incl. direction column)
    major_cities.csv                # Map reference layer: one city per country, geographic orientation only
    ai_hubs.csv                     # Map reference layer: named, cited AI/compute/telecom infrastructure sites
    watch_indicators.csv            # Watch Next's leading indicators, each tied to an already-cited data point
    non_oil_diversification.csv     # Manually researched non-oil GDP share (8 countries; 9 marked not-applicable)
  worldbank/                        # Auto-refreshed by GitHub Actions
  computed/                         # Recomputed composite_scores.csv
  geo/region_countries.geojson      # Bundled country boundaries for all 17 tracked countries (see note below)
briefs/
  gulf-ai-ambitions-and-geopolitical-risk.md   # Standalone region-wide written analytic brief
.streamlit/config.toml              # Custom theme + static-serving config -- paper/ink palette shared with the briefs
assets/favicon.png                  # Generated browser-tab icon (page_icon on every page)
static/og-image.png                 # Generated link-preview card image (see note below)
patch_og_tags.py                    # Patches GA/OG tags/cold-start loader into Streamlit's shell (see note below)
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

The bundled GeoJSON carries all 17 tracked countries -- Iran, Iraq, Syria, Jordan, Lebanon, Israel, Yemen,
Egypt, and Afghanistan were added specifically so the Overview map read as a contiguous regional map instead
of three disconnected landmasses (Turkey / the Gulf peninsula / Pakistan) floating in empty space, and were
then researched and scored rather than left as gray filler (see "Country set" above). `build_choropleth_
figure()` still has a `context_ids` parameter, which currently renders nothing (every bundled country is
scored) -- kept for the same reason: if a future country is added to the map's geometry before it's
researched, this is what distinguishes "not tracked at all" (light, unbordered gray) from "tracked but the
data was too thin to score" (the darker, bordered gray still used if any of the 17 develops a real data
gap) -- two different situations the map shouldn't make look the same.

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

### Traffic analytics, link previews, and the cold-start loader

Streamlit is a client-rendered single-page app with no `<head>` a running script can reach, so a normal
`st.markdown` GA/OG snippet gets sandboxed in an iframe and never fires a real pageview or shows up to a
link-preview crawler (LinkedIn, Slack, iMessage -- none of which execute JS). `patch_og_tags.py` patches
Streamlit's own shipped `index.html` directly as a Render build step, right after `pip install` -- the same
technique already proven in the companion MENASA Risk Monitor's own `patch_og_tags.py`. One script now
handles three things:

1. **Google Analytics.** Reuses MENASA's GA4 property (`G-QP9RPS41KJ`) rather than standing up a separate
   one, so this tracker's traffic reports alongside the portfolio's and MENASA's in one place.
2. **Open Graph / Twitter Card tags**, so sharing the link actually renders a preview card -- title,
   description, and `static/og-image.png` (a generated 1200x630 card in the app's own paper/ink palette,
   served at `/app/static/og-image.png` via `[server] enableStaticServing = true` in `.streamlit/config.toml`).
3. **A branded cold-start loading screen.** Render's free tier spins the service down after a few idle
   minutes; the first visitor after a quiet spell hits a genuine ~20-30s wait while Streamlit's JS bundle
   loads, connects its websocket, and runs the script -- during which the browser would otherwise show a
   blank page. This static (no-JS-bundle-required) block renders instantly and removes itself once
   `[data-testid="stAppViewContainer"]` actually has content, so the wait reads as "loading," not "broken."

`assets/favicon.png` (also a generated image, a simple blue/red split circle in the same palette) is set as
`page_icon` on every page -- Streamlit accepts a local image path there, not just an emoji, and MENASA
already establishes this as the pattern for a real browser-tab icon rather than a generic emoji every other
Streamlit app on Render shares. Wired into `render.yaml`'s `buildCommand` and a `SITE_URL` env var; nothing
to configure locally (`streamlit run app.py` skips the patch entirely, which only matters for the deployed
site -- link previews and the cold-start loader are meaningless when running locally with no cold start).

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

- **China Exposure Depth's second factor (Chinese AI/cloud/digital ties) is a newer, thinner research
  pass than the telecom-penetration factor it complements.** All 17 countries have a scored row with a
  cited source and rationale, but several rest on a single MOU, marketing announcement, or a cloud
  service's public launch rather than a confirmed, audited deployment figure -- Bahrain, Jordan, and Iraq
  are explicitly `Low` confidence for exactly this reason. Treat this factor as directionally sound but
  less battle-tested than the telecom factor it's averaged with.
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
- **The 9 regional countries added later inherit the same `bis.gov`/primary-source access gap.** The
  research session that added Israel, Egypt, Jordan, Iraq, Lebanon, Syria, Iran, Yemen, and Afghanistan
  hit the identical `EGRESS_BLOCKED` wall on `bis.gov`, the Federal Register, and several law-firm client-
  alert domains, and relied on WebSearch-synthesized secondary reporting instead -- every one of those nine
  countries' export-control-tier rows is marked `Medium` or `Low` confidence for exactly this reason, never
  silently upgraded to `High`. Two specific judgment calls are worth a reader's attention: **Israel**'s
  export-control tier (4/5) rests on a single Israeli outlet's characterization of the Dec 2025 "Pax Silica"
  declaration, not a confirmed BIS regulatory text change; **Syria**'s tier (0/5) required reconciling a
  major 2025 sanctions-relief wave with a BIS guidance document (dated 31 May 2026) that separately confirms
  the advanced-computing license requirement specifically was *not* relaxed -- both rows' `rationale` columns
  spell out the reasoning in full. **Egypt is a live, unresolved situation as of this dataset's research
  date**: a Huawei bid to build Egypt's national AI data center and a competing US-backed counter-offer were
  both still pending as of Xi Jinping's Sept 2026 Cairo visit, so Egypt's China-exposure and export-control
  scores are the single most likely to move in this dataset's next research pass.
- **Investment and compute figures are undercounts, by design.** Only deals this research could attribute
  to a specific country with a specific dollar/MW figure and a citable source are scored. Afghanistan,
  Bahrain, Iran, Kuwait, Oman, Pakistan, Qatar, Turkey, and Yemen show `N/A` on these two factors not
  because nothing is happening, but because nothing at this level of specificity was found in this research
  pass -- see the `not_found` rows in `data/curated/ai_investment_deals.csv` and `compute_capacity_deals.csv`
  for exactly what was checked.
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
- **Phase 4:** Scenario Lab (originally "Scenario Explorer," renamed for consistency with the wider
  redesign -- see PROGRESS.md) -- live reweighting of the US Integration Depth sub-weights, the China
  Exposure Depth sub-weights (telecom penetration vs. AI/cloud/digital ties), and the US-vs-China axis
  balance, with 7 named presets each carrying a stated analytical rationale (mirrors the MENASA Risk
  Monitor's own Scenario Explorer); a templated (not free-generated) plain-language interpretation of each
  scenario's effect on the ranking; a Normalization Sensitivity section that recomputes the ranking against
  alternative, equally-defensible investment/compute ceilings so a reader can check whether the ranking
  depends on that judgment call; and a Model Robustness / Rank Stability analysis that samples many weight
  configurations (across all five reweightable sub-weights) and reports how much each country's rank
  actually moves. Operates purely on `build_composite()`'s in-memory output; never writes to
  `data/curated/*.csv`. ✅
- **Overview map gained a metric selector** -- it originally only rendered Net Alignment Score; it now
  switches between Net Alignment, US Integration Depth, China Exposure Depth, Chinese Telecom Penetration,
  Chinese AI/Cloud/Digital Ties, disclosed AI Investment, disclosed Compute Capacity, and AI Governance
  Maturity, each with its own color scale and colorbar label.
- **Overview map gained two optional marker layers, both toggleable and on by default:**
  - **Major cities** (`data/curated/major_cities.csv`) -- one reference dot per tracked country, for
    geographic orientation. Deliberately framed as "major city," never "capital," to sidestep disputed
    political-status questions: Israel is labeled with Tel Aviv (its tech/financial hub) rather than the
    internationally disputed designation of Jerusalem, and Yemen is labeled with Sana'a as the
    constitutional capital, independent of which government currently controls it.
  - **AI / compute hubs** (`data/curated/ai_hubs.csv`) -- 9 specific, named infrastructure sites (NEOM;
    Ashdod, Mevo Carmel, and Kiryat Tivon in Israel; Cairo/Maadi Technology Park; Baghdad; the Al-Risha gas
    field in eastern Jordan; Tartus, Syria; and Istanbul), each geocoded from a site name **already
    explicitly named** in this project's existing sourced deal data (`ai_investment_deals.csv`,
    `compute_capacity_deals.csv`, or `chinese_digital_ties.csv`'s rationale) -- never inferred from a
    company's headquarters or an announcement venue. Hovering a star shows the deal, its scale, and its
    source. Jordan's marker is explicitly flagged as an approximate regional location, not a precise site
    coordinate, since only the gas field's general area (not exact coordinates) is disclosed in reporting.
- **China Exposure Depth gained a second factor** -- Chinese AI/cloud/digital-infrastructure ties, scored
  0-5 and blended 50/50 with the existing telecom-penetration factor via the same renormalizing
  weighted-average pattern already used for US Integration Depth. Closes the project's longest-standing
  documented methodology limitation (a single-factor China axis). See the Methodology section above for
  the rubric and the research notes on specific country judgment calls.
- **Executive Key Findings, Score Momentum, Watch Next, and a rebuilt Country Deep Dive** (a "credibility
  upgrade" pass): the Overview's bottom-line callout became a 4-part KEY FINDINGS card (Bottom Line / Key
  Judgment / Confidence / Why It Matters, all computed from live data -- `ui.key_findings_card()`); a new
  `src/momentum.py` module computes Score Momentum from `composite_scores_history.csv`, correctly returning
  `Insufficient data` while only one dated snapshot exists rather than fabricating a trend, and is wired
  into both the Overview and Country Deep Dive; a new reusable `Watch Next` component
  (`data/curated/watch_indicators.csv`, 6 leading indicators, each tied to a specific already-cited
  pending/target/unresolved item elsewhere in the curated data -- e.g. Egypt's unresolved Huawei/iFlytek AI
  data-center bid, Jordan's not-yet-built Al-Risha 400MW target) appears on the Overview and every Country
  Deep Dive; and Country Deep Dive was restructured into a full intelligence-profile hierarchy (Current
  Position, Key Judgments, Key Drivers factor table, Trend, What Changed, Strategic Implications for
  policymakers/investors/corporates, What to Watch, Data Quality, Sources). The Policy Event Tracker gained
  country and date-range filters plus a `direction` classification (Loosening/Tightening, analyst judgment
  applied to each event's already-cited, already-summarized effect -- never a numeric score fabrication) on
  every event card. See PROGRESS.md for the full scope decision (a prioritized subset of a much larger
  brief) and what was deliberately not built this round.
- **Economic Analysis page and Sources & Data catalog** (Tiers 2-3 of the same credibility-upgrade brief):
  a new `src/economic_analysis_engine.py` module reports this tracker's one serious empirical finding -- AI
  governance maturity is moderately-to-strongly associated with US export-control tier (Pearson r=0.68,
  full 17-country sample, robust to excluding either the highest-scoring or floor-sharing countries),
  reported as descriptive correlation rather than a fitted regression, with an explicit
  association-not-causation discussion of three distinct plausible causal stories. A candidate-relationships
  table documents what was considered and rejected for sample size (investment/compute correlations only
  have 4-6 of 17 countries with both figures). A supplementary finding uses a new manually-researched
  dataset, `data/curated/non_oil_diversification.csv` (real IMF/national-statistics-sourced non-oil GDP
  share figures for 8 countries, gathered specifically because this project's live World Bank pipeline is
  unpopulated in its development sandbox -- the other 9 countries are correctly marked structurally
  not-applicable rather than estimated), finding a moderate negative association between diversification and
  China Exposure Depth (r=-0.50, n=8, explicitly flagged as exploratory given the small sample). A new
  Sources & Data page (`src/data_catalog.py`) catalogs every dataset this tracker uses -- source type,
  country coverage, observation count, missingness, methodology, and limitations, all computed live from
  the actual files rather than typed in by hand -- with a direct CSV download button per dataset.
- **Strategic Risk, 12-Month Outlook, data validation, chart-color centralization, and a fuller PDF export**
  (the remaining Tiers 3-5 of the same brief): a new Strategic Risk page rates every country on 4 dimensions
  derived transparently from already-scored data (US Policy Exposure from export-control tier, China
  Exposure directly, Infrastructure Execution Risk from the share of counted compute capacity still under
  development, Measurement Confidence Risk from this project's own curated `confidence` columns) -- two
  dimensions the brief named ("semiconductor dependency," "geopolitical volatility") are explicitly *not*
  rated per-country, since the first would just restate the other two axes and the second would require a
  political judgment this project's data doesn't support. A new 12-Month Outlook page reports a Base Case
  and Alternative Case per country, built entirely from Watch Next's own indicators, with every probability
  an explicit qualitative band (Likely/Possible/Unlikely/N/A) rather than a fabricated percentage, and every
  section labeled ANALYST JUDGMENT vs. the one real MODEL OUTPUT (the current score). A new
  `src/data_validation.py` runs structural checks (duplicate countries, out-of-range scores, malformed
  dates, mismatched ISO3 codes, negative dollar/MW figures, invalid weight sums) against the actual
  repository data on every test run. Chart colors were centralized into `ui.py` (`sequential_map_scale()`,
  `NET_ALIGNMENT_DIVERGING_SCALE`, `CHART_BASELINE`/`CHART_SCENARIO`) -- catching and fixing a real
  inconsistency where the Scenario Lab's "scenario" bar used a blue almost identical to the US Integration
  semantic color instead of the brief's own "scenario = navy" convention. `src/pdf_export.py`'s
  `build_country_pdf()` gained optional Current Position / Key Drivers / Recent Developments / Strategic
  Implications / What to Watch / Data Quality sections (still works with just a brief, for backward
  compatibility), and a new `build_executive_pdf()` renders the regional Key Findings, Country Rankings,
  What Changed, and Strategic Risk matrix into a downloadable executive assessment from the Overview page.

### How the Scenario Lab stays honest

`src/scoring.py`'s `build_composite()` takes optional weight-override parameters (`tier_weight`,
`investment_weight`, `compute_weight`, `axis_balance`, `china_telecom_weight`, `china_digital_weight`,
`investment_ceiling`, `compute_ceiling`), all defaulting to the exact values used everywhere else in this
tracker -- calling it with no arguments is guaranteed identical to the scored methodology (covered by a
dedicated test). The Scenario Lab page is the only caller that ever passes overrides. Presets are named,
dated design choices with a stated rationale shown inline (e.g. "Export-control-centric" weights BIS status
at 70% because an analyst might treat the regulatory label as stickier than capital commitments) -- not
arbitrary slider positions, and never a claim that any one configuration is more "correct" than the scored
default.
