"""
Frontend / Backend Engineering Parameter Consistency
=====================================================

The frontend keeps a small display mirror of prototype engineering parameters
(`frontend/src/types/api.ts`) so that parameter tables and KPI colour
thresholds can render without an extra round trip.

The backend analytics engine is the single source of truth. This test reads the
frontend constants and asserts they still agree with the engine, so a threshold
change on either side cannot silently drift.

The backend side is probed through behaviour (classify_risk / map_priority_level)
rather than by re-reading literals, so the test stays meaningful if the
analytics code is refactored internally.

These are Prototype Design Parameters, not national or industry standards.
"""
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pytest

from app.analytics import risk as risk_mod
from app.analytics.config import BHI_WEIGHTS, THRESHOLD_RULES
from app.analytics.priority import map_priority_level

FRONTEND_TYPES = (
    Path(__file__).resolve().parents[2] / "frontend" / "src" / "types" / "api.ts"
)

RISK_LEVELS = ["Normal", "Attention", "Abnormal", "HighRisk"]


@pytest.fixture(scope="module")
def fe_source() -> str:
    assert FRONTEND_TYPES.exists(), f"frontend types not found at {FRONTEND_TYPES}"
    return FRONTEND_TYPES.read_text(encoding="utf-8")


def _parse_risk_bands(src: str) -> Dict[str, Tuple[int, int]]:
    """Parse BHI_RISK_BANDS into {level: (min, max)}."""
    block = re.search(
        r"export const BHI_RISK_BANDS[^=]*=\s*\{(.*?)\n\};", src, re.S
    )
    assert block, "BHI_RISK_BANDS not found in frontend types"
    pairs = re.findall(
        r"(\w+):\s*\{\s*min:\s*(\d+),\s*max:\s*(\d+)\s*\}", block.group(1)
    )
    assert len(pairs) == 4, f"expected 4 risk bands, parsed {len(pairs)}"
    return {name: (int(lo), int(hi)) for name, lo, hi in pairs}


def _parse_bhi_weights(src: str) -> Dict[str, float]:
    """Parse the BHI_WEIGHTS literal into {dimension: weight}."""
    block = re.search(r"export const BHI_WEIGHTS[^=]*=\s*\{(.*?)\n\};", src, re.S)
    assert block, "BHI_WEIGHTS not found in frontend types"
    pairs = re.findall(r"(\w+):\s*([\d.]+),", block.group(1))
    assert len(pairs) == 5, f"expected 5 dimensions, parsed {len(pairs)}"
    return {name: float(w) for name, w in pairs}


def _parse_detection_thresholds(
    src: str,
) -> Dict[str, Tuple[Optional[float], Optional[float], str]]:
    """Parse DETECTION_THRESHOLDS into {metric: (medium, high, unit)}."""
    block = re.search(
        r"export const DETECTION_THRESHOLDS[^=]*=\s*\[(.*?)\n\];", src, re.S
    )
    assert block, "DETECTION_THRESHOLDS not found in frontend types"
    rows = re.findall(
        r"\{\s*metric:\s*\"(\w+)\",\s*medium:\s*(null|[\d.]+),\s*"
        r"high:\s*(null|[\d.]+),\s*unit:\s*\"([^\"]*)\"",
        block.group(1),
    )
    assert rows, "no detection threshold rows parsed"
    out: Dict[str, Tuple[Optional[float], Optional[float], str]] = {}
    for metric, medium, high, unit in rows:
        out[metric] = (
            None if medium == "null" else float(medium),
            None if high == "null" else float(high),
            unit,
        )
    return out


# ============ BHI weights ============
def test_frontend_bhi_weights_match_backend(fe_source):
    assert _parse_bhi_weights(fe_source) == BHI_WEIGHTS


# ============ BHI risk bands ============
def test_frontend_risk_bands_match_engine(fe_source):
    """
    Every band endpoint must classify to its own level in the engine.
    Probing behaviour keeps this honest even if risk.py is refactored.
    """
    for level, (lo, hi) in _parse_risk_bands(fe_source).items():
        for probe in (lo, hi):
            classified = risk_mod.classify_risk(
                float(probe), n_high=0, n_medium=0, n_low=0
            ).risk_level
            assert classified == level, (
                f"BHI {probe} classifies as {classified} but the frontend "
                f"band {level} claims {lo}-{hi}"
            )


def test_frontend_risk_bands_tile_the_scale(fe_source):
    bands = sorted(_parse_risk_bands(fe_source).values())
    assert bands[0][0] == 0
    assert bands[-1][1] == 100
    for (_, prev_hi), (next_lo, _) in zip(bands, bands[1:]):
        assert next_lo == prev_hi + 1, "risk bands must not gap or overlap"


# ============ Anomaly detection thresholds ============
def test_frontend_detection_thresholds_match_backend(fe_source):
    parsed = _parse_detection_thresholds(fe_source)
    for metric, (medium, high, unit) in parsed.items():
        rule = THRESHOLD_RULES.get(metric)
        assert rule is not None, f"{metric} missing from backend THRESHOLD_RULES"
        assert medium == rule.medium, f"{metric} medium drifted"
        assert high == rule.high, f"{metric} high drifted"
        assert unit == rule.unit, f"{metric} unit drifted"


# ============ Retrofit priority boundary ============
def test_frontend_high_priority_boundary_matches_engine(fe_source):
    """
    The frontend hint says "priority >= RETROFIT_PRIORITY_HIGH_MIN"; the backend
    counts high_priority_count with the same boundary. Both must agree with the
    engine's own High tier.
    """
    m = re.search(r"export const RETROFIT_PRIORITY_HIGH_MIN\s*=\s*(\d+)", fe_source)
    assert m, "RETROFIT_PRIORITY_HIGH_MIN not found in frontend types"
    fe_boundary = int(m.group(1))

    assert map_priority_level(float(fe_boundary)) == "High"
    # one below the boundary must not be High
    assert map_priority_level(float(fe_boundary) - 1) != "High"
