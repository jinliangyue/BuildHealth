"""
Engineering Parameters API · read-only prototype configuration
==============================================================

Exposes the prototype parameters that the frontend renders in its parameter
tables, so those tables stop relying on a hand-maintained frontend copy.

Strictly read-only and purely descriptive:
  * no engineering calculation happens here
  * no BHI / risk / priority formula is touched
  * the values are read from app/analytics/config.py, which remains the
    single source of truth

The frontend may keep a static fallback for offline rendering, but this
endpoint is the normal data source.
"""
from typing import Dict, List

from fastapi import APIRouter

from app.analytics.config import (
    ANOMALY_DETECTION_VERSION,
    BHI_CALCULATION_VERSION,
    BHI_RISK_BANDS,
    BHI_WEIGHTS,
    PRIORITY_LEVEL_THRESHOLDS,
    RECOMMENDATION_RULES_VERSION,
    RETROFIT_PRIORITY_VERSION,
    RETROFIT_PRIORITY_WEIGHTS,
    RISK_CLASSIFICATION_VERSION,
    THRESHOLD_RULES,
)
from app.core.config import AI_VERSION
from app.schemas.api import EngineeringParametersResponse

router = APIRouter(prefix="/engineering-parameters", tags=["parameters"])

PARAMETERS_NOTICE = (
    "Prototype Design Parameters. These are not national or industry "
    "standards and do not constitute a building safety grade, a structural "
    "appraisal, or a compliance assessment. Risk classification and retrofit "
    "priority are decision support only; qualified professional review is "
    "required. The frontend renders these values and never recomputes "
    "engineering results from them."
)


def _priority_bands() -> List[Dict]:
    """
    Turn PRIORITY_LEVEL_THRESHOLDS [(threshold, level)] into inclusive bands.

    The threshold list is descending in the config; sorting ascending lets each
    band's max be the next band's min minus one, with the top band ending at 100.
    """
    ordered = sorted(PRIORITY_LEVEL_THRESHOLDS, key=lambda t: t[0])
    bands: List[Dict] = []
    for i, (threshold, level) in enumerate(ordered):
        lo = int(threshold)
        hi = int(ordered[i + 1][0]) - 1 if i + 1 < len(ordered) else 100
        bands.append({"level": level, "min": lo, "max": hi})
    return bands


@router.get("", response_model=EngineeringParametersResponse)
def get_engineering_parameters() -> EngineeringParametersResponse:
    """
    Read-only prototype parameter set.

    Values are returned exactly as configured in app/analytics/config.py;
    the endpoint performs no calculation of its own.
    """
    return EngineeringParametersResponse(
        calculation_versions={
            "bhi": BHI_CALCULATION_VERSION,
            "risk_classification": RISK_CLASSIFICATION_VERSION,
            "anomaly_detection": ANOMALY_DETECTION_VERSION,
            "retrofit_priority": RETROFIT_PRIORITY_VERSION,
            "recommendation_rules": RECOMMENDATION_RULES_VERSION,
            "ai": AI_VERSION,
        },
        bhi_weights=dict(BHI_WEIGHTS),
        bhi_risk_bands=[dict(b) for b in BHI_RISK_BANDS],
        retrofit_priority_bands=_priority_bands(),
        retrofit_priority_weights=dict(RETROFIT_PRIORITY_WEIGHTS),
        detection_thresholds=[
            {
                "metric": rule.metric,
                "medium": rule.medium,
                "high": rule.high,
                "low": rule.low,
                "unit": rule.unit,
                "direction": rule.direction,
            }
            for rule in THRESHOLD_RULES.values()
        ],
        notice=PARAMETERS_NOTICE,
    )
