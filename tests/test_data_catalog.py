import pandas as pd
import pytest

from data_catalog import build_catalog


@pytest.fixture(scope="module")
def catalog():
    return build_catalog()


def test_catalog_has_expected_columns(catalog):
    expected = {
        "Dataset", "Source type", "Countries covered", "Observations",
        "Update cadence", "Missingness", "Methodology", "Limitations", "_path",
    }
    assert expected.issubset(set(catalog.columns))


def test_every_registered_file_actually_exists(catalog):
    """A dataset entry pointing at a file that no longer exists is a real
    bug (a rename/move this catalog wasn't updated for) -- fail loudly."""
    for _, row in catalog.iterrows():
        from pathlib import Path
        assert Path(row["_path"]).exists(), f"{row['Dataset']} points at a missing file: {row['_path']}"


def test_observations_are_never_negative(catalog):
    assert (catalog["Observations"] >= 0).all()


def test_country_coverage_never_exceeds_seventeen(catalog):
    """A long-format deal file can carry a non-tracked pseudo-country row
    (e.g. 'GCC region-wide', context only, never scored) -- coverage counts
    must exclude those, never report more than the 17 tracked countries."""
    for _, row in catalog.iterrows():
        coverage = row["Countries covered"]
        if coverage.endswith("/ 17 countries"):
            n = int(coverage.split("/")[0].strip())
            assert 0 <= n <= 17, f"{row['Dataset']}: {coverage}"


def test_every_dataset_has_methodology_and_limitations_text(catalog):
    for _, row in catalog.iterrows():
        assert len(row["Methodology"]) > 10
        assert len(row["Limitations"]) > 10


def test_composite_scores_dataset_present(catalog):
    assert "Composite Scores" in set(catalog["Dataset"])


def test_worldbank_dataset_documents_the_sandbox_limitation(catalog):
    row = catalog[catalog["Dataset"].str.startswith("World Bank")].iloc[0]
    assert "sandbox" in row["Limitations"].lower() or "blocks" in row["Limitations"].lower()
