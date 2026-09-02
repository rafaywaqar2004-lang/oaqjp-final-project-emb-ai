"""
Watch Next -- leading indicators, not forecasts. Loads
data/curated/watch_indicators.csv (each row already traceable to a real,
cited row elsewhere in data/curated/*.csv -- see that column) and filters
it for the Overview (regional-scope items) or a specific Country Deep Dive
(that country's items plus regional ones).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from constants import CURATED_DIR

WATCH_INDICATORS_PATH = Path(CURATED_DIR) / "watch_indicators.csv"


def load_watch_indicators(path: str | Path = WATCH_INDICATORS_PATH) -> pd.DataFrame:
    return pd.read_csv(path)


def watch_items_for(indicators: pd.DataFrame, country: str | None = None) -> pd.DataFrame:
    """country=None returns only Regional-scope items (for the Overview).
    A specific country returns that country's own items plus Regional ones,
    country items first."""
    regional = indicators[indicators["scope"] == "Regional"]
    if country is None:
        return regional
    country_specific = indicators[indicators["scope"] == country]
    return pd.concat([country_specific, regional], ignore_index=True)
