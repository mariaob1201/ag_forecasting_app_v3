"""Tests for features/data.py — payload flattening + class normalization."""

import numpy as np
import pandas as pd
import pytest

from features.data import flatten_features, normalize_class, prepare_disease_df


# ---------------------------------------------------------------------------
# normalize_class
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("raw, expected", [
    # Active-season prefixed forms (sort key + period / colon / hyphen / paren)
    ("1.Low",      "Low"),
    ("2.Moderate", "Moderate"),
    ("3.High",     "High"),
    ("1. High",    "High"),
    (" 3:High",    "High"),
    ("2)Moderate", "Moderate"),
    ("3-High",     "High"),
    # Plain forms with mixed casing
    ("INACTIVE", "Inactive"),
    ("low",      "Low"),
    ("HiGh",     "High"),
    # Empty / missing → Unknown
    ("",     "Unknown"),
    ("   ",  "Unknown"),
    (None,   "Unknown"),
])
def test_normalize_class_handles_common_api_shapes(raw, expected):
    assert normalize_class(raw) == expected


def test_normalize_class_handles_nan():
    assert normalize_class(np.nan) == "Unknown"


# ---------------------------------------------------------------------------
# flatten_features
# ---------------------------------------------------------------------------

def _make_feature(station_id, name, lat, lon, rows):
    return {
        "station": {
            "station_id": station_id,
            "station_name": name,
            "city": name + " City",
            "county": "Dane",
            "region": "South Central",
            "state": "WI",
            "coordinates": {"latitude": lat, "longitude": lon},
        },
        "timeseries": [
            {"date": ts_date, "data": [
                {"fieldname": k, "value": v} for k, v in fields.items()
            ]}
            for ts_date, fields in rows
        ],
    }


def test_flatten_features_empty_payload():
    assert flatten_features({}).empty
    assert flatten_features({"features": []}).empty


def test_flatten_features_one_row_per_station_per_date():
    payload = {"features": [
        _make_feature("ALTN", "Arlington", 43.3, -89.4, [
            ("2026-07-15", {"tarspot_risk": 0.42, "tarspot_risk_class": "High"}),
            ("2026-07-16", {"tarspot_risk": 0.10, "tarspot_risk_class": "Low"}),
        ]),
        _make_feature("MAPL", "Maple",     45.2, -91.5, [
            ("2026-07-15", {"tarspot_risk": -1,  "tarspot_risk_class": "Inactive"}),
        ]),
    ]}
    df = flatten_features(payload)
    assert len(df) == 3
    assert set(df["station_id"]) == {"ALTN", "MAPL"}
    altn_2 = df[(df["station_id"] == "ALTN") & (df["date"] == "2026-07-16")].iloc[0]
    assert altn_2["tarspot_risk"] == 0.10
    assert altn_2["tarspot_risk_class"] == "Low"


def test_flatten_features_drops_missing_coords():
    payload = {"features": [
        _make_feature("ALTN", "Arlington", 43.3, -89.4,
                      [("2026-07-15", {"tarspot_risk": 0.5})]),
        _make_feature("BAD",  "Bad",       None, None,
                      [("2026-07-15", {"tarspot_risk": 0.5})]),
    ]}
    df = flatten_features(payload)
    assert list(df["station_id"]) == ["ALTN"]


def test_flatten_features_coerces_coords_to_float():
    payload = {"features": [
        _make_feature("ALTN", "Arlington", "43.3", "-89.4",
                      [("2026-07-15", {"tarspot_risk": 0.5})]),
    ]}
    df = flatten_features(payload)
    assert df["latitude"].dtype.kind == "f"
    assert df["latitude"].iloc[0] == pytest.approx(43.3)


# ---------------------------------------------------------------------------
# prepare_disease_df
# ---------------------------------------------------------------------------

def test_prepare_disease_df_attaches_three_columns():
    df = pd.DataFrame({
        "station_id":          ["ALTN", "MAPL"],
        "tarspot_risk":        [0.42, -1],
        "tarspot_risk_class":  ["2.Moderate", "Inactive"],
    })
    out = prepare_disease_df(df, "tarspot_risk", "tarspot_risk_class")
    assert {"risk_class", "risk_value", "risk_display"}.issubset(out.columns)
    # The "2.Moderate" form is normalized to plain "Moderate"
    assert out.loc[out["station_id"] == "ALTN", "risk_class"].iloc[0] == "Moderate"
    assert out.loc[out["station_id"] == "MAPL", "risk_class"].iloc[0] == "Inactive"
    # -1 → "n/a" for the display, but risk_value stays numeric (-1)
    assert out.loc[out["station_id"] == "MAPL", "risk_display"].iloc[0] == "n/a"
    assert out.loc[out["station_id"] == "ALTN", "risk_display"].iloc[0] == "0.42"


def test_prepare_disease_df_tolerates_missing_columns():
    df = pd.DataFrame({"station_id": ["ALTN"]})
    out = prepare_disease_df(df, "no_such_risk", "no_such_class")
    assert out.loc[0, "risk_class"] == "Unknown"
    assert pd.isna(out.loc[0, "risk_value"])
    assert out.loc[0, "risk_display"] == "n/a"
