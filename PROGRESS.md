# Progress Log -- Gulf AI & Tech-Bloc Alignment Tracker

Read this first if picking up the project cold, whether that's a fresh Claude session or the project
owner returning after a break. It's meant to make re-explaining the project unnecessary.

## Where things stand

**Latest session: a visual-design pass on the Streamlit app itself, prompted by direct user feedback
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
   GeoJSON (`data/geo/gulf_countries.geojson`, sourced from the public-domain `datasets/geo-countries`
   Natural Earth derivative) with zero runtime network calls -- verified working in a fully
   network-restricted sandbox. This is a more robust choice for a Render deployment regardless of the
   sandbox restriction that surfaced it.

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

1. **Should China Exposure Depth stay a single-factor axis, or is it worth the research time to add a
   second China-tie factor** (e.g. disclosed Chinese AI model deployments, CPEC/BRI-style digital
   financing) before Phase 2? Flagged as a known limitation in the README; not blocking, but worth a
   decision before this is shown to anyone who'd press on it.
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
5. **Move both South-Asia/MENA briefs into the actual MENASA Risk Monitor repo**
   (`rafaywaqar2004-lang/overeign-risk-index`) -- `briefs/sovereign-debt-and-political-instability.md` and
   `briefs/mena-geopolitical-risk-brief-issue-01.md` both still live in this repo only because it's the one
   a session had write access to at the time. Given item 4 above worked by requesting push access directly,
   the same approach should work here too -- `add_repo(owner=..., repo="overeign-risk-index", access="push")`
   -- rather than continuing to treat this as blocked.
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

## Environment note for whoever picks this up next

This session's sandbox blocked `api.worldbank.org` and `cdn.plot.ly` at the network-policy level (both
confirmed via `curl $HTTPS_PROXY/__agentproxy/status`, not assumed) -- neither is expected to be an issue on
Render or in GitHub Actions, which have normal outbound internet access. If World Bank data still doesn't
populate after deployment, that's a real bug worth investigating, not the same known/expected block seen
here.
