"""
Shared constants for the Gulf AI & Tech-Bloc Alignment Tracker.
"""

# Country set: 6 Gulf states + 2 non-Gulf comparators (Pakistan, Turkey),
# both navigating similar US/China balancing acts on a smaller scale.
COUNTRIES = {
    "Saudi Arabia": "SAU",
    "United Arab Emirates": "ARE",
    "Qatar": "QAT",
    "Bahrain": "BHR",
    "Kuwait": "KWT",
    "Oman": "OMN",
    "Pakistan": "PAK",
    "Turkey": "TUR",
}

GULF_COUNTRIES = {"Saudi Arabia", "United Arab Emirates", "Qatar", "Bahrain", "Kuwait", "Oman"}
COMPARATOR_COUNTRIES = {"Pakistan", "Turkey"}

ISO3_TO_COUNTRY = {v: k for k, v in COUNTRIES.items()}

# World Bank indicator codes used by the automated refresh pipeline.
WB_INDICATORS = {
    "oil_rents_pct_gdp": "NY.GDP.PETR.RT.ZS",   # Oil rents (% of GDP) -- used as an inverse proxy for non-oil diversification
    "fdi_net_inflows_pct_gdp": "BX.KLT.DINV.WD.GD.ZS",  # FDI, net inflows (% of GDP)
    "gdp_current_usd": "NY.GDP.MKTP.CD",         # GDP, current US$ (context only)
}

DATA_DIR = "data"
CURATED_DIR = f"{DATA_DIR}/curated"
WORLDBANK_DIR = f"{DATA_DIR}/worldbank"
COMPUTED_DIR = f"{DATA_DIR}/computed"
