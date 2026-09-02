"""
Strategic Risk -- rates every tracked country on 4 risk dimensions derived
transparently from this tracker's own existing scored data (see
src/strategic_risk.py), then gives qualified investor/corporate/policy
transmission-channel implications for a selected country. Two dimensions
named in the original brief -- semiconductor dependency, geopolitical
volatility -- are explicitly not rated per-country here; see the page's
own explanation for why.
"""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from constants import COUNTRIES  # noqa: E402
from country_brief import load_curated  # noqa: E402
from scoring import build_composite  # noqa: E402
from strategic_risk_engine import assess_all, assess_country  # noqa: E402
from ui import inject_base_css, page_header, confidence_pill, footer, RED, GOLD, GREEN, GRAY  # noqa: E402

_LEVEL_COLOR = {"High": RED, "Moderate": GOLD, "Low": GREEN, "Insufficient data": GRAY}


@st.cache_data(ttl=3600)
def _composite() -> pd.DataFrame:
    return build_composite()


@st.cache_data(ttl=3600)
def _curated() -> dict[str, pd.DataFrame]:
    return load_curated()


def _level_badge(level: str) -> str:
    color = _LEVEL_COLOR.get(level, GRAY)
    return f'<span style="color:{color}; font-weight:700; font-family:\'IBM Plex Mono\', monospace; font-size:0.78rem; text-transform:uppercase;">{level}</span>'


def _transmission_channels(row: pd.Series) -> dict[str, str]:
    """Transmission-channel framing distinct from Country Deep Dive's
    Strategic Implications -- focused specifically on *how* a risk would
    propagate, per this project's own scored factors. Deterministic,
    branches on the country's actual values, never a recommendation."""
    us_exposure = row["us_tier_raw"]
    china_exposure = row["china_exposure_depth"]
    country = row["country"]

    if pd.isna(us_exposure) and pd.isna(china_exposure):
        note = f"{country} has insufficient disclosed data to trace a specific risk transmission channel."
        return {"investor": note, "corporate": note, "policy": note}

    investor_parts = []
    if pd.notna(us_exposure) and us_exposure >= 3:
        investor_parts.append(
            f"greater dependence on {country}'s US-controlled advanced-chip access (tier {us_exposure:.0f}/5) may "
            "increase exposure to future US export-control policy changes specifically"
        )
    if pd.notna(china_exposure) and china_exposure >= 50:
        investor_parts.append(
            f"China Exposure Depth of {china_exposure:.0f}/100 carries transmission-channel risk from a future "
            "US secondary-sanctions or entity-list action targeting Chinese vendors operating in-country"
        )
    investor = (
        ("; ".join(investor_parts) + ".").capitalize() if investor_parts else
        f"{country} shows limited disclosed exposure on either axis -- fewer identifiable single-bloc-policy transmission channels than a more deeply engaged peer."
    )

    corporate = (
        f"Corporates with {country}-based operations or supply chains should map dependency on any single "
        "chip-access channel (US export-control tier) or telecom/cloud vendor relationship (Chinese exposure) "
        "identified above -- a policy shock on either side would propagate through whichever channel the "
        "operation actually depends on, not an abstract country-level score."
    )

    if pd.notna(us_exposure) and us_exposure >= 3:
        policy = (
            f"{country} holds a disclosed bilateral arrangement (tier {us_exposure:.0f}/5) -- any US decision to "
            "tighten, broaden, or condition that arrangement has a directly traceable effect on this country's "
            "position, not just a regional signaling effect."
        )
    else:
        policy = (
            f"{country} has no disclosed bilateral US chip-access arrangement -- a first authorization would be "
            "a first-order, immediately scoreable policy event, and its absence itself is a policy-relevant "
            "signal (see the Policy Event Tracker and Watch Next for what's pending)."
        )

    return {"investor": investor, "corporate": corporate, "policy": policy}


def main() -> None:
    inject_base_css()
    page_header(
        "Strategic Risk",
        "Risk dimensions derived transparently from this tracker's own scored data -- never a separately invented risk score.",
        meta=["DATA AS OF: SEPTEMBER 2026"],
    )

    with st.expander("What this page does and doesn't rate", expanded=False):
        st.markdown(
            """
Four dimensions are rated **Low / Moderate / High / Insufficient data**, each traced to a specific number
already computed elsewhere in this tracker:

- **US Policy Exposure** -- from the US export-control tier. A country with a broad, disclosed bilateral
  arrangement has more to lose if that arrangement is tightened or reversed than a country with none.
- **China Exposure** -- directly, this tracker's own China Exposure Depth score.
- **Infrastructure Execution Risk** -- the share of a country's counted, disclosed AI compute capacity that
  is still under development or a stated target, not yet operating.
- **Measurement Confidence Risk** -- how much of a country's own scored position rests on Low- or
  Medium-confidence curated data, pulled directly from this project's own `confidence` columns.

**Two dimensions named in early drafts of this page's brief are deliberately not rated per-country:**
"semiconductor dependency" would just restate US Policy Exposure and China Exposure in different words --
this tracker's own two axes already measure exactly that. "Geopolitical volatility" would require a
political judgment this project's curated data doesn't support without guessing, so it is not rated here
rather than invented.
            """
        )

    composite = _composite()
    curated = _curated()

    st.subheader("Regional risk matrix")
    matrix = assess_all(composite, curated)
    display_matrix = matrix.copy()
    for col in display_matrix.columns[1:]:
        display_matrix[col] = display_matrix[col].map(lambda level: _level_badge(level))
    st.write(
        display_matrix.to_html(escape=False, index=False),
        unsafe_allow_html=True,
    )
    st.caption(
        "Hover no cell needed -- each rating's specific basis (the real number behind it) is shown in the "
        "per-country detail below. This matrix is a summary view, not the full evidence."
    )

    st.divider()
    st.subheader("Per-country detail")
    country = st.selectbox("Country", options=list(COUNTRIES.keys()))
    row = composite[composite["country"] == country].iloc[0]
    dims = assess_country(row, curated)

    for d in dims:
        with st.container(border=True):
            c1, c2 = st.columns([1, 3])
            with c1:
                st.markdown(f"**{d.name}**")
                st.markdown(_level_badge(d.level), unsafe_allow_html=True)
            with c2:
                st.caption(d.basis)

    st.divider()
    st.subheader("Transmission-channel implications")
    channels = _transmission_channels(row)
    tc1, tc2, tc3 = st.columns(3)
    with tc1:
        st.markdown("**Investor**")
        st.caption(channels["investor"])
    with tc2:
        st.markdown("**Corporate**")
        st.caption(channels["corporate"])
    with tc3:
        st.markdown("**Policy**")
        st.caption(channels["policy"])
    st.caption(
        "Qualified analytical framing tracing a specific transmission channel, not a recommendation to buy, "
        "sell, or adopt any specific position. See the Country Deep Dive page for this country's full "
        "Strategic Implications section."
    )

    footer()


if __name__ == "__main__":
    main()
