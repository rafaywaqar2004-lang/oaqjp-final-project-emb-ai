"""
Gulf AI & Tech-Bloc Alignment Tracker -- entry point / router.

Thin by design: this file's only job is grouped navigation via
st.navigation(). Every page's actual content lives in app_pages/. See
README.md for full methodology and country-set history.
"""

import streamlit as st

st.set_page_config(
    page_title="Gulf AI & Tech-Bloc Alignment Tracker",
    page_icon="assets/favicon.png",
    layout="wide",
)

pg = st.navigation(
    {
        "Overview": [
            st.Page("app_pages/regional_dashboard.py", title="Regional Dashboard", default=True),
        ],
        "Country Intelligence": [
            st.Page("app_pages/country_comparison.py", title="Country Comparison"),
            st.Page("app_pages/country_deep_dive.py", title="Country Deep Dive"),
        ],
        "Policy Monitor": [
            st.Page("app_pages/policy_events.py", title="Policy Events"),
        ],
        "Forecasting": [
            st.Page("app_pages/scenario_lab.py", title="Scenario Lab"),
        ],
        "Risk & Outlook": [
            st.Page("app_pages/strategic_risk.py", title="Strategic Risk"),
            st.Page("app_pages/outlook.py", title="12-Month Outlook"),
        ],
        "Sanctions & Risk": [
            st.Page("app_pages/sanctions_exposure.py", title="Sanctions Exposure"),
        ],
        "Research": [
            st.Page("app_pages/methodology.py", title="Methodology"),
            st.Page("app_pages/economic_analysis.py", title="Economic Analysis"),
            st.Page("app_pages/sources_data.py", title="Sources & Data"),
        ],
    }
)
pg.run()
