"""Tests for the pure (non-Streamlit) helpers extracted from the Streamlit app.

Streamlit's testing harness (``streamlit.testing.v1.AppTest``) is great for
behavior tests, but most of the logic worth verifying here is already
factored out into plain functions — we test those directly.
"""

import pandas as pd
import pytest

from streamlit_app.sidebar import (
    WHITE_MOLD_LABEL,
    WHITE_MOLD_VARIANTS,
    build_visible_options,
    resolve_disease_label,
)
from streamlit_app.tabs.forecast import count_risk_buckets
from streamlit_app.tabs.biomass import _default_plant_date
from datetime import date


# ---------------------------------------------------------------------------
# sidebar.build_visible_options — collapse the three WM rows into one label
# ---------------------------------------------------------------------------

def test_build_visible_options_collapses_white_mold():
    opts = {
        "Tar Spot (corn)":                          {"type": "disease"},
        "White Mold — Non-irrigated (soybean)":     {"type": "disease"},
        "White Mold — Irrigated 30in (soybean)":    {"type": "disease"},
        "White Mold — Irrigated 15in (soybean)":    {"type": "disease"},
        "Cereal Rye Biomass":                       {"type": "biomass"},
    }
    visible = build_visible_options(opts)
    assert visible == [
        "Tar Spot (corn)",
        WHITE_MOLD_LABEL,
        "Cereal Rye Biomass",
    ]


def test_build_visible_options_with_no_white_mold():
    opts = {
        "Tar Spot (corn)":   {"type": "disease"},
        "Cereal Rye Biomass": {"type": "biomass"},
    }
    visible = build_visible_options(opts)
    assert WHITE_MOLD_LABEL not in visible
    assert visible == ["Tar Spot (corn)", "Cereal Rye Biomass"]


# ---------------------------------------------------------------------------
# sidebar.resolve_disease_label — map (dropdown, sub-radio) → real label
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("display, irrigation, expected", [
    ("Tar Spot (corn)", None,                          "Tar Spot (corn)"),
    ("Tar Spot (corn)", "Non-irrigated",               "Tar Spot (corn)"),
    (WHITE_MOLD_LABEL,  "Non-irrigated",               WHITE_MOLD_VARIANTS["Non-irrigated"]),
    (WHITE_MOLD_LABEL,  "Irrigated 30in",              WHITE_MOLD_VARIANTS["Irrigated 30in"]),
    (WHITE_MOLD_LABEL,  "Irrigated 15in",              WHITE_MOLD_VARIANTS["Irrigated 15in"]),
    # Defensive: missing / unknown sub-radio falls back to the first variant.
    (WHITE_MOLD_LABEL,  None,                          WHITE_MOLD_VARIANTS["Non-irrigated"]),
    (WHITE_MOLD_LABEL,  "Bogus",                       WHITE_MOLD_VARIANTS["Non-irrigated"]),
])
def test_resolve_disease_label(display, irrigation, expected):
    assert resolve_disease_label(display, irrigation) == expected


# ---------------------------------------------------------------------------
# forecast.count_risk_buckets — counts under the tricky API formats.
# ---------------------------------------------------------------------------

def test_count_risk_buckets_handles_active_season_prefixes():
    s = pd.Series(["1.Low", "1.Low", "2.Moderate", "3.High", "Inactive"])
    counts = count_risk_buckets(s)
    assert counts == {"total": 5, "active": 4, "high": 1, "moderate": 1, "low": 2}


def test_count_risk_buckets_handles_synonyms_and_casing():
    s = pd.Series(["high", "MEDIUM", "Low", "None", "n/a", "unknown"])
    counts = count_risk_buckets(s)
    assert counts["total"] == 6
    # "MEDIUM" is treated as Moderate; the three inactive synonyms drop out.
    assert counts["high"] == 1
    assert counts["moderate"] == 1
    assert counts["low"] == 1
    assert counts["active"] == 3   # high + medium + low


def test_count_risk_buckets_all_inactive():
    s = pd.Series(["Inactive"] * 78)
    counts = count_risk_buckets(s)
    assert counts == {"total": 78, "active": 0, "high": 0, "moderate": 0, "low": 0}


# ---------------------------------------------------------------------------
# biomass._default_plant_date — picks current-year Sep 15, else previous year.
# ---------------------------------------------------------------------------

def test_default_plant_date_uses_current_year_when_after_planting():
    # Forecasting in November → Sep 15 of the same year is in the past.
    assert _default_plant_date(date(2026, 11, 1)) == date(2026, 9, 15)


def test_default_plant_date_falls_back_to_prior_year():
    # Forecasting in May → Sep 15 of the same year is in the future,
    # so the helper should reach back to the prior fall.
    assert _default_plant_date(date(2026, 5, 1)) == date(2025, 9, 15)
