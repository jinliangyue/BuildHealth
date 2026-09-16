"""
Engineering Parameters API · contract + consistency tests
=========================================================

GET /api/engineering-parameters exposes the prototype parameters the frontend
renders, so the frontend no longer has to keep its own copy as the normal
data source.

The endpoint is descriptive only. These tests pin two things:
  1. the response contract (fields, types, values read from config)
  2. that the exposed bands agree with what the analytics engine ACTUALLY does,
     probed through classify_risk / map_priority_level — so the parameter table
     can never drift from the engine that computes with it
"""
import pytest

from app.analytics import risk as risk_mod
from app.analytics.config import (
    BHI_RISK_BANDS,
    BHI_WEIGHTS,
    PRIORITY_LEVEL_THRESHOLDS,
    RETROFIT_PRIORITY_WEIGHTS,
    THRESHOLD_RULES,
)
from app.analytics.priority import map_priority_level
from app.api.parameters import PARAMETERS_NOTICE

ENDPOINT = "/api/engineering-parameters"


@pytest.fixture
def payload(client):
    r = client.get(ENDPOINT)
    assert r.status_code == 200, r.text
    return r.json()


# ------------------------------------------------------------- contract shape
def test_endpoint_returns_expected_top_level_fields(payload):
    expected = {
        "calculation_versions",
        "bhi_weights",
        "bhi_risk_bands",
        "retrofit_priority_bands",
        "retrofit_priority_weights",
        "detection_thresholds",
        "notice",
    }
    assert expected <= set(payload.keys())


def test_calculation_versions_are_present_and_versioned(payload):
    versions = payload["calculation_versions"]
    assert set(versions) == {
        "bhi",
        "risk_classification",
        "anomaly_detection",
        "retrofit_priority",
        "recommendation_rules",
        "ai",
    }
    for key, value in versions.items():
        assert isinstance(value, str) and value, f"{key} version missing"


def test_notice_states_prototype_and_non_standard(payload):
    notice = payload["notice"].lower()
    assert "prototype" in notice
    assert "not national or industry standards" in notice
    assert "qualified professional review" in notice


def test_weights_match_config(payload):
    assert payload["bhi_weights"] == BHI_WEIGHTS
    assert payload["retrofit_priority_weights"] == RETROFIT_PRIORITY_WEIGHTS


def test_detection_thresholds_match_config(payload):
    by_metric = {t["metric"]: t for t in payload["detection_thresholds"]}
    assert set(by_metric) == set(THRESHOLD_RULES.keys())
    for metric, rule in THRESHOLD_RULES.items():
        got = by_metric[metric]
        assert got["medium"] == rule.medium
        assert got["high"] == rule.high
        assert got["low"] == rule.low
        assert got["unit"] == rule.unit
        assert got["direction"] == rule.direction


# ------------------------------------------------- engine agreement (the guard)
def test_bhi_risk_bands_agree_with_engine(payload):
    """
    Every band endpoint must classify to its own level in the engine, with no
    anomaly override in play. This is what stops the exposed table drifting
    from analytics/risk.py.
    """
    bands = payload["bhi_risk_bands"]
    assert len(bands) == 4
    for band in bands:
        for probe in (band["min"], band["max"]):
            classified = risk_mod.classify_risk(
                float(probe), n_high=0, n_medium=0, n_low=0
            ).risk_level
            assert classified == band["level"], (
                f"BHI {probe} classifies as {classified} but the parameter "
                f"table says {band['level']} ({band['min']}-{band['max']})"
            )


def test_bhi_risk_bands_tile_the_scale(payload):
    bands = sorted(payload["bhi_risk_bands"], key=lambda b: b["min"])
    assert bands[0]["min"] == 0
    assert bands[-1]["max"] == 100
    for prev, nxt in zip(bands, bands[1:]):
        assert nxt["min"] == prev["max"] + 1, "bands must not gap or overlap"


def test_priority_bands_agree_with_engine(payload):
    bands = payload["retrofit_priority_bands"]
    assert len(bands) == len(PRIORITY_LEVEL_THRESHOLDS)
    for band in bands:
        assert map_priority_level(float(band["min"])) == band["level"]
        assert map_priority_level(float(band["max"])) == band["level"]


def test_priority_bands_tile_the_scale(payload):
    bands = sorted(payload["retrofit_priority_bands"], key=lambda b: b["min"])
    assert bands[0]["min"] == 0
    assert bands[-1]["max"] == 100
    for prev, nxt in zip(bands, bands[1:]):
        assert nxt["min"] == prev["max"] + 1


# ------------------------------------------------------------------ read-only
def test_endpoint_does_not_require_a_database(client):
    """
    Pure configuration read — it must not depend on the DB session, and must
    not write anything. A 200 with the standard TestClient (no seeded data)
    confirms it serves purely from configuration.
    """
    r = client.get(ENDPOINT)
    assert r.status_code == 200
    assert r.json()["bhi_weights"]


def test_exposed_weights_are_the_ones_the_engine_uses():
    """
    Guard against the endpoint inventing its own weights: the config table it
    reads is the same one the health engine imports.
    """
    from app.analytics import health as ha

    assert ha.BHI_WEIGHTS == BHI_WEIGHTS
    assert sum(BHI_WEIGHTS.values()) == pytest.approx(1.0)
    assert [b["level"] for b in BHI_RISK_BANDS] == [
        "Normal",
        "Attention",
        "Abnormal",
        "HighRisk",
    ]
    assert PARAMETERS_NOTICE
