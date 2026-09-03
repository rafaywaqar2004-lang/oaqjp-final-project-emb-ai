"""
Sovereign AI Investment Flow Tracker -- tracks Gulf-state sovereign-fund /
government-directed AI and tech capital flows and which bloc (US or China)
the destination lands in (see src/investment_flow_engine.py for the scoring
logic and its two explicit judgment calls: same-country "sovereign launch"
deals are excluded from cross-border flow metrics, and the Capital
Alignment Ratio is computed strictly over bloc_affiliation in
{"US", "China"} -- "US-aligned" deals are shown but excluded from that
ratio). This is a genuinely different signal from this tracker's existing
composite Net Alignment Score -- see the module docstring for how the two
relate.
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from constants import CURATED_DIR  # noqa: E402
from investment_flow_engine import (  # noqa: E402
    bloc_totals, by_quarter, by_sector, capital_alignment_ratio, cross_border_flows,
    domestic_sovereign_deals, load_flows, per_country_summary, sankey_data,
    unconfirmed_value_count, with_parsed_value,
)
from ui import inject_base_css, page_header, key_findings_card, kpi_card, kpi_row, footer, BLUE, RED, GRAY, NAVY  # noqa: E402

FLOWS_CSV_PATH = Path(CURATED_DIR) / "investment_flows.csv"

_BLOC_COLOR = {"US": BLUE, "China": RED, "US-aligned": "#8FB6DC", "Neutral": GRAY}


@st.cache_data(ttl=3600)
def _flows() -> pd.DataFrame:
    return load_flows()


def _key_findings(df: pd.DataFrame) -> tuple[str, str, str]:
    totals = bloc_totals(df)
    us_total = totals.get("US", 0.0)
    china_total = totals.get("China", 0.0)
    ratio = capital_alignment_ratio(us_total, china_total)
    unconfirmed = unconfirmed_value_count(df)
    domestic = domestic_sovereign_deals(df)
    domestic_total = with_parsed_value(domestic)["deal_value_usd_millions_parsed"].sum(min_count=1)

    if ratio is None:
        bluf = "No cross-border deal in the tracked set currently has both a confirmed value and a US/China bloc label, so a Capital Alignment Ratio cannot be computed yet."
    else:
        bluf = (
            f"Of {len(cross_border_flows(df))} tracked cross-border deals, confirmed-value flows split "
            f"${us_total:,.0f}M US-bound vs. ${china_total:,.0f}M China-bound -- a Capital Alignment Ratio "
            f"of {ratio:.0f}%. {unconfirmed} of {len(df)} tracked deals have no confirmed dollar value and are "
            "excluded from every total above, not treated as zero."
        )
    key_judgment = (
        f"Saudi Arabia's HUMAIN sovereign AI launch (${domestic_total:,.0f}M, domestic buildout) is tracked "
        "separately from cross-border flows above -- folding a single large domestic deal into a 'capital flow "
        "direction' metric would be a category error, not a data point."
        if pd.notna(domestic_total) and domestic_total > 0
        else "Saudi Arabia's HUMAIN sovereign AI launch is tracked separately from cross-border flows above as a "
        "domestic buildout, not a cross-border flow -- its own deal_value_usd_millions is currently RESEARCH_NEEDED "
        "(the commonly-cited $40bn figure was investigated this session and found to be misattributed to an "
        "earlier, unrelated PIF plan, not HUMAIN's own launch -- see the deal-level table's notes column)."
    )
    why = (
        "A country's Capital Alignment Ratio can diverge from its existing Net Alignment Score -- e.g. a country "
        "scoring 'hedging' on tech-policy alignment could still show its sovereign capital flowing overwhelmingly "
        "to one bloc, or vice versa. See the positioning scatter below for exactly where each country falls."
    )
    return bluf, key_judgment, why


def _sankey_figure(df: pd.DataFrame) -> go.Figure:
    sd = sankey_data(df)
    fig = go.Figure(data=[go.Sankey(
        node=dict(pad=20, thickness=18, label=sd["labels"], color=NAVY),
        link=dict(
            source=sd["links"]["source"], target=sd["links"]["target"], value=sd["links"]["value"],
            color=sd["links"]["color"], label=sd["links"]["label"],
        ),
    )])
    fig.update_layout(height=420, margin=dict(t=10, b=10))
    return fig


def _quarterly_bar(df: pd.DataFrame) -> go.Figure:
    q = by_quarter(df)
    fig = go.Figure()
    fig.add_trace(go.Bar(x=q["quarter"], y=q["US"], name="US-bound", marker_color=BLUE))
    fig.add_trace(go.Bar(x=q["quarter"], y=q["China"], name="China-bound", marker_color=RED))
    fig.update_layout(barmode="stack", height=380, margin=dict(t=20), yaxis_title="Confirmed deal value ($M)")
    return fig


def _sector_pie(df: pd.DataFrame) -> go.Figure:
    s = by_sector(df)
    fig = px.pie(s, names="sector", values="total_usd_millions", hole=0.4)
    fig.update_layout(height=380, margin=dict(t=20))
    return fig


def _capital_ratio_bar(summary: pd.DataFrame) -> go.Figure:
    scored = summary.dropna(subset=["capital_alignment_ratio"]).sort_values("capital_alignment_ratio")
    fig = px.bar(
        scored, x="capital_alignment_ratio", y="country", orientation="h",
        color="capital_alignment_ratio", color_continuous_scale=[RED, "#F0E6C8", BLUE], range_color=(0, 100),
        labels={"capital_alignment_ratio": "Capital Alignment Ratio (%)", "country": ""},
    )
    fig.update_layout(height=360, margin=dict(t=20), coloraxis_showscale=False)
    return fig


def _positioning_scatter(summary: pd.DataFrame) -> go.Figure:
    scored = summary.dropna(subset=["capital_alignment_ratio", "net_alignment_score"])
    fig = go.Figure()
    fig.add_shape(type="line", x0=50, x1=50, y0=-4, y1=104, line=dict(color=GRAY, width=1, dash="dot"))
    fig.add_shape(type="line", x0=-4, x1=104, y0=50, y1=50, line=dict(color=GRAY, width=1, dash="dot"))
    fig.update_layout(annotations=[
        dict(x=25, y=97, text="CHINA-ALIGNED SCORE<br>BUT US CAPITAL", showarrow=False, font=dict(size=9, color=GRAY)),
        dict(x=75, y=97, text="ALIGNED ON PAPER<br>AND IN CAPITAL", showarrow=False, font=dict(size=9, color=GRAY)),
        dict(x=25, y=3, text="CONSISTENTLY<br>CHINA-ALIGNED", showarrow=False, font=dict(size=9, color=GRAY)),
        dict(x=75, y=3, text="US-ALIGNED SCORE<br>BUT CHINESE CAPITAL", showarrow=False, font=dict(size=9, color=GRAY)),
    ])
    fig.add_trace(go.Scatter(
        x=scored["net_alignment_score"], y=scored["capital_alignment_ratio"], mode="markers+text",
        text=scored["country"], textposition="top center", textfont=dict(size=9, color=GRAY),
        marker=dict(size=13, color=NAVY, line=dict(width=1, color="white")),
        hovertemplate="<b>%{text}</b><br>Net Alignment: %{x:.0f}<br>Capital Alignment: %{y:.0f}%<extra></extra>",
    ))
    fig.update_xaxes(title="Net Alignment Score (0=China-leaning, 100=US-integrated)", range=[-4, 104])
    fig.update_yaxes(title="Capital Alignment Ratio (%, 0=all China, 100=all US)", range=[-4, 104])
    fig.update_layout(height=520, plot_bgcolor="white", margin=dict(t=30))
    return fig


def _deal_table(df: pd.DataFrame) -> None:
    st.subheader("Deal-Level Table")
    c1, c2, c3 = st.columns(3)
    with c1:
        countries = st.multiselect("Source country", options=sorted(df["source_country"].unique()))
    with c2:
        blocs = st.multiselect("Bloc affiliation", options=sorted(df["bloc_affiliation"].unique()))
    with c3:
        sectors = st.multiselect("Sector", options=sorted(df["sector"].unique()))
    deal_types = st.multiselect("Deal type", options=sorted(df["deal_type"].unique()))

    filtered = df.copy()
    if countries:
        filtered = filtered[filtered["source_country"].isin(countries)]
    if blocs:
        filtered = filtered[filtered["bloc_affiliation"].isin(blocs)]
    if sectors:
        filtered = filtered[filtered["sector"].isin(sectors)]
    if deal_types:
        filtered = filtered[filtered["deal_type"].isin(deal_types)]

    display_cols = [
        "date", "source_fund", "source_country", "destination_company", "destination_country",
        "sector", "deal_value_usd_millions", "bloc_affiliation", "deal_type", "source_url",
    ]
    st.dataframe(
        filtered[display_cols].rename(columns={
            "date": "Date", "source_fund": "Source Fund", "source_country": "Source Country",
            "destination_company": "Destination Company", "destination_country": "Destination Country",
            "sector": "Sector", "deal_value_usd_millions": "Deal Value ($M)",
            "bloc_affiliation": "Bloc", "deal_type": "Deal Type", "source_url": "Source URL",
        }),
        hide_index=True, use_container_width=True,
        column_config={"Source URL": st.column_config.LinkColumn()},
    )
    st.download_button(
        "Download filtered deals (CSV)", data=filtered.to_csv(index=False),
        file_name="investment_flows_filtered.csv", mime="text/csv",
    )


def _admin_data_editor() -> None:
    with st.expander("Edit Investment Data (admin)"):
        st.caption(
            "Edits here write directly to data/curated/investment_flows.csv on this running server. On most "
            "hosted deployments (e.g. Render, Streamlit Community Cloud) the filesystem is ephemeral -- a "
            "redeploy or restart will discard any change made here that wasn't also committed to the "
            "repository. Treat this as a convenience for local editing/review, not a permanent data store."
        )
        raw = pd.read_csv(FLOWS_CSV_PATH, dtype={"deal_id": str})
        edited = st.data_editor(raw, num_rows="dynamic", use_container_width=True, key="investment_flows_editor")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Save changes to investment_flows.csv"):
                try:
                    edited.to_csv(FLOWS_CSV_PATH, index=False)
                    st.cache_data.clear()
                    st.success("Saved. Reload the page to see the recalculated totals.")
                except OSError as e:
                    st.error(f"Could not write to {FLOWS_CSV_PATH}: {e}")
        with c2:
            st.caption("To delete a row: select it in the table above (row checkbox), press Delete, then Save.")

        st.markdown("**Add a new deal**")
        with st.form("add_deal_form"):
            fc1, fc2, fc3 = st.columns(3)
            with fc1:
                new_id = st.text_input("deal_id")
                new_date = st.text_input("date (YYYY-MM)")
                new_source_fund = st.text_input("source_fund")
            with fc2:
                new_source_country = st.text_input("source_country")
                new_destination_company = st.text_input("destination_company")
                new_destination_country = st.text_input("destination_country")
            with fc3:
                new_sector = st.text_input("sector")
                new_value = st.text_input("deal_value_usd_millions (or RESEARCH_NEEDED)")
                new_bloc = st.selectbox("bloc_affiliation", options=["US", "China", "US-aligned", "Neutral"])
            new_deal_type = st.text_input("deal_type")
            new_source_url = st.text_input("source_url")
            new_notes = st.text_area("notes")
            submitted = st.form_submit_button("Add deal")
            if submitted:
                if not new_id or not new_source_country:
                    st.error("deal_id and source_country are required.")
                else:
                    new_row = pd.DataFrame([{
                        "deal_id": new_id, "date": new_date or "RESEARCH_NEEDED", "source_fund": new_source_fund,
                        "source_country": new_source_country, "destination_company": new_destination_company,
                        "destination_country": new_destination_country, "destination_country_iso": "RESEARCH_NEEDED",
                        "sector": new_sector, "deal_value_usd_millions": new_value or "RESEARCH_NEEDED",
                        "bloc_affiliation": new_bloc, "deal_type": new_deal_type,
                        "source_url": new_source_url or "RESEARCH_NEEDED", "notes": new_notes,
                        "last_updated": pd.Timestamp.today().date().isoformat(),
                    }])
                    updated = pd.concat([raw, new_row], ignore_index=True)
                    try:
                        updated.to_csv(FLOWS_CSV_PATH, index=False)
                        st.cache_data.clear()
                        st.success(f"Added deal {new_id}. Reload the page to see it reflected.")
                    except OSError as e:
                        st.error(f"Could not write to {FLOWS_CSV_PATH}: {e}")


def investment_flows_section(country: str | None = None) -> None:
    """Renders the Investment Flows sub-section for one country -- used by
    both this page (country=None, full dataset) and Country Deep Dive
    (country=<name>). Kept as one function so the two pages can never drift
    apart on what counts as a country's tracked investment."""
    df = _flows()
    if country is not None:
        df = df[df["source_country"] == country]

    if df.empty:
        st.caption(f"No tracked investment for {country}." if country else "No tracked investment on file.")
        return

    cb = cross_border_flows(df)
    totals = bloc_totals(df)
    us_total = totals.get("US", 0.0)
    china_total = totals.get("China", 0.0)
    ratio = capital_alignment_ratio(us_total, china_total)

    st.markdown(f"**\\${us_total:,.0f}M** US-bound &middot; **\\${china_total:,.0f}M** China-bound "
                f"(confirmed-value cross-border deals only)")
    if ratio is not None:
        st.markdown(f"**Capital Alignment Ratio: {ratio:.0f}%** ({'more US-bound' if ratio >= 50 else 'more China-bound'} capital)")
    else:
        st.caption("Insufficient confirmed-value cross-border deals to compute a Capital Alignment Ratio.")

    domestic = domestic_sovereign_deals(df)
    if not domestic.empty:
        dom_total = with_parsed_value(domestic)["deal_value_usd_millions_parsed"].sum(min_count=1)
        st.caption(
            f"Plus \\${dom_total:,.0f}M in domestic sovereign buildout (tracked separately, not a cross-border flow)."
            if pd.notna(dom_total) else "Plus at least one domestic sovereign buildout deal with an unconfirmed value."
        )

    with st.container(border=True):
        st.dataframe(
            df[["date", "destination_company", "destination_country", "sector", "deal_value_usd_millions", "bloc_affiliation", "deal_type"]]
            .rename(columns={
                "date": "Date", "destination_company": "Destination", "destination_country": "Destination Country",
                "sector": "Sector", "deal_value_usd_millions": "Value ($M)", "bloc_affiliation": "Bloc", "deal_type": "Type",
            }),
            hide_index=True, use_container_width=True,
        )

    if not cb.empty:
        st.plotly_chart(_sankey_figure(df), use_container_width=True)

    st.caption("Investment data is manually curated. See Sources & Data for methodology.")


def main() -> None:
    inject_base_css()

    with st.spinner("Loading investment data..."):
        try:
            df = _flows()
        except (FileNotFoundError, KeyError) as e:
            page_header(
                "Sovereign AI Investment Flow Tracker",
                "Gulf-state sovereign-fund and government-directed AI/tech capital flows, by destination bloc",
                meta=["MANUALLY CURATED"],
            )
            st.error(f"Could not load investment flow data: {e}")
            return

    page_header(
        "Sovereign AI Investment Flow Tracker",
        "Gulf-state sovereign-fund and government-directed AI/tech capital flows, by destination bloc",
        meta=[f"{len(df)} TRACKED DEALS", "MANUALLY CURATED"],
    )

    st.warning(
        "Investment flow data is manually curated and may not reflect all publicly disclosed deals. Deal "
        "values are indicative, not comprehensive. Several fields are explicitly marked RESEARCH_NEEDED "
        "where this project has not yet independently verified a figure -- those deals are excluded from "
        "dollar totals, not guessed."
    )

    bluf, key_judgment, why = _key_findings(df)
    key_findings_card(bluf, key_judgment, "Moderate", why)

    st.divider()
    st.subheader("Summary")
    totals = bloc_totals(df)
    us_total = totals.get("US", 0.0)
    china_total = totals.get("China", 0.0)
    combined = us_total + china_total
    ratio = capital_alignment_ratio(us_total, china_total)
    unconfirmed = unconfirmed_value_count(df)

    kpi_row([
        kpi_card("Total Tracked Investment", f"${combined:,.0f}M", "confirmed-value cross-border deals"),
        kpi_card("US-Bound Investment", f"${us_total:,.0f}M", f"{(us_total/combined*100):.0f}% of total" if combined else "N/A"),
        kpi_card("China-Bound Investment", f"${china_total:,.0f}M", f"{(china_total/combined*100):.0f}% of total" if combined else "N/A"),
        kpi_card("Capital Alignment Ratio", f"{ratio:.0f}%" if ratio is not None else "N/A", "US / (US + China)"),
    ])
    if unconfirmed:
        st.warning(f"{unconfirmed} of {len(df)} tracked deals have unconfirmed deal values and are excluded from dollar totals above.")

    st.divider()
    st.subheader("Capital Flow Sankey")
    st.plotly_chart(_sankey_figure(df), use_container_width=True)
    st.caption("Width proportional to confirmed deal value. Blue = US-bound, red = China-bound, light blue = US-aligned. Same-country sovereign-launch deals and unconfirmed-value deals are excluded.")

    col_q, col_s = st.columns(2)
    with col_q:
        st.subheader("Investment Over Time")
        st.plotly_chart(_quarterly_bar(df), use_container_width=True)
    with col_s:
        st.subheader("Investment by Sector")
        st.plotly_chart(_sector_pie(df), use_container_width=True)

    st.divider()
    _deal_table(df)

    st.divider()
    st.subheader("Capital Alignment Ratio by Country")
    summary = per_country_summary(df)
    st.plotly_chart(_capital_ratio_bar(summary), use_container_width=True)

    st.subheader("Capital Alignment vs. Net Alignment Score")
    st.plotly_chart(_positioning_scatter(summary), use_container_width=True)
    st.caption(
        "Discrepancies between alignment scores and capital flows may indicate hedging behavior or legacy "
        "relationships not yet reflected in policy positioning. Countries with no confirmed-value cross-border "
        "deal in either bloc are omitted from this chart."
    )

    st.divider()
    _admin_data_editor()

    footer()


if __name__ == "__main__":
    main()
