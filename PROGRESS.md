# Progress Log -- Gulf AI & Tech-Bloc Alignment Tracker

Read this first if picking up the project cold, whether that's a fresh Claude session or the project
owner returning after a break. It's meant to make re-explaining the project unnecessary.

## Where things stand

**Most recent session: fixed a real mobile-navigation bug, then built a new Sanctions & Entity List
Exposure module end to end from the project owner's detailed spec.** Two pieces of work:

1. **Sidebar navigation was completely unreachable on mobile/narrow viewports.** The project owner
   reported "the sidebar which shows the different tabs isn't showing up." Root cause:
   `ui.inject_base_css()` hid the entire `header[data-testid="stHeader"]` element via
   `visibility: hidden` -- but that header is also where Streamlit renders the sidebar's
   expand/collapse toggle button. On desktop this went unnoticed (sidebar starts open), but on any
   narrow viewport Streamlit auto-collapses the sidebar on load, and with the header hidden there was
   no control left to reopen it. Reproduced locally via Playwright at 390px width (confirmed the toggle
   and sidebar were both fully invisible), fixed by keeping the header visible but transparent/borderless
   instead of hiding it outright, verified the fix at both mobile and desktop widths, shipped as its own
   PR (#7) separate from the feature work below.

2. **Sanctions & Entity List Exposure** -- a new module built from a detailed project-owner spec (data
   file schema, page layout, scoring formula, admin data editor, all specified up front). Followed the
   spec closely while applying this project's own no-fabrication discipline to every field: real,
   well-documented facts the owner supplied (Iran's OFAC programs, Turkey's 2020 CAATSA designation) were
   kept as given; every other field was either genuinely researched via `WebSearch` this session or
   explicitly marked `RESEARCH_NEEDED` (the owner's own requested convention) rather than guessed.
   A background research agent confirmed BIS Entity List counts are **not obtainable** for any of the 17
   countries from any source it could find -- not BIS's own site, not the trade.gov Consolidated
   Screening List (both network-blocked in this sandbox anyway) -- because the Entity List has no
   published per-country tally; it's a rolling list built from decades of individual Federal Register
   rules. That field stays `RESEARCH_NEEDED` for all 17 countries rather than estimated. The same pass
   found real, cited OFAC/EU/CAATSA answers for all 17 countries, including some genuinely nuanced ones
   (Egypt's 2019 CAATSA sanctions were *threatened but never imposed* over a Su-35 purchase; Syria's 2025
   sanctions relief left the chip-specific BIS restriction in place while OFAC's own program page is now
   titled "Inactive and Archived"). A real bug was caught and fixed during the build: pandas silently
   reads a bare cell value of exactly `"None"` or `"N/A"` as a missing value (`NaN`) under its default
   `na_values` list -- two countries' `caatsa_status` cells were silently nulled out by this until every
   such cell was reworded to avoid the exact NA-lookalike tokens (`"None on file"` instead of bare
   `"None"`), with a regression test now guarding the whole curated CSV against it recurring. The
   Sanctions Exposure Score itself reuses this project's own already-cited `export_control_tier.csv`
   `tier_score` for the BIS-tier factor rather than re-deriving a fresh judgment call, so the two modules
   can't drift apart on the same underlying facts. 41 new tests (`test_sanctions_engine.py`); 393/393
   passing overall. Verified in-browser via Playwright: the summary table, heatmap, ranked bar chart,
   positioning scatter, and admin `st.data_editor` panel all render without error, and the new Sanctions
   Profile sub-section renders correctly on Country Deep Dive.

**Previous session: closed five self-identified "more detail" gaps -- historical backfill, the BIS
confidence gap, expanded Policy Event Tracker coverage, and more AI/compute hub sites.** Prompted by the
project owner asking what could be made more thorough, then approving all five suggestions at once
("lets do all of these tehn"). All five are real, sourced, tested additions -- nothing here is estimated
or backdated without evidence.

1. **Historical backfill** (`src/historical_backfill.py`, new module, 19 tests). Score Momentum and Trend
   had exactly one dated snapshot since they shipped (`data/computed/composite_scores_history.csv`), so
   every call returned "Insufficient data" by design -- correct, but not useful until a second snapshot
   existed. Rather than waiting months for the daily pipeline to accumulate history, this reconstructs 18
   additional dated snapshots **today, from evidence that already exists in this project's own curated
   data**:
   - AI investment and compute-capacity deals are filtered by their own existing `announced_date` column
     (`ai_investment_deals.csv` / `compute_capacity_deals.csv`) -- a deal simply isn't counted before its
     own disclosed announcement date. Purely mechanical, no judgment calls.
   - Two documented export-control tier step-changes, both already cited in `export_control_tier.csv`'s
     rationale text: Saudi Arabia tier 0->3 on 2025-11-19 (HUMAIN's capped authorization) and the UAE
     tier ->4 on 2026-07-10 (BIS Country Group A:5 upgrade). The UAE's *pre-upgrade* value (2) is an
     explicit **analyst inference** -- the same Country Group D:3/D:4 bucket Qatar/Bahrain are scored in
     today, not a directly sourced historical figure -- flagged via a dedicated `us_tier_inferred` column
     and called out by name everywhere it surfaces.
   - Every other country's tier, and every country's Chinese-tie/governance factors, are held constant at
     today's curated values across all historical dates, because no dated evidence exists for when those
     specific relationships or scores changed. **This is disclosed, not hidden**: a `source` column
     (`"backfilled"` vs. `"live_pipeline"`) now distinguishes reconstructed rows from the real daily
     pipeline snapshot, and Country Deep Dive's new Trend chart (a real Plotly line chart, added because a
     19-point trend line finally exists to draw) carries an explicit caption whenever backfilled rows are
     present in view, plus a matching caption on the Regional Dashboard's regional-trend line.
   - Net effect: Momentum and Trend went from permanently "Insufficient data" to functioning end-to-end --
     verified in-browser (Saudi Arabia's Trend chart now visibly shows the real 2025-05 and 2025-11 US
     Integration Depth jumps against a flat China Exposure Depth line).

2. **BIS confidence-gap closure** (`data/curated/export_control_tier.csv`). Five countries were carrying
   `Low` confidence on their export-control tier because `bis.gov` itself has been unreachable all session
   (`WebFetch` returns `EGRESS_BLOCKED` for every external domain tried this session, not just bis.gov --
   confirmed again this round against `cov.com` and `kpmg.com`). A `WebSearch` query surfaced a real, named
   law-firm export-control alert (Covington & Burling LLP, Oct 2023) explicitly classifying Bahrain,
   Kuwait, Oman, and Qatar under Country Group D:4 -- consistent with, and corroborating, this project's
   existing tier scores for those four countries. Their confidence was raised `Low` -> `Medium` (not
   `High`: this is a secondary-source corroboration, not a primary bis.gov read) with the new citation
   appended to each row's rationale. **Turkey's gap was NOT closed** -- repeated follow-up searches
   targeting Turkey's specific BIS Country Group classification found nothing citable, so it stays `Low`
   confidence with the failed search attempts documented in its rationale rather than guessed at.

3. **Policy Event Tracker expanded 8 -> 16 events** (`data/curated/policy_events.csv`). A background
   research agent, briefed with the exact existing schema and an explicit non-duplication list, sourced 8
   more real, dated, cited chip/AI export-control events spanning Dec 2024-Dec 2025 from BIS, Congress.gov,
   DOJ, and trade-press sources -- including the Dec 2024 BIS semiconductor package that the existing 8
   events' own Jan 2025 AI Diffusion Rule was built on top of, both 2025 GAIN AI Act legislative vehicles,
   and a second DOJ smuggling enforcement action (Operation Gatekeeper, $160m).

4. **AI/compute hub map expanded 9 -> 14 sites, 7 -> 12 countries** (`data/curated/ai_hubs.csv`). A second
   background agent, held to the same "a specific named site in a real citable source, never inferred from
   HQ or capital-city defaults" rule the existing 9 rows already followed, found 5 more real, named sites:
   UAE (Khazna's Masdar City AI-ready data center), Qatar (Microsoft's Doha Azure region), Bahrain (AWS's
   Saar facility), Oman (Equinix/Omantel's Barka interconnection hub), and Pakistan (Huawei-partnered
   Karachi Technopolis). Kuwait, Lebanon, Iran, Yemen, and Afghanistan genuinely turned up no qualifying
   named site and were correctly left uncovered rather than filled in with a guess.

`src/data_validation.py`'s `validate_all()` returns zero issues against the full updated data set. 352/352
tests passing (19 new: `test_historical_backfill.py`). Verified in-browser via Playwright: Country Deep
Dive's new Trend chart, the Regional Dashboard's updated trend caption, and the 16-event Policy Events feed
all render without error.

**Previous session: closed out the "9+/10 credibility upgrade" brief -- Strategic Risk, 12-Month
Outlook, data validation, chart-color centralization, and a fuller PDF export (Tiers 3-5).** This
completes every tier of the brief except a handful of items explicitly judged not defensible without
fabrication (see "Deliberately not built" below) or genuinely out of proportion for a portfolio project
(a full WCAG audit, a from-scratch mobile-first redesign).

1. **Strategic Risk page** (`app_pages/strategic_risk.py` + `src/strategic_risk_engine.py`). Rates all 17
   countries on 4 dimensions, each traced to a specific already-computed number:
   - US Policy Exposure (from `us_tier_raw` -- a country with a broad bilateral arrangement has more to
     lose from a future US policy reversal than one with none)
   - China Exposure (directly, `china_exposure_depth`)
   - Infrastructure Execution Risk (the share of a country's counted compute capacity still
     `under_development`/`target` rather than `disclosed_current` -- UAE's two counted compute deals are
     both 100% not-yet-built, so it correctly rates High; a country with no compute deal on file rates
     Insufficient data, never a guessed Low)
   - Measurement Confidence Risk (the worst confidence rating across a country's tier/china/china_digital
     curated rows -- a risk in the *assessment itself*, not the country's real-world position)

   Two dimensions named in the original brief -- "semiconductor dependency" and "geopolitical volatility" --
   are deliberately **not** rated per-country. The first would just restate US Policy Exposure + China
   Exposure in different words (this tracker's own two axes already measure exactly that). The second would
   require a political judgment this project's curated data doesn't support without guessing -- exposed as
   a limitation on the page itself rather than invented.

2. **12-Month Outlook page** (`app_pages/outlook.py` + `src/outlook_engine.py`). The hardest page to build
   honestly this session, because it's inherently forward-looking and this tracker has zero historical trend
   data to fit anything to. Solution: Base Case ("current position persists, absent a specific disclosed
   pending event") and Alternative Case built *directly from a country's own Watch Next items* -- if none
   exist, the Alternative Case says so explicitly (`probability: "N/A"`) rather than inventing one. Every
   probability is one of 4 fixed qualitative labels (Likely/Possible/Unlikely/N/A) -- covered by a test that
   asserts no digit ever appears in a probability value, since a numeric percentage here would imply a
   precision this project's data cannot support. Every section is explicitly labeled `ANALYST JUDGMENT`; the
   only `MODEL OUTPUT` on the page is the current composite score, labeled as such.

3. **Data validation module** (`src/data_validation.py`, 25 tests). Structural checks -- duplicate
   countries, out-of-range ordinal/composite scores, mismatched ISO3 codes, malformed dates, negative
   dollar/MW figures, unrecognized confidence values, weights that don't sum to 1 -- run against the actual
   repository data on every test run (`test_repository_data_currently_has_no_validation_issues` fails loudly
   if a future edit introduces a real data bug, rather than letting it slip into `main` silently).

4. **Chart-color centralization** (`src/ui.py` gained `sequential_map_scale()`, `NET_ALIGNMENT_DIVERGING_SCALE`,
   `CHART_BASELINE`, `CHART_SCENARIO`, `MAP_NEUTRAL`). This surfaced and fixed a real, pre-existing
   inconsistency: Scenario Lab's "scenario" bar was colored `#2454a6`, nearly identical to `BLUE` (the US
   Integration semantic color, `#2463A5`) -- one digit apart, clearly an unintentional near-duplicate rather
   than a deliberate choice. Per the brief's own explicit convention ("Scenario = navy"), it's now `NAVY`,
   and the baseline bar is now the shared `GRAY` token instead of a one-off `#c3c0b3`. `regional_dashboard.py`'s
   6-entry `MAP_METRICS` dict, which previously repeated the literal `"#f0e6c8"` six times, now calls
   `sequential_map_scale(BLUE)` / `sequential_map_scale(RED)` / etc. `src/mapping.py`'s AI-hub star marker
   color, which duplicated `ui.GREEN`'s hex value as an independent literal, now imports `GREEN` directly --
   removing a second source of truth for the same color.

5. **Fuller PDF export** (`src/pdf_export.py`). `build_country_pdf()` gained optional `current_position`,
   `key_drivers`, `what_changed`, `strategic_implications`, `watch_items`, and `data_quality` parameters --
   each renders a new section if supplied, skipped silently if not, so the original minimal call shape
   (`build_country_pdf(brief)`) still works (a real backward-compatibility concern, not just a style
   choice, since a signature change here could have broken the download button without any test catching
   it -- covered by a dedicated "minimal call" test for all 17 countries). Country Deep Dive's download
   button now passes through everything the page itself already computes. A new `build_executive_pdf()`
   renders a regional report (Executive Summary from Key Findings, Regional Positioning, Country Rankings,
   What Changed, Strategic Risk matrix, Methodology, Sources) from the Overview page -- wrapped in
   `st.cache_data` (a real performance fix caught during this session: the first draft rebuilt the entire
   ReportLab PDF, including a fresh Strategic Risk pass over all 17 countries, on every single script
   rerun -- e.g. toggling the map's city/hub checkboxes -- not just when the underlying data changed).

**A real bug caught and fixed during this session, not shipped:** naming every new engine module the same
as its page file (`src/strategic_risk.py` next to `app_pages/strategic_risk.py`, same for `outlook.py`)
caused a circular self-import the moment the page tried `from strategic_risk import assess_all` -- Python
resolved "strategic_risk" to the page file itself (shadowing the src module, since `app_pages/` sits earlier
on `sys.path` per `tests/conftest.py`), not the intended module. Worse: **this exact bug already existed,
silently, in the previous session's `economic_analysis.py`** -- it happened not to surface then because
pytest's import-caching order masked it in a full-suite run, but broke immediately when that one test file
was run in isolation. All three engine modules were renamed with an `_engine` suffix
(`strategic_risk_engine.py`, `outlook_engine.py`, `economic_analysis_engine.py`) to eliminate the collision
class entirely, and a systematic `comm -12` check across every `src/`/`app_pages/` basename confirmed no
other collisions exist. Worth remembering for any future page+engine-module pair this project adds.

62 new tests this session (`test_strategic_risk.py`, `test_outlook.py`, `test_data_validation.py`,
`test_pdf_export.py`); 333/333 passing. Verified in-browser via Playwright across every one of the app's 10
pages.

**Deliberately still not built:** a full WCAG contrast/screen-reader audit and a mobile-first layout
redesign (Streamlit's own column-based layout has known limits on narrow viewports that aren't fixable
without a different UI framework -- out of proportion for this session). Everything else the original
42-section brief asked for is now built.

**Previous session: Tiers 2-3 of the same "9+/10 credibility upgrade" brief -- the Economic Analysis page
and the Sources & Data catalog.** Continuing directly from the Tier 1 session below. Two real gaps closed:

1. **Economic Analysis page** (`app_pages/economic_analysis.py` + `src/economic_analysis.py`). The primary
   finding: AI governance maturity is moderately-to-strongly associated with US export-control tier
   (Pearson r=0.68, Spearman ρ=0.64, full 17-country sample -- every other candidate relationship involving
   investment or compute figures only has 4-6 of 17 countries with both values, documented and rejected in
   a `CANDIDATE_RELATIONSHIPS` table on the page). Reported as a correlation, not a fitted regression (n=17
   with two 5-point ordinal scales doesn't support the false precision a regression line implies), with two
   robustness checks (excluding Saudi Arabia/UAE: r=0.52; excluding Yemen/Afghanistan: r=0.63 -- the
   association survives both, so it isn't purely 2-4 outliers) and an explicit three-way
   association-vs-causation discussion (governance→tier, tier→governance, or a shared confound -- a single
   cross-sectional snapshot can't distinguish between them, and the page says so).
2. **A real workaround for the blocked World Bank pipeline.** The project owner explicitly said not to
   limit sourcing to the World Bank API specifically -- "take it from any source as long as it is reliable
   and valid." A background research agent gathered real, cited non-oil GDP share figures from IMF Article
   IV releases, national statistics agencies (UAE's FCSC, Qatar's NPC, Bahrain's and Oman's finance
   ministries), and World Bank *published* reports (as opposed to the live, currently-blocked API) for 8 of
   17 countries -- and correctly marked the other 9 as **structurally not-applicable** (Pakistan, Turkey,
   Israel, Jordan, Lebanon, Syria, Yemen, Afghanistan aren't hydrocarbon-rent economies at all, so the
   "non-oil GDP share" concept doesn't mean anything for them; Egypt has a real-but-misleadingly-small oil-
   rents figure that would imply ~97% "non-oil" on par with a rentier state if forced through the formula,
   so it was correctly left out rather than reported). New file: `data/curated/non_oil_diversification.csv`.
   Used as a **supplementary, smaller-sample finding** (diversification vs. China Exposure Depth, r=-0.50,
   n=8, explicitly flagged as exploratory) alongside the primary n=17 governance/tier result -- never given
   equal weight to the full-sample finding, and the investment/compute-vs-diversification angle the original
   brief suggested was checked and still rejected (n=2, Saudi Arabia and UAE only).
3. **Sources & Data page** (`app_pages/sources_data.py` + `src/data_catalog.py`). A research data catalog:
   every dataset this tracker uses (13 entries -- 11 curated, 1 computed, 1 live/automated), with source
   type, country coverage, observation count, missingness, methodology note, and limitations all **computed
   live from the actual files** at page-load time (row counts, unique-country counts, null percentages --
   never hard-coded numbers that could drift out of sync with the data). Each curated CSV has a direct
   download button. Coverage counts correctly exclude non-tracked pseudo-country rows (e.g.
   `compute_capacity_deals.csv`'s "GCC region-wide" context row) so a long-format file never reports more
   than 17/17 countries.

25 new tests (`test_economic_analysis.py`, `test_data_catalog.py`, plus the new diversification-data
checks); 208/208 passing. Verified in-browser via Playwright.

**Deliberately still not built:** Strategic Risk page and 12-Month Outlook page (Tiers 3-4 of the brief) --
both remain real scope beyond this session; chart-style centralization, PDF export restructure, full
accessibility pass (Tier 5 polish, explicitly lowest priority in the brief's own ordering).

**Previous session: Tier 1 of a 42-section "9+/10 quality & credibility upgrade" master prompt.** The
project owner pasted a very large, explicitly self-prioritized brief (Tiers 1-5, `IMPLEMENTATION PRIORITY`
section) aimed at making the tracker read as a CSIS/CFR/PIIE-grade research product rather than a "student
Streamlit dashboard." Given the brief's own scale and its own explicit decision rule ("If a feature cannot
be implemented without fabricating information, do not implement a fake version"), this session built Tier
1 in full and documented Tiers 2-5 as deliberately deferred, rather than attempting a shallow pass across
all 42 sections.

**Tier 1 built, in the brief's own order:**

1. **Methodology consistency audit.** Swept README.md, every `app_pages/*.py`, `src/scoring.py`'s
   docstring, and PROGRESS.md for stale "single-factor China axis" / "6 factors" language left over from
   the China Exposure Depth work two sessions ago. Found and fixed one real remaining case:
   `regional_dashboard.py`'s "read this before the numbers" expander still said "China Exposure Depth
   currently rests on a single factor" -- updated to describe the current 2-factor, 50/50-weighted
   methodology. Everywhere else was already consistent (verified by grep, not assumed).
2. **Executive Key Findings on the Overview.** `ui.key_findings_card()` (new component) renders a 4-part
   KEY FINDINGS / KEY JUDGMENT / CONFIDENCE / WHY IT MATTERS card. `regional_dashboard.py`'s `_key_findings()`
   computes all four fields from the live composite dataframe (the modal-quadrant bottom line already
   existed; Key Judgment is new -- the point spread between the most US-integrated and most China-leaning
   country -- and Why It Matters is a fixed, defensible analytical framing sentence, not a fabricated
   per-run claim).
3. **Country Deep Dive rebuilt as an intelligence profile.** New hierarchy: Current Position -> Bottom Line
   Up Front -> Key Judgments (existing) -> **Key Drivers** (new factor-level table: all 5 scored components
   across both axes, with raw value, scored value, weight, and confidence pulled from the same curated rows
   used elsewhere, never re-derived) -> **Trend** (new, via `src/momentum.py`) -> **What Changed** (new,
   reuses `policy_events._affected_countries()` to filter the existing event feed to this country) ->
   **Strategic Implications** (new, `_strategic_implications()` -- deterministic, branches on the country's
   actual tier/axis values into distinct Policymakers/Investors/Corporates text, never a generic paragraph
   repeated for every country, and explicitly never a buy/sell recommendation -- covered by a test that
   asserts neither word appears) -> **What to Watch** (new, via `src/watch_next.py`) -> **Data Quality**
   (new, factor coverage + confidence distribution + deal counts) -> Sources (existing).
4. **What Changed intelligence feed.** The existing Policy Event Tracker was already close to this
   spec (dated, sourced, categorized, with a "Model impact & source" expander using the same honest
   "current tier, not a fabricated delta" pattern from an earlier session). Added: a country filter, a date-
   range filter, and a new `direction` column (`Loosening`/`Tightening`) on `policy_events.csv` -- an
   analyst classification of each event's already-described effect (e.g. the AI Diffusion Rule's issuance
   is `Tightening`, its rescission is `Loosening`), covered by a test that asserts both bilateral-
   authorization events are classified `Loosening` (a sanity check that the label tracks the event's actual
   effect, not an arbitrary tag).
5. **Watch Next, a new reusable component.** `src/watch_next.py` + `data/curated/watch_indicators.csv` (6
   rows). Every indicator is derived from an already-cited fact elsewhere in the curated data flagged
   `pending`/`target`/`not yet realized` -- e.g. Egypt's unresolved Huawei/iFlytek AI-data-center bid,
   Jordan's not-yet-built Al-Risha 400MW target, the five countries whose export-control tier is still `Low`
   confidence pending BIS access. Rendered on the Overview (regional-scope items) and every Country Deep
   Dive (country-specific + regional items). Explicitly labeled leading indicators, never forecasts.
6. **Score Momentum infrastructure.** New `src/momentum.py`: `compute_momentum()` and `regional_momentum()`
   classify a metric's trajectory (Accelerating/Increasing/Stable/Declining/Rapidly declining) from
   `composite_scores_history.csv`, with a hard rule -- fewer than 2 dated snapshots returns `Insufficient
   data`, fewer than 3 can report direction but never acceleration. **As of this session the history file
   holds exactly one dated snapshot (2026-09-02)**, so every live call currently returns `Insufficient data`
   -- this is the correct, honest behavior per the brief's own rule, not a bug, and needs no code change the
   day a second snapshot lands. Wired into the Overview (one regional-trend caption) and every Country Deep
   Dive (a Trend section for all 3 axes). 13 tests exercise the classification logic directly with synthetic
   multi-snapshot histories the live data doesn't yet have, so the logic is verified even though it can't
   yet be observed live.

**Also fixed while touching these files:** a `ModuleNotFoundError` at runtime (not caught by tests, which
add `app_pages/` to `sys.path` themselves) -- `country_deep_dive.py`'s new `from policy_events import
_affected_countries` needed an explicit `sys.path.insert(0, .../app_pages)`, since Streamlit's page router
doesn't put a page's own directory on the path the way the test suite's `conftest.py` does. Caught via a
live Playwright pass, not by the test suite -- worth remembering this class of bug isn't test-visible.

**Deliberately not built this session (Tiers 2-5 of the brief) -- and why:**

- **Sources & Data catalog page, Strategic Risk page, 12-Month Outlook page.** All three are net-new pages,
  not enhancements to existing ones -- real scope, not fabrication risk, just larger than a single Tier-1-
  focused session. The underlying data these pages would present already exists and is already surfaced
  elsewhere (Methodology page, README, Key Drivers table, Watch Next), so nothing is currently hidden; it
  would just be re-presented in a more purpose-built layout.
- **One serious empirical economic-analysis module (Section 21, PIIE angle).** Not attempted this session --
  a real, defensible descriptive/associational analysis (e.g. AI investment vs. non-oil diversification)
  needs its own careful sample-size and causality-framing pass, not a rushed addition alongside 5 other
  Tier-1 items. Flagged as the highest-value Tier 3 item for a follow-up session.
- **Chart-styling centralization, PDF export upgrade to the fuller "policy brief" structure, full
  accessibility pass.** Tier 5 polish items, explicitly lowest priority in the brief's own ordering. The
  existing PDF export and chart styling are functional and already follow the paper/ink palette; this is
  refinement, not a missing feature.
- **Country cards on the Overview** (Section 8) already show Net Alignment, US/China sub-scores, and tag --
  Momentum wasn't added to them specifically (17 cards x a Trend badge reading "Insufficient data" for
  every one would be pure repetition with zero information value at N=1 snapshot); the single regional-
  trend caption plus the full per-country Trend section on Country Deep Dive covers this honestly without
  the repetition.

**Most recent session before this one: added two optional map reference layers -- major cities and named AI/compute
hubs.** The project owner asked for the Regional Dashboard's map to "highlight main cities, ai hubs and
other important info ... whatever is needed to make it more detailed." Built as two independently
toggleable marker layers (both on by default) on the existing custom `go.Scatter`-polygon choropleth in
`src/mapping.py`:

- **Major cities** (`data/curated/major_cities.csv`, 17 rows) -- one reference dot + label per tracked
  country, for geographic orientation. Framed deliberately as "major city," never "capital," to avoid
  taking a position on disputed political-status questions: Israel is labeled Tel Aviv (its actual
  tech/financial hub -- "Silicon Wadi" -- and arguably more relevant to an AI-alignment tracker than a
  political capital anyway) rather than the internationally disputed Jerusalem designation; Yemen is
  labeled Sana'a as the constitutional capital, worded to make no claim about which government currently
  controls it amid the civil war.
- **AI / compute hubs** (`data/curated/ai_hubs.csv`, 9 rows) -- specific, named infrastructure sites,
  rendered as gold stars with hover text citing the deal, its scale, and its source. Built under a strict
  rule to keep the no-fabrication discipline intact for a *new* kind of claim (precise geographic
  location, which this project had never asserted before): **a site only gets a hub marker if its curated
  deal-data notes already explicitly name that location** -- never inferred from a company's known
  headquarters or an announcement venue. This ruled out two real candidates: the UAE's Stargate campus
  (widely reported as Abu Dhabi-adjacent given G42's HQ, but the curated deal notes don't name a specific
  site) and Saudi Arabia's "KKR + Gulf Data Hub (LEAP25)" deal (announced at a Riyadh conference, but the
  conference venue isn't the same fact as the data center's physical site) were both left off the map
  rather than guessed at. The 9 sites that made the cut: NEOM (Saudi Arabia); Ashdod, Mevo Carmel, and
  Kiryat Tivon (Israel, 3 separate Nvidia/data-center deals); Cairo/Maadi Technology Park (Egypt, 2 deals);
  Baghdad (Iraq); the Al-Risha gas field in eastern Jordan (explicitly flagged as an *approximate* regional
  location, not a precise coordinate, since only the gas field's general area is disclosed); Tartus, Syria
  (the SilkLink subsea cable landing station); and Istanbul (Turkey's Huawei Cloud region, already cited in
  `chinese_digital_ties.csv`).

`src/mapping.py`'s `build_choropleth_figure()` gained optional `city_markers`/`hub_markers` params (lists
of `{lat, lon, name, hover}` dicts), rendered as additional `go.Scatter` traces on top of the existing
country polygons -- zero new runtime dependencies, consistent with why this project draws its own
choropleth instead of using Plotly's geo subplot machinery in the first place. `app_pages/
regional_dashboard.py` gained two checkboxes next to the existing metric selector and a caption explaining
what's shown and why (including the Tel Aviv/Sana'a framing and Jordan's approximate-location flag). Also
fixed two stale mentions of "single-factor China axis" / "6 factors" in this page's own "read this before
the numbers" expander that the prior session's China Exposure Depth work had missed. 18 new tests added
(`tests/test_mapping.py`, plus new classes in `tests/test_scoring.py` and `tests/test_regional_dashboard.py`)
covering the two CSVs' schemas and the marker-building/rendering logic; full suite at 104/104 passing.
Verified in-browser via Playwright, including toggling both layers off.

**Previous session: closed China Exposure Depth's single-factor limitation** with a second, independent,
fully-sourced factor -- Chinese AI/cloud/digital-infrastructure ties -- researched across all 17 tracked
countries and blended 50/50 with the existing Chinese-telecom-penetration factor. This was the top item on
the project owner's approved "deepen the project" list, carrying an explicit standing instruction: no
fabrication, everything grounded in current, reliable, cited 2025/2026 sources.

**How the research was done:** three parallel background research agents (isolated worktrees, `WebSearch`
only -- `WebFetch` is broadly blocked in this sandbox, confirmed even for benign domains like Wikipedia),
each covering a subset of the 17 countries, each returning structured JSON scored against a shared 0-5
rubric (0 = no disclosed presence, 5 = extensive/state-level backbone plus multiple financing ties -- see
the Methodology page or README for the full table). Every row carries a `source_name`, `source_url`,
`confidence` (High/Medium/Low), `as_of_date`, and a `rationale` explaining the score -- the same sourcing
bar as every other curated factor in this project, never an inferred or aggregated number.

**A real integrity check passed during this research:** one candidate source for Egypt's digital-ties score
-- a specific-dollar-figure claim ("$9.8bn, Deutsche Bank-facilitated" data-center financing via an obscure
outlet, `cqbluejay.com`) -- was flagged by the research agent itself as carrying "hallmarks of a fabricated
financial press release" (a chain of obscure SPV entities with no independent corroboration) and correctly
declined. Egypt's score instead rests on mainstream Bloomberg/Entrepreneur/Al-Monitor reporting of the real,
still-unresolved Huawei/iFlytek AI-data-center bid. This is the no-fabrication instruction working as
intended, not a close call that got waved through.

**What changed in the data and the score:**

- New file `data/curated/chinese_digital_ties.csv` (17 rows, full schema matching the project's other
  curated factors). Final scores span the full 0-5 range: Israel and Bahrain lowest (0-1, `High`/`Low`
  confidence respectively), Saudi Arabia and Pakistan highest (4, "Deep"). Three rows (Bahrain, Jordan,
  Iraq) are `Low` confidence -- flagged, not hidden -- because their evidence rests on a single MOU or
  marketing announcement rather than a confirmed, audited deployment.
- A specific, documented finding worth a reader's attention: **Saudi Arabia's digital-ties score (4/5,
  "Deep") exceeds its telecom-penetration score (3/5, "Significant")** -- an active Huawei/Alibaba Cloud
  footprint plus a disclosed Chinese-financed data-center joint venture outweighs its telecom exposure.
  **Iraq shows the opposite pattern** (telecom 4/5 "Deep" vs. digital ties 1/5 "Minimal" -- Huawei is
  entrenched in Iraqi telecom, but its flagship digital-infrastructure financing bid has stalled). Neither
  factor reliably predicts the other, which is exactly why the brief called for two factors instead of one.
- `src/scoring.py`: new `CHINA_TELECOM_WEIGHT = 0.50` / `CHINA_DIGITAL_WEIGHT = 0.50` constants; a new
  shared `_weighted_average()` helper (replacing the old US-Integration-only inline closure, now used
  symmetrically by both axes); `build_composite()` gained `china_telecom_weight` / `china_digital_weight`
  override params, defaulting to the scored 50/50 split, with the same renormalize-over-available-factors
  behavior US Integration Depth already had (a country missing one China factor is scored on the other
  alone, never silently treated as 0).
- Real score movement, not a cosmetic relabeling: Saudi Arabia's `net_alignment_score` moved from 59.78 to
  54.78 once its China Exposure Depth stopped being a pure telecom-only passthrough (60.0) and became the
  blended figure (70.0, pulled up by its high digital-ties score). This is the expected, correct effect of
  adding a real second factor -- not a bug.
- `src/country_brief.py`, `app_pages/country_comparison.py` (radar + raw-data table), and
  `app_pages/regional_dashboard.py` (map metric selector) all updated to surface the new factor alongside
  the existing telecom one, never replacing it.
- `app_pages/scenario_lab.py` gained a China Exposure Depth sub-weight slider row (telecom vs. digital
  ties), mirroring the existing US Integration slider row exactly -- two new presets
  ("China-telecom-centric", "China-digital-ties-centric") demonstrate the two ends of that range, and the
  Model Robustness analysis now samples the China sub-weights too, not just the US ones.
- `app_pages/methodology.py` and README.md updated: the factor-weights table, the ordinal-rubric tabs (a
  third rubric added), the confidence-counts table, the "why 7 factors" section, the Known Limitations
  entry (rewritten from "single-factor axis" to "the new factor is thinner-sourced than the one it
  complements," which is now the true state), and the Scenario Lab / roadmap sections.
- `data/computed/composite_scores.csv` regenerated; `data/computed/composite_scores_history.csv` gained a
  new dated snapshot reflecting the post-change scores.
- Full test suite (86 tests, including new coverage for the weighted-average symmetry, the renormalization
  behavior, and the curated CSV's own shape) passes.

**Previous session: a scoped subset of a 56-section "master upgrade brief"** the project owner pasted
(sourced from an outside consultant's advice), aimed at turning the tracker into a CSIS/CFR/PIIE-style
professional geopolitical-intelligence product rather than a "Streamlit demo." The brief itself says to
implement in phases, not all at once, and names its own top 3 highest-value items -- this session did
exactly those three, plus the foundational design-system work they depend on, and explicitly declined
several other sections rather than build them dishonestly. Full reasoning below; see the brief's own
sections (numbered) referenced throughout.

**The one hard blocker, flagged before writing any code:** sections on Score Momentum, historical trend
charts, and a 12-Month Outlook all require comparing a country's score against a *past* snapshot. This
tracker stores exactly one point-in-time value per country -- no `scored_history.csv` equivalent exists
(unlike MENASA, which has one). Building those sections honestly would mean every single cell reads
"Insufficient data," per the brief's own rule ("never calculate momentum when there is insufficient
historical data"). Rather than fabricate a trend, or build a UI for data that doesn't exist yet, this
session skipped them entirely -- flagged as the top honest follow-up (see Open Questions).

**What was built, in the order the brief itself prioritized:**

1. **Design tokens (Section 4-7).** `.streamlit/config.toml` and `src/ui.py` adopted the brief's exact
   palette (`#F5F4EF` paper, `#17202A` ink, `#2463A5` blue = US integration, `#B5473A` red = China exposure,
   `#A77B20` gold = caution/uncertainty, `#397A5B` green = confirmed, `#6B7280` gray = neutral/unavailable)
   -- deliberately *not* "blue = good, red = bad," per the brief's own explicit instruction. `src/ui.py`
   gained `page_header()` (title + subtitle + right-aligned mono metadata, e.g. "17 COUNTRIES", "DATA AS OF:
   SEPTEMBER 2026"), `bottom_line()`, and `evidence_card()` components alongside the existing KPI cards and
   confidence pills.
2. **Navigation restructure (Section 6-7).** Migrated off Streamlit's classic `pages/` folder onto
   `st.navigation()` with grouped sections (Overview / Country Intelligence / Policy Monitor / Forecasting /
   Research), matching the brief's proposed IA. This is a real structural change, not cosmetic: `app.py`
   is now a ~25-line router (`st.set_page_config()` + `st.navigation({...}).run()`), and every page's actual
   content moved into a new `app_pages/` folder (`pages/` was a magic auto-discovered folder under the old
   system and had to be vacated to avoid Streamlit rendering both navigation systems at once). This also
   fixes a long-standing known issue flagged in earlier sessions: the sidebar's top entry no longer reads
   the literal, un-styled word "app" -- it now reads "Regional Dashboard" under an "Overview" heading, same
   fix work previously deferred as "needs `st.navigation()` migration, bigger than a quick pass."
3. **US-vs-China positioning scatterplot (Section 11)**, the brief's #1-ranked highest-value item -- added
   to the renamed "Regional Dashboard" (formerly the Overview page). X = China Exposure Depth, Y = US
   Integration Depth, quadrant divider lines at 50/50, quadrant labels ("Strategic hedgers," "US-oriented,"
   etc.), hover tooltips with the full score breakdown. **Caught and fixed a real bug during verification**:
   the first draft had the top-left/bottom-right quadrant labels swapped (mixed up which corner is
   low-China/high-US vs. high-China/low-US) -- caught by actually reading the rendered screenshot against
   the axis definitions, not just trusting the code. Also switched from permanent on-chart country-name
   labels to hover-only once 17 overlapping labels turned out to be unreadable in practice (with a
   collapsed data table underneath as a non-hover fallback for a reader who wants exact values without
   hovering each point).
4. **Evidence -> Model Impact chain (Section 15-17)**, the brief's #2-ranked item -- every Policy Event
   Tracker card now has a "Model impact & source" expander showing which of this tracker's scoring
   components the event connects to (currently always US export-control tier -- every event in this
   8-event dataset is chip/export-policy news) and the tagged countries' *current* scored tier with
   confidence. **Deliberately does not show a fabricated numeric delta** ("+6.2" style, as the brief's own
   example shows) -- there is no pre-event historical score to compute a real one from, and the brief
   itself says to show "qualitative relevance" instead of inventing a number in exactly this situation.
   `_affected_countries()` parses the curated `policy_events.csv`'s free-text `countries` column against
   the tracked-country list, handling the "Global (incl. all N tracked countries)" case explicitly.
5. **Model Robustness / Rank Stability (Section 23)**, the brief's #3-ranked item -- added to the renamed
   "Scenario Lab" (formerly "Scenario Explorer," per Section 21). Samples 150 random-but-valid weight
   configurations (documented fixed seed, uniform draws across each slider's actual valid range) and
   reruns the exact same `build_composite()` used everywhere else in this tracker for each one, reporting
   median/best/worst rank and a rank-range-based robustness label (HIGH/MODERATE/LOW) per country.
   Deliberately labeled **"scenario/rank stability," never "statistical significance" or "confidence
   interval"** -- per the brief's own explicit warning against overclaiming what a sensitivity sweep can
   support. Gated behind a button (initial version auto-ran on every page load at 300 samples and took
   ~6 seconds; reduced to 150 samples and made opt-in after measuring the actual cost, not guessing at it).
   Also fixed the "top-3 frequency" framing bug this design invites: a country that reliably ranks *last*
   regardless of weighting is exactly as rank-*stable* as one that reliably ranks first, so robustness is
   computed from rank-range width, not proximity to the top -- documented inline so a reader doesn't
   mistake "0% top-3" for "unstable."

**Verification, not just writing the code:** ran the full pytest suite before and after (48 -> 68 tests,
20 new: rank-range consistency and reproducibility for the robustness sampler, `_affected_countries()`
resolution against real `policy_events.csv` rows including the "Global" special case, and the bottom-line
generator's behavior on both the real dataset and an empty edge case). Booted the restructured app with a
local Streamlit server and screenshotted every single page via Playwright -- this is what caught the
quadrant-label swap in item 3 above; reading the rendered output, not just the code, is what found it.

**Deliberately not built, and why (the brief itself asks for this list rather than a bare "10/10" claim):**

- **Score Momentum, historical trend charts, 12-Month Outlook, "What Changed" deltas (Sections 10, 18, 24-25)**
  -- blocked on the no-historical-data problem above. The honest fix is capturing a dated snapshot of
  `data/computed/composite_scores.csv` going forward (a small addition to the existing `src/scoring.py`
  `__main__` block) so this becomes buildable in a few months, not fabricating a trend today.
- **Investor / Policymaker / Corporate view tabs, Strategic Investment Risk page (Sections 26-27)** -- real
  scope-creep and overclaiming risk: this tracker's data supports a technology-alignment assessment, not
  financial risk scoring or investment recommendations, and dressing the same 6 factors up as "financial
  risk dimensions" without new, defensibly-sourced data would be exactly the kind of unsupported-precision
  problem the brief itself warns against in Section 30 ("every variable must have... a defensible
  definition... If those conditions cannot be met, retain the existing variable").
- **Separate "Sources & Data" page (Section 28)** distinct from the existing Methodology page -- the
  existing single Methodology page already covers this content; splitting it was judged to add navigation
  complexity without adding real information, not skipped from laziness.
- **PDF export redesign, "Research Brief" per-country export upgrade (Sections 36-37)** -- the existing
  PDF export (via `reportlab`, see `src/pdf_export.py`) already works and is already reasonably clean;
  a redesign pass wasn't part of the top-3-prioritized scope and wasn't requested beyond the original brief.
- **Full emoji/decorative-noise purge across every remaining page** (Section 49) -- the four
  brief-implementation items above got the new design language; the Country Deep Dive and Policy Event
  Tracker pages' pre-existing emoji category icons were left as-is rather than doing a cosmetic-only sweep
  unrelated to the four functional items actually requested.

**Before that, four "quick win" polish items, asked for directly after a project/site rating
request.** Prompted by an honest rating exchange (content 9/10, technical 8/10, visual design 7/10 up from
an earlier 3/10, but with the Render free-tier cold start flagged as the single biggest remaining risk to a
recruiter's first impression) -- the project owner asked for suggestions, then said "yep" to doing the four
free/quick ones:

1. **Real favicon.** `assets/favicon.png` (512x512 PNG, generated with PIL -- a simple blue/red split
   circle in the project's own palette, echoing the "two blocs" theme) replaces the generic 🌐 emoji as
   `page_icon` on every page. Streamlit accepts a local image path there, not just an emoji or a Unicode
   codepoint.
2. **Open Graph / Twitter Card tags**, so sharing this link (LinkedIn, Slack, iMessage) actually renders a
   preview card instead of a bare URL. Needed a real card image too: `static/og-image.png` (1200x630,
   generated with PIL + IBM Plex Serif/Work Sans, matching the app's paper/ink theme), served via
   `[server] enableStaticServing = true`.
3. **Country Comparison's radar chart no longer defaults to all 17 countries.** It was genuinely unreadable
   at that density (flagged in the project rating). Now defaults to the original 6 Gulf states; the
   multiselect still lets a reader add any of the other 11.
4. **The MENASA-style branded cold-start loading screen**, so a Render free-tier wake-up (~20-30s) reads as
   "loading," not "broken."

Items 1, 2, and 4 all came from porting a pattern the companion MENASA Risk Monitor had already built and
proven: `patch_og_tags.py`, a script that patches Streamlit's own shipped `index.html` directly as a Render
build step (`pip install -r requirements.txt && python patch_og_tags.py`), because Streamlit is a
client-rendered SPA with no `<head>` a running Python/JS snippet can actually reach -- `st.markdown` content
gets iframe-sandboxed and link-preview crawlers don't execute JS at all. This tracker's version was renamed
to match MENASA's filename (was `patch_analytics.py`, a narrower GA-only version added earlier this
session) once it grew OG tags and the loader too, so a reader who's seen one project recognizes the pattern
immediately in the other. It also reuses MENASA's GA4 property (`G-QP9RPS41KJ`) rather than a separate one
-- see the GA section below, which predates this entry.

Verified end to end before calling this done: ran the patch script against the actually-installed Streamlit
package and confirmed via `curl` that the served page's `<head>` contains the real OG meta tags pointing at
a `static/og-image.png` URL that itself returns `200` (i.e. the image is actually reachable, not just
referenced), that the custom favicon is served as the page's icon (not the Streamlit default), and with a
Playwright screenshot that the Country Comparison page's radar chart is legible with the new 6-country
default. All 48 tests still pass.

**Not done, and worth a future look:** an equivalent OG-image/favicon pass on the standalone Claude Artifact
briefs (they're static HTML files with their own design already, not Streamlit -- a different, unrelated
technique would be needed there, and it wasn't asked for). Also not done: the sidebar's first nav entry
still literally reads "app" (a Streamlit filename quirk flagged in an earlier session entry) -- fixing that
needs a move to Streamlit's newer `st.navigation()` entrypoint API, a bigger structural change than any of
this session's quick wins.

**Before that, a further direct follow-up: "include date [data] for all
those countries as well."** The 9 countries just added to the map as unscored gray context (Iran, Iraq,
Syria, Jordan, Lebanon, Israel, Yemen, Egypt, Afghanistan) are now fully scored, real countries in this
tracker -- 17 total, up from 8. This is a genuine scope expansion, not a cosmetic map fix, and was treated
with the same research rigor as the original 8: three parallel research agents (Israel/Egypt/Jordan,
Iraq/Lebanon/Syria, Iran/Yemen/Afghanistan) each read the existing CSVs first to match format and
confidence-tagging discipline, then used WebSearch/WebFetch against real, dated, named sources for every
one of the 5 curated data files (export-control tier, Chinese tech penetration, governance maturity,
AI investment deals, compute capacity deals) -- see "Country set" in README.md for the full writeup,
including the two hardest judgment calls (Israel's export-control tier, Syria's post-2025-sanctions-relief
but still-D:5-for-chips status) and the one live/unresolved situation (Egypt's pending Huawei-vs-US AI
data-center bidding war).

Mechanically:
- All 9 countries' research came back as JSON (not raw CSV text) from the research agents, matching each
  CSV's exact column schema, then integrated via a small Python script using `csv.writer` (never
  hand-built string concatenation) to guarantee correct quoting/escaping given how many rationale fields
  contain commas, quotes, and dollar signs.
- `src/constants.py`: `COUNTRIES` grew from 8 to 17 entries; added a `REGIONAL_COUNTRIES` set alongside the
  existing `GULF_COUNTRIES`/`COMPARATOR_COUNTRIES` (a map/labeling distinction only -- all three groups use
  the identical scoring methodology).
- `data/geo/region_countries.geojson`: every feature's `scored` property flipped from `false` to `true`,
  which automatically empties `context_ids` in `app.py`/`src/mapping.py` -- the muted-gray "not tracked"
  rendering path is still wired up (for a future country added before it's researched) but currently
  renders nothing, since all 17 bundled countries are now scored.
- `app.py`: KPI "composite score coverage" card, country-ranking tag logic (now 3-way: Gulf/Comparator/
  Regional, sourced from `constants.py` instead of a second hardcoded set), map caption, and the caveats
  expander's "no disclosed investment/compute" country list were all updated to reflect the real 17-country
  picture rather than left stale.
- `data/computed/composite_scores.csv` regenerated via `PYTHONPATH=src python3 src/scoring.py` -- all 17
  countries produce a real (non-`N/A`) Net Alignment Score, since every one of them now has at least an
  export-control tier and a Chinese-tech-penetration score (the two inputs that can never be missing under
  this project's renormalization rule).
- `tests/test_scoring.py`'s `test_all_eight_countries_present` (hardcoded `len(df) == 8`) renamed to
  `test_all_countries_present` and now asserts against `len(COUNTRIES)` instead of a literal -- the kind of
  hardcoded assumption a country-count expansion is exactly designed to catch. Several stray "8 countries"
  mentions in docstrings/comments (`country_brief.py`, `fetch_worldbank.py`, both country-comparison pages)
  were also swept for accuracy, though none were load-bearing.
- Verified in-browser with a local Streamlit server + Playwright across every page (Overview top/bottom,
  Country Comparison, Country Deep Dive, Scenario Explorer, Methodology) before calling this done, plus a
  direct Python check that `generate_brief()` and `build_country_pdf()` succeed for all 9 new countries
  (the Deep Dive page's country dropdown is a Streamlit BaseWeb widget that has repeatedly resisted reliable
  Playwright automation earlier in this project -- same known flakiness, same decision to trust the
  equivalent direct-function-call check plus the full pytest suite instead of fighting the locator). All 48
  tests pass (up from 39 -- the country-count expansion grew some parametrized-style coverage along with
  the dataset).
- One visible, expected side effect: the Country Comparison page's radar chart is visually dense with all
  17 countries selected by default (it was already the multiselect default-to-all behavior at 8 countries;
  17 overlapping polygons is a real readability cost of that same design choice, not a new bug). The
  multiselect already lets a reader narrow it down; not treated as blocking, but worth a future look if the
  project owner wants a smaller default selection now that the country count has roughly doubled.

**Before that, a direct follow-up: "include all the countries in
between so the map looks full."** The Overview map's original GeoJSON held only the 8 tracked countries,
so Turkey, the Gulf peninsula, and Pakistan rendered as three disconnected landmasses with large empty gaps
where Iran, Iraq, Syria, and Afghanistan should be -- geographically correct, but it reads as broken or
low-effort rather than intentional. Fixed by rebuilding the bundled GeoJSON:

- Fetched the same public-domain `datasets/geo-countries` source used originally, this time keeping 17
  countries instead of 8: the 8 tracked ones plus Iran, Iraq, Syria, Jordan, Lebanon, Israel, Yemen, Egypt,
  and Afghanistan as unscored regional context. New file: `data/geo/region_countries.geojson` (~480KB),
  replacing `data/geo/gulf_countries.geojson` (deleted -- nothing else referenced it).
- `src/mapping.py`'s `build_choropleth_figure()` gained a `context_ids` parameter so the 9 context countries
  render in a light, unbordered gray with a hover label that says outright "not tracked by this index,"
  visually distinct from the darker, bordered gray already used for a *tracked* country with a genuine data
  gap (e.g. if Bahrain had insufficient data) -- those are two different situations and the map shouldn't
  make them look the same.
- `app.py` derives `context_ids` from each feature's `properties.scored` flag rather than hardcoding a
  country list a second time, and the map caption now names the 9 context countries explicitly so a reader
  isn't left guessing why they're on the map but gray.
- Verified in-browser again with the local Streamlit server + Playwright before calling it done (same
  standard as the visual pass below). All 39 tests still pass -- geometry-only change, no scoring touched.

**Before that, a visual-design pass on the Streamlit app itself, prompted by direct user feedback
after reviewing the deployed dashboard.** The verdict was specific: content 8/10, presentation 3/10 --
"it's 100% unstyled default Streamlit... zero visual identity... looks like a homework submission." The
underlying analysis (methodology transparency, the Scenario Explorer, sourced confidence levels) wasn't
the problem; the problem was that every page was default gray-on-white Streamlit chrome. Fixed in order of
the impact the user identified:

1. **`.streamlit/config.toml`** -- replaced the single `primaryColor` override with a full custom theme:
   warm paper background (`#f7f7f2`), ink text, `#2454a6` blue accent (not Streamlit's default red/blue),
   and `Source Serif 4` / `Public Sans` / `IBM Plex Mono` as heading/body/code fonts -- the exact palette
   and type system already used in the three standalone briefs, so the dashboard and the briefs now read
   as one portfolio rather than two disconnected projects.
2. **`src/ui.py`** (new) -- one shared module every page imports: `inject_base_css()` hides the Streamlit
   hamburger menu, footer, and "Made with Streamlit" badge and loads the Google Fonts as a CSS fallback;
   `kpi_card()`/`kpi_row()` render metric cards; `confidence_pill()` renders a colored badge (blue/amber/red)
   for a confidence string, replacing plain emoji dots; `footer()` renders a consistent attribution +
   last-updated line at the bottom of every page.
3. **Overview page (`app.py`) restructured**: 4 KPI cards (regional average, most US-integrated, most
   China-leaning, composite-score coverage) now lead the page, above the "read this before the numbers"
   caveats -- previously the caveats were the first thing on the page. The map moved from a cramped 3/4-width
   column squeezed next to a text legend to full width at `height=560` (was 460), with hover tooltips now
   showing the US Integration / China Exposure sub-score breakdown, not just the net score. The legend
   became a single caption line under the map instead of its own column. The country-ranking list (plain
   text rows) became a 4-across grid of bordered metric cards.
4. **Country Deep Dive**: the emoji confidence dots (🟡/⚪/🔴, which didn't actually distinguish High from
   Moderate from Low -- all three non-gap levels rendered the same white circle) became color-coded pill
   badges via `confidence_pill()`, matching the briefs' own confidence-tag styling.
5. **Verified in-browser**, not just by reading the diff: ran `streamlit run app.py` locally and screenshotted
   every page with Playwright (Overview top/bottom, Country Deep Dive, Policy Event Tracker, Scenario
   Explorer) before treating this as done, per this project's own standard for UI changes. One console
   warning appeared (`fonts.googleapis.com` blocked by this sandbox's network policy, same class of known
   sandbox limitation as `api.worldbank.org` and `cdn.plot.ly` elsewhere in this log) -- Streamlit's native
   `[theme]` font keys still applied correctly without it, and the Google Fonts `@import` is a pure
   enhancement that will resolve on Render's unrestricted network.
6. All 39 existing tests still pass unchanged -- this was styling/layout only, no scoring or data logic touched.

**Not done in this pass, and worth naming so it isn't mistaken for finished:** a real custom favicon (the
browser-tab icon is still the 🌐 emoji passed to `page_icon`, which is the idiomatic Streamlit approach and
was left as-is rather than fighting Streamlit's static-file serving for an uploaded PNG), and the sidebar's
first nav entry still reads as the literal label "app" (from `app.py`'s filename) rather than "Overview" --
fixing that requires moving to Streamlit's newer `st.navigation()` entrypoint API rather than the
folder-based `pages/` convention this project already uses, which is a bigger structural change than this
pass's scope and was deliberately not attempted alongside a purely visual pass.

**Also added beyond the original 4-phase brief: an in-app Methodology page** (`pages/5_Methodology.py`),
after being asked generally to make the project "much better and more detailed and more professional."
The gap: methodology, weights, and rubrics only lived in the GitHub README -- someone browsing the live
Streamlit app (a recruiter, most realistically) would never see any of that. MENASA's own README describes
an in-app "Methodology & Data" tab as one of its features; this tracker had nothing analogous. The new page
mirrors the README's methodology section (weights table with rationale, both ordinal rubrics in tabs,
missing-data handling) plus one thing that couldn't exist in a static README: a live confidence-level
breakdown table computed fresh from the actual curated CSVs each load, so it can never drift out of sync
with the data the way a hand-written summary could.

**All four phases from the original brief are now built.** Phase 4 (Scenario Explorer) was added after
being directly asked to re-evaluate it against Phase 2 on the merits, not by default -- the reconsideration
that changed the earlier "skip it" call: MENASA's own Scenario Explorer (live sliders + named shock
presets) is one of that project's headline features, and this tracker had nothing analogous; it's also a
small lift given `scoring.py`'s weights were already isolated as named constants.

- `src/scoring.py`'s `build_composite()` now takes optional overrides (`tier_weight`, `investment_weight`,
  `compute_weight`, `axis_balance`), all defaulting to the exact scored values -- verified with a dedicated
  test (`test_default_params_reproduce_baseline_exactly`) that calling it with no args is byte-for-byte
  identical to before this change. `axis_balance` generalizes the previously-hardcoded 50/50 split in the
  Net Alignment formula (`50 + (US - China) / 2`) into `50 + axis_balance*US - (1-axis_balance)*China`,
  which reduces to the exact original formula at `axis_balance=0.5`.
- `pages/4_Scenario_Explorer.py`: 3 sliders for the US Integration sub-weights (renormalized to sum to 100%
  automatically, so presets can pass human-friendly numbers like 70/15/15 rather than pre-normalized
  fractions), 1 slider for axis balance, 5 named presets each with a one-sentence stated rationale (not
  arbitrary positions), and a scenario-vs-baseline grouped bar chart plus a "biggest movers" readout.
- 6 new tests in `tests/test_scoring.py` (`TestScenarioOverrides`) cover: default-reproduces-baseline,
  weight renormalization, a tier-heavy scenario actually moving a country with real investment/compute data,
  both axis-balance extremes (0 and 1) reducing to the expected simplified formula, and a regression guard
  that scenario overrides never write back to `data/curated/*.csv` (checked via file mtimes). 39 tests total.

**Previous session: everything from prior sessions was deployed and made publicly visible, and Phase 2 was
built.**

- **Deployment/sharing (the "your side" items from prior sessions) are done**: the tracker is live at
  https://oaqjp-final-project-emb-ai-c8u6.onrender.com (Render free tier, deployed from this branch); all
  three brief artifacts were shared publicly; the portfolio site's 4 relevant project cards were updated
  from "Planned" to "Live" with working links -- this was done directly by a session with push access to
  `rafaywaqar-portfolio` (see `add_repo`/`register_repo_root` in that session's tool history), not just
  handed off as instructions. Verified the live portfolio actually renders the updated cards via a local
  Playwright screenshot before pushing.
- **Phase 2 (Policy Event Tracker) is now built**, reversing the earlier "only if a brief needs it" default
  -- reconsidered when directly asked to evaluate Phase 2 vs. Phase 4 on their merits: Phase 2 gives
  feature parity with the MENASA Risk Monitor's own "Live Conflicts" tab (one of that project's strongest
  features, and this tracker had nothing analogous), and most of the sourcing was already sitting in this
  session's own research from earlier work on the Gulf brief and the export-control confidence-gap pass --
  building it was assembly, not a fresh research project. Phase 4 (scenario toggle) was evaluated the same
  way and stayed deprioritized: it's an interaction feature, not an analytic one.
  - `data/curated/policy_events.csv`: 8 dated, sourced events, Jan 2025 - Jul 2026 (AI Diffusion Rule
    issued and rescinded, Chip Security Act introduced and marked up in committee, the Nov 2025 Saudi
    HUMAIN/UAE G42 authorizations, two March 2026 chip-smuggling indictments, the UAE's July 2026 Country
    Group A:5 upgrade). Every row has a real, checked source URL -- verified via fresh web searches in this
    session, not carried over from memory.
  - `pages/3_Policy_Event_Tracker.py`: filterable timeline cards (by category), a by-category count chart,
    explicit "not a live feed, last reviewed [date]" framing -- same honesty pattern as the rest of this
    project.
  - `tests/test_policy_events.py`: data-quality tests for the new dataset (no future-dated events, every
    row sourced, no duplicate titles) -- extends the test-suite pattern to the new data file rather than
    leaving it uncovered.

**Also added in an earlier session: a real automated test suite** (`tests/`, 27 tests, all passing) -- nothing
existed before this. `tests/test_scoring.py` covers the normalization bounds (including a regression test
for the exact min-max bug caught and fixed during the original build -- two data points must not collapse
to a 100-vs-0 spread), the missing-data-as-NaN-never-zero rule, weight renormalization when a US Integration
factor is unavailable, and the Net Alignment formula itself. `tests/test_country_brief.py` runs the brief
generator against all 8 countries and checks a country with no scored deals gets an explicit "Data gap"
judgment rather than a silently wrong number. Wired into two GitHub Actions workflows:
`.github/workflows/test.yml` runs on every push/PR, and `refresh_worldbank_data.yml` now runs the suite as
a gate before the scheduled weekly refresh commits anything -- a broken data change should fail CI, not get
auto-committed. `requirements-dev.txt` added for the pytest-only dev dependency.

**Latest research-pass session: a dedicated confidence-gap research pass**, per the "depth over breadth" call at the end
of the prior session (all four planned written pieces were already done -- see below). Results:
- **Upgraded:** Turkey's governance-maturity score (Low -> Medium confidence, fresh 2026 sourcing: an
  active "Turkiye 2026 AI Strategy" leveraging TUBITAK BILGEM/ASELSAN, concrete 2030 targets, a TBMM AI
  Research Commission report due late 2026) -- score itself moved 2 -> 3. Saudi Arabia's Chinese-tech-
  penetration score (Low -> Medium confidence, fresh STC-Huawei sourcing: SuperLink Nov 2024, Saudi
  Arabia's first Full Duplex deployment 2026) -- score unchanged at 3, but now properly evidenced as a
  three-vendor (Nokia/Huawei/Ericsson) picture with Huawei leading advanced-feature rollouts specifically.
- **Corrected, not just upgraded:** Bahrain's Chinese-tech-penetration score actually changed (3 -> 2) once
  a Bahrain-specific source (AGBI, on Batelco) showed the current deployed 5G vendor is Ericsson, with
  Huawei only in early-stage, unconfirmed 6G talks -- the prior score rested on a regional-only citation
  that didn't actually establish Bahrain's current vendor. This moved Bahrain's Net Alignment Score from
  40 to 50. **This is the kind of thing a "close the confidence gaps" pass is supposed to catch** -- a
  score that was wrong, not just under-sourced.
- **Still unresolved, and now explicitly documented as such:** Qatar, Bahrain, Kuwait, and Oman's
  export-control tier, and Turkey's export-control tier, remain `Low` confidence. A follow-up attempt to
  check BIS's own Country Group table directly (`bis.gov`, `beta.bis.gov`) hit `EGRESS_BLOCKED` from this
  session's network policy -- same class of restriction that blocked `api.worldbank.org` and `cdn.plot.ly`
  in the original build session (see "Environment note" below). Each affected row's rationale now states
  this explicitly (what's confirmed -- the UAE's own D:3/D:4 removal, corroborated by multiple law-firm
  sources -- versus what's inferred -- the other four Gulf states plausibly remaining in that same
  pre-upgrade bucket -- versus what's simply unverified this session) rather than leaving a vague "Low
  confidence" label with no explanation of what was tried. **Next session with unrestricted network
  access should check BIS's Interactive Country Groups tool directly** -- that's the one concrete
  unblocking step left on this front.

**Phase 1 (MVP) is built and working end-to-end**, tested in a network-restricted sandbox:
- Composite index (`src/scoring.py`) computing US Integration Depth, China Exposure Depth, and a derived
  Net Alignment Score for all 8 countries.
- Choropleth map of Net Alignment Score (`app.py`), custom-rendered (see below -- not `plotly.express`).
- Country ranking list with sub-scores, and a radar/bar comparison page (`pages/1_Country_Comparison.py`)
  across all 6 factors.
- World Bank data pipeline (`src/data_pipeline/fetch_worldbank.py`) written and working in principle, but
  **could not be executed live in this session** -- see "Blocked / needs attention" below.
- README.md written covering methodology, weights/rationale, sourcing, and limitations.
- GitHub Actions workflow for the scheduled World Bank refresh; `render.yaml` for deployment.

**Written companion product also done:** `briefs/gulf-ai-ambitions-and-geopolitical-risk.md` -- a full
analytic-tradecraft risk brief (BLUF, 6 numbered Key Judgments with confidence levels, a 3-hypothesis
alternative-analysis section, implications for Western strategic interests, and dated indicators to watch),
built strictly from the tracker's already-cited dataset -- no new unsourced claims. Also published as a
designed, standalone page: https://claude.ai/code/artifact/42522a4b-83ae-48ef-887f-caebdc87cf20 (currently
private; the project owner needs to share it from the page's share menu before linking it publicly from the
portfolio site). See "Sequencing decision" below for why this came before Phase 2.

**Phase 3 (country deep-dives) is also built**, ahead of Phase 2, per the same sequencing logic:
- `src/country_brief.py` -- templates a per-country BLUF + Key Judgments brief straight from the curated
  CSVs and computed scores. No LLM call at runtime, no free-generated text: every sentence is built from
  conditional templates filled with real cited values, so the brief is deterministic and stays correct
  automatically when a curated figure changes. Confidence tags come directly from each source row's
  `confidence` column.
- `src/pdf_export.py` -- renders the same brief to a downloadable PDF via `reportlab` (pure Python, no
  system deps, so it'll build fine on Render's free tier).
- `pages/2_Country_Deep_Dive.py` -- the Streamlit page: country selector, sub-score metrics, the
  BLUF/Key-Judgments brief, investment and compute-capacity timelines (every deal from the curated CSVs,
  including the excluded/aspirational ones, each labeled), sources list, and the PDF download button.
- **Real bug caught and fixed during testing**: Streamlit's markdown renderer treats a matched pair of `$`
  characters as a LaTeX math span (`$34.2bn ... $23.0bn` was rendering as a garbled math/code block instead
  of plain text). Fixed with an `esc()` helper in the page that escapes literal `$` before any generated
  text reaches `st.write`/`st.markdown`/`st.caption`/`st.info`. This only affects the Streamlit UI layer --
  the PDF export (reportlab) was never affected, since it uses its own markup, not Streamlit's markdown.
  Worth remembering if any future page renders generated text containing dollar amounts.

This reframes what "Phase 3" means from the original brief: rather than a UI feature bolted onto the
dashboard, the per-country brief is a second written-analysis output (8 short country briefs, same
BLUF/Key-Judgments format as the standalone Gulf-wide brief) that happens to live inside the dashboard --
which was the whole point of prioritizing it over Phase 2 and Phase 4 (see below).

**A third written product is also done**, per the "next content decision" from the sequencing discussion:
`briefs/sovereign-debt-and-political-instability.md` -- the "Policy Brief -- Sovereign Debt and Political
Instability" already listed as "Planned" on the portfolio, examining feedback loops between fiscal crises
and governance breakdown across Pakistan, Sri Lanka, and Bangladesh (with India, Nepal, Bhutan, Maldives,
and Afghanistan as comparative data points), same BLUF/Key-Judgments/alternative-analysis format as the
other two briefs. Published as a matching designed page:
https://claude.ai/code/artifact/8908bad9-96cc-48e4-8aa1-752d37f7968d (also private by default -- needs
sharing). **This one required pulling data from a second repository**: `rafaywaqar2004-lang/overeign-risk-index`
(the MENASA Risk Monitor's actual repo -- note the typo in the repo name itself, "overeign" not
"sovereign," worth knowing if searching for it later), cloned read-only the same way as the portfolio repo.
Every figure in this brief traces to that repo's `scored_data.csv` (composite scores, debt-to-GDP,
governance indicators) and `context_data.py` (the curated IMF-program histories, protest/collapse
narratives, and creditor-relationship summaries) -- which turned out to be a genuinely rich, well-sourced
dataset (14 historical-context entries for Pakistan alone, going back to 2013). This session only had
read access to that repo, so the brief's markdown source lives in this repo's `briefs/` folder with a note
that it should move to the MENASA repo when convenient -- flagged again in "Open questions" below.

**Nothing from the original 4-phase brief remains unbuilt.** See "Where things stand" above for Phase 4
(Scenario Explorer), built after being directly reconsidered -- "Sequencing decision" below still records
the original reasoning for deprioritizing it, kept as a record of the judgment call and how it changed.

## Sequencing decision: why the written brief (and then Phase 3) came before Phase 2

Checked the project owner's live portfolio (`rafaywaqar2004-lang/rafaywaqar-portfolio`) mid-project. Two
things came out of that worth recording:

1. **This dashboard already fulfills a project slot the owner had planned for himself** --
   "Gulf States Vision 2030 & AI Investment Tracker" (listed as `Planned -- Q3 2028`) -- and exceeds its
   original scope (8 countries instead of 2, an alignment-scoring methodology instead of a flat KPI
   tracker). Once deployed, that portfolio entry should point here instead of sitting as a separate
   "planned" placeholder; the placeholder year also reads as stale next to a 2026 copyright footer.
2. **A second planned entry, "Gulf AI Ambitions and Geopolitical Risk," was explicitly scoped by the owner
   himself as a *written* analytic narrative** meant to "pair with" the quantitative dashboard --
   i.e. he had already identified, independently, the exact gap this project's earlier discussion flagged:
   a dashboard alone doesn't demonstrate analytic-tradecraft writing (BLUF, confidence language,
   alternative-hypothesis reasoning), which is what CIA/CFR/CSIS/PIIE-type screening actually looks for,
   and which his 12+ published op-eds don't fully cover (journalistic register, not analytic-memo register).

Given that, the agreed plan was: **pause the dashboard roadmap and write the brief next**, rather than
proceeding straight to Phase 2. That's now done (see above). The agreed rule for what comes after: **build
Phase 2 (Policy Event Tracker) only if a future written piece specifically needs a sourced chip-policy
timeline to cite** -- treat it as an appendix the writing calls for, not a fixed next roadmap step. If no
such need arises, the next unit of work should be another written piece (the monthly MENA risk brief series
or the sovereign-debt/political-instability brief, both already listed as "Planned" on the portfolio) rather
than more dashboard features, on the logic that 2-3 written analytic pieces will do more for this specific
career goal than a third dashboard.

**Update after Phase 3 shipped:** when asked what should happen to Phases 2-4, the view given (and agreed
by the project owner, who said to proceed) was to rank them by how much each demonstrates analyst judgment
rather than build order:
- **Phase 4 (scenario reweighting toggle) is deprioritized, possibly permanently.** It's an interaction
  feature, not an analytic one -- wiring a slider to a recompute function doesn't demonstrate judgment the
  way the rest of this project does. Lowest priority; fine to skip if time is short.
  - **Reversed in a later session** when directly asked "why is Phase 4 skipped, won't it make this
    better" -- rather than just re-asserting the above, reconsidered on the merits: the MENASA Risk
    Monitor's own Scenario Explorer (live sliders + named shock presets) is one of that project's headline
    features, and this tracker had nothing analogous, which is a real inconsistency for anyone comparing
    the two projects directly. Built it; see "Where things stand" above. The original reasoning wasn't
    wrong exactly (it genuinely demonstrates less analytical judgment than the writing does), it was just
    incomplete -- it didn't weigh the feature-parity argument or the fact that the underlying weights were
    already isolated as named constants, making it a cheap addition, not a big one.
- **Phase 2 (Policy Event Tracker) stays on the "build when a brief needs it" rule above** -- not
  reprioritized, just reaffirmed.
- **Phase 3 (this session's work) turned out to be worth doing *before* Phase 2 after all**, once reframed:
  a per-country downloadable PDF brief in the same BLUF/Key-Judgments format as the standalone brief isn't
  really a dashboard feature, it's 8 more written-analysis outputs with a UI wrapper. That reframing is why
  it jumped the queue -- see "Where things stand" above for what got built.

## Key decisions made, and why

1. **Two sub-scores (US Integration Depth, China Exposure Depth) roll up into a derived Net Alignment
   Score**, rather than one flat weighted index. This was the project owner's explicit choice after I laid
   out the tradeoff: a single directional score would flatten the actual story (Gulf states maximizing ties
   with *both* blocs simultaneously -- the UAE has the region's best US chip-export status *and* runs
   Huawei radio equipment on live 5G networks). A non-directional pure-capability index would lose the
   geopolitical signal entirely. Two sub-scores plus a derived headline number gets both: one number for
   the map/ranking view, two components for the "why" in the comparison view.
   - *Caveat*: **the derived score's midpoint (50) is genuinely ambiguous** -- it means "hedging
     successfully on both fronts" for a country that maxes out both axes, and "not very engaged on either
     front" for a country that does little on both. The app's UI explicitly warns about this in the "read
     this before the numbers" expander on the overview page. Don't let a future revision silently drop
     that caveat.

2. **6 factors, not 8-10**, kept as close to the original brief's list as research supported. Considered
   folding compute capacity into investment volume (they correlate -- same PIF/G42 deals often drive both)
   but kept them separate since a country's disclosed capital and its physical buildout aren't always in
   lockstep, and an analyst audience would want to see both facts independently.

3. **Fixed-ceiling log-scale normalization, not dataset-relative min-max**, for the two dollar/MW factors.
   Caught this as a real bug during testing, not a hypothetical: with only Saudi Arabia and the UAE having
   any disclosed investment/compute figure, min-max normalization stretched a real-but-modest gap ($34.2bn
   vs $15.2bn) into an artificial 100-vs-0 spread. Fixed the ceilings to sourced, documented anchors
   (`INVESTMENT_CEILING_USD_BN = 50`, `COMPUTE_CEILING_MW = 6000` in `src/scoring.py`) instead. This will
   need periodic revisiting as new deals get disclosed and the ceilings start to feel dated -- if Saudi
   Arabia or the UAE blow past $50bn/6000MW in scored (not aspirational) deals, raise the ceiling and note
   the change here.

4. **Governance maturity and non-oil diversification are context factors, shown separately, not folded
   into the alignment score.** A mature AI regulator or a diversified economy doesn't inherently signal
   pro-US or pro-China bloc alignment -- they're state-capacity signals, not alignment signals. This was my
   call as the analyst, not something the project owner was asked to sign off on; flag if they'd rather see
   it folded in.

5. **Custom choropleth renderer instead of `plotly.express.choropleth`.** Discovered during testing (not
   assumed) that Plotly's built-in geo trace fetches its world-atlas topojson from `cdn.plot.ly` at render
   time regardless of custom-geojson/visible=False settings, in the Plotly.js version this project runs
   against (`plotly==7.0.0` as tested). That's exactly the kind of external runtime dependency the brief
   ruled out ArcGIS for. Wrote `src/mapping.py` to draw filled polygons directly from a bundled, pre-filtered
   GeoJSON (originally `data/geo/gulf_countries.geojson`, later rebuilt as `data/geo/region_countries.geojson`
   to add regional-context countries -- see "Where things stand" above -- sourced from the public-domain
   `datasets/geo-countries` Natural Earth derivative) with zero runtime network calls -- verified working in
   a fully network-restricted sandbox. This is a more robust choice for a Render deployment regardless of
   the sandbox restriction that surfaced it.

6. **Data-thinness handling**: missing curated figures are `N/A`/excluded, never estimated or defaulted to
   zero. The US Integration Depth weighted average renormalizes over whichever of its 3 inputs are
   available for a given country (tracked in `us_integration_factors_available`); a country with zero
   available inputs shows `N/A` and renders gray on the map rather than silently scoring as the worst case.

## Research grounding (what's solid vs. thin)

**Well-sourced, high confidence:** Saudi Arabia and UAE across nearly all factors -- the Nov 2025 HUMAIN/G42
chip authorization, the Jul 2026 UAE BIS Country Group A:5 upgrade, HUMAIN/PIF and G42/MGX investment deals,
SDAIA and the UAE's AI Office/Regulatory Intelligence Office, Kuwait's 2025 multi-operator Huawei 5G-A
deployment, Pakistan's Jul 2025 cabinet-approved National AI Policy and its decades-deep Huawei/CPEC
telecom integration, Turkey's Huawei/Turkcell partnership continuing through MWC 2025.

**Genuinely thin, flagged in the data files as `Low` confidence:** Qatar, Bahrain, Kuwait, and Oman's
export-control tier (no BIS rule/entity authorization found for any of them -- scored via analyst judgment
against a documented rubric, not a real designation); Turkey's export-control tier and governance-maturity
score (no fresh 2025/2026 source located this session -- general awareness of Turkey's TÜBİTAK-era AI
strategy was used but not re-verified); Saudi Arabia's and Bahrain's Chinese-tech-penetration score
(regional-level sourcing rather than country-specific this pass). These are exactly the rows a critical
reader (or a future research pass) should hit first.

## Blocked / needs attention

- **The World Bank data pipeline could not be run live in this development session.** This sandbox's
  network egress policy blocks `api.worldbank.org` (confirmed via the proxy status endpoint: `403` /
  "policy denial," not a code bug). The script (`src/data_pipeline/fetch_worldbank.py`) is written, handles
  failures gracefully (writes `N/A` rather than crashing, which is what's currently checked into
  `data/worldbank/`), and should work as-is once run somewhere with normal internet access -- a GitHub
  Actions runner, Render, or the project owner's own machine. **First thing to verify after this reaches an
  unrestricted environment**: run `python src/data_pipeline/fetch_worldbank.py` and confirm
  `data/worldbank/worldbank_latest.csv` populates with real values, then re-run `PYTHONPATH=src python
  src/scoring.py` to refresh `data/computed/composite_scores.csv`.
- Similarly, `cdn.plot.ly` was blocked in this sandbox, which is what surfaced the choropleth issue (see
  decision #5) -- worth a quick sanity check that the custom renderer still looks right once viewed from an
  unrestricted environment, though nothing about it depends on that environment being restricted.

**A fourth written product, the first of a series, is also done:**
`briefs/mena-geopolitical-risk-brief-issue-01.md` -- Issue No. 1 of the "MENA Geopolitical Risk Brief Series"
(the last remaining "Planned" written piece on the portfolio). Different shape from the other three briefs
deliberately: a monthly digest format (regional snapshot stats, a risk-movers table, 3 spotlighted conflicts,
a shorter "Also Watching" roundup, an outlook section that explicitly carries open questions into "Issue
No. 2") rather than a single-topic analytic argument, because a recurring series and a one-off assessment
are different products and shouldn't be forced into the same template. Published as a matching page:
https://claude.ai/code/artifact/9203fd21-1872-464b-94cb-b72b3b9143a7 (also private by default).

Grounded the same way as the sovereign-debt brief -- pulled from `rafaywaqar2004-lang/overeign-risk-index`,
this time its `LIVE_CONFLICTS` list in `context_data.py` (13 tracked conflicts, each with real casualty/
economic-impact figures and sources) plus `scored_data.csv` for the regional snapshot and risk-mover
figures (computed fresh: regional average, score spread, and conflict-exposure share, none of which existed
as a single number anywhere in the source repo -- these were derived directly from the raw per-country rows
via a quick Python pass, then cited back to the underlying dataset). Scoped to the 20 MENA countries only
(excluded the South Asia and Horn of Africa conflicts in the same dataset, noted explicitly rather than
silently dropped, since the portfolio's own description names this series "MENA," not "MENASA").

**With this, all four "Planned" written pieces originally listed on the portfolio are now written**
(Gulf AI Ambitions, the sovereign-debt/political-instability brief, and this MENA series' first issue --
plus the Gulf dashboard itself fulfilling the fifth "Planned" entry). The portfolio site itself still shows
all of them as "Planned" until the project owner updates it -- see "Open questions" below, item 4.

## Open questions for the project owner

1. **Resolved this session.** China Exposure Depth now blends Chinese telecom penetration with a new,
   independently-researched Chinese AI/cloud/digital-ties factor (50/50, renormalized when one is missing).
   See "Where things stand" above for the research method, the specific country findings, and the resulting
   score movements. The new factor's sourcing is thinner than the telecom factor it complements (3 of 17
   rows are `Low` confidence) -- worth a follow-up pass if this project is ever shown to a critical reader,
   but not a blocking gap.
2. **Partially resolved this session** -- see "Where things stand" above. Turkey's governance score and
   Saudi Arabia's China-penetration score are now `Medium` confidence with fresh sources; Bahrain's
   China-penetration score was corrected outright. **Still open:** Qatar/Bahrain/Kuwait/Oman's and Turkey's
   export-control tier remain `Low` confidence, blocked on checking BIS's own Country Group table (network
   access to `bis.gov` was blocked in this session -- worth trying again in an unrestricted environment
   before presenting this project to a critical reader).
3. Confirm the fixed normalization ceilings ($50bn / 6000MW) still feel right, or would you rather they be
   configurable/documented differently (e.g. tied to a specific benchmark like "2x the current leader"
   instead of a static number)?
4. **Resolved this session.** The tracker is deployed (https://oaqjp-final-project-emb-ai-c8u6.onrender.com),
   all three brief artifacts are shared publicly, and the portfolio's 4 relevant cards are updated and live.
   A session was granted push access to `rafaywaqar-portfolio` directly (via `add_repo` with `access:
   "push"`) rather than working around read-only access -- worth remembering that's available if a similar
   situation comes up again with another of the project owner's repos (e.g. the MENASA repo, item 5 below).
5. **Resolved.** Both South-Asia/MENA briefs moved into the actual MENASA Risk Monitor repo
   (`rafaywaqar2004-lang/overeign-risk-index`, `briefs/` folder there) via the same `add_repo(access="push")`
   approach that worked for the portfolio in item 4 -- confirming that pattern generalizes to any of the
   project owner's repos, not just the one it happened to be tried on first. Removed from this repo's own
   `briefs/` folder (`git rm`) rather than left duplicated; this repo's `briefs/` now holds only its own
   companion piece, `gulf-ai-ambitions-and-geopolitical-risk.md`.
6. **Issue No. 2 of the MENA series** needs an actual month to pass with new developments before it's worth
   writing -- it's a monthly series, not something to produce back-to-back with Issue No. 1. When it's time,
   its outlook section already sets the agenda: the Iran-Israel-US war's ceasefire durability, the Houthi-
   Saudi blockade's status, Turkey's risk trajectory (flagged but not analyzed in Issue No. 1), and Syria's
   investment-versus-risk-score divergence.
7. **With all four originally-planned written pieces done, all 4 dashboard phases built, and everything
   deployed and shared**, the tracker itself is feature-complete against its original brief. The next
   session's highest-value work is closing the confidence gaps (open question 2 above) -- specifically the
   still-unverified export-control tier for Qatar, Bahrain, Kuwait, Oman, and Turkey, which needs a session
   that can actually reach `bis.gov`. A fifth written piece is a reasonable option too, but depth on what
   already exists is the stronger use of time at this point, not more breadth.
8. **Resolved in a later session.** `src/scoring.py`'s `__main__` block now calls
   `append_history_snapshot()` on every refresh, appending a dated row per country to
   `data/computed/composite_scores_history.csv` (idempotent per day). Score Momentum, historical trend
   charts, and a real 12-Month Outlook are still not built (there isn't yet enough history accumulated to
   make them meaningful), but the data collection that unblocks them going forward is now in place and has
   been running for several sessions.

## Environment note for whoever picks this up next

This session's sandbox blocked `api.worldbank.org` and `cdn.plot.ly` at the network-policy level (both
confirmed via `curl $HTTPS_PROXY/__agentproxy/status`, not assumed) -- neither is expected to be an issue on
Render or in GitHub Actions, which have normal outbound internet access. If World Bank data still doesn't
populate after deployment, that's a real bug worth investigating, not the same known/expected block seen
here.
