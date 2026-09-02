# Progress Log -- Gulf AI & Tech-Bloc Alignment Tracker

Read this first if picking up the project cold, whether that's a fresh Claude session or the project
owner returning after a break. It's meant to make re-explaining the project unnecessary.

## Where things stand

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

**Not yet started:** Phase 2 (Policy Event Tracker), Phase 3 (country deep-dives + PDF export), Phase 4
(scenario reweighting toggle). Build in that order per the original brief.

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

## Open questions for the project owner

1. **Should China Exposure Depth stay a single-factor axis, or is it worth the research time to add a
   second China-tie factor** (e.g. disclosed Chinese AI model deployments, CPEC/BRI-style digital
   financing) before Phase 2? Flagged as a known limitation in the README; not blocking, but worth a
   decision before this is shown to anyone who'd press on it.
2. **The `Low`-confidence rows above are the biggest credibility risk in the current build.** Worth a
   dedicated research pass on Qatar/Bahrain/Kuwait/Oman's export-control status and Turkey's current AI
   governance apparatus before presenting this project, or worth flagging live as "known gap, actively
   being researched" if shown sooner.
3. Confirm the fixed normalization ceilings ($50bn / 6000MW) still feel right, or would you rather they be
   configurable/documented differently (e.g. tied to a specific benchmark like "2x the current leader"
   instead of a static number)?
4. Ready to move to **Phase 2 (Policy Event Tracker)** next, per the original build order, unless you'd
   rather prioritize closing the confidence gaps above first.

## Environment note for whoever picks this up next

This session's sandbox blocked `api.worldbank.org` and `cdn.plot.ly` at the network-policy level (both
confirmed via `curl $HTTPS_PROXY/__agentproxy/status`, not assumed) -- neither is expected to be an issue on
Render or in GitHub Actions, which have normal outbound internet access. If World Bank data still doesn't
populate after deployment, that's a real bug worth investigating, not the same known/expected block seen
here.
