"""
Health Assessment Engine
BHI 0-100 = Structural×0.40 + Facility×0.20 + Environment×0.15 + Energy×0.10 + Fire×0.15
每个维度输入范围 [0,100]，超出范围抛 ValueError（不静默接受）。

维度评分来源（V1）：
- structural_safety: 基础分 100，按 HIGH/MEDIUM/LOW 异常扣分
- facility_condition: 基础分 100，按建筑年龄与设计年限比例扣分
- environmental_quality: 由 temperature/humidity 历史稳定性计算
- energy_performance: 由 electricity 变异系数计算
- fire_safety: 占位逻辑（楼层数 + 年龄微调）

输出：
  HealthAssessment dataclass，含 score / 5 维度 / calculation_version / explanation
"""
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any
import statistics

from app.analytics.config import BHI_WEIGHTS, BHI_CALCULATION_VERSION


class HealthInputError(ValueError):
    """健康评估输入非法（维度分数超出 0-100）"""


@dataclass
class HealthAssessment:
    building_id: int
    structural_safety: float
    facility_condition: float
    environmental_quality: float
    energy_performance: float
    fire_safety: float
    score: float
    calculation_version: str
    explanation: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _clamp(x: float) -> float:
    return max(0.0, min(100.0, round(x, 2)))


def _validate_dim(name: str, value: float) -> float:
    if not (0.0 <= value <= 100.0):
        raise HealthInputError(
            f"Dimension '{name}' must be in [0, 100], got {value}"
        )
    return float(value)


def compute_bhi(
    structural_safety: float,
    facility_condition: float,
    environmental_quality: float,
    energy_performance: float,
    fire_safety: float,
    building_id: Optional[int] = None,
) -> HealthAssessment:
    """
    计算 BHI。所有维度分数必须在 [0, 100]，否则抛 HealthInputError。
    返回 HealthAssessment（含 score, 5 维度, calculation_version, explanation）。
    """
    dims = {
        "structural_safety": _validate_dim("structural_safety", structural_safety),
        "facility_condition": _validate_dim("facility_condition", facility_condition),
        "environmental_quality": _validate_dim(
            "environmental_quality", environmental_quality
        ),
        "energy_performance": _validate_dim("energy_performance", energy_performance),
        "fire_safety": _validate_dim("fire_safety", fire_safety),
    }

    # 权重校验（防御性）
    total_weight = sum(BHI_WEIGHTS.values())
    if abs(total_weight - 1.0) > 1e-6:
        raise HealthInputError(
            f"BHI weights sum to {total_weight}, must equal 1.0"
        )

    score = sum(dims[k] * BHI_WEIGHTS[k] for k in BHI_WEIGHTS)
    score = round(score, 2)

    weakest = min(dims.items(), key=lambda x: x[1])
    strongest = max(dims.items(), key=lambda x: x[1])

    explanation = (
        f"Prototype assessment (calculation_version={BHI_CALCULATION_VERSION}) "
        f"yields BHI={score:.2f}. Strongest dimension: {strongest[0]}={strongest[1]:.2f}. "
        f"Weakest dimension: {weakest[0]}={weakest[1]:.2f}. "
        f"Prototype assessment suggests further professional inspection is recommended."
    )

    return HealthAssessment(
        building_id=building_id if building_id is not None else 0,
        structural_safety=dims["structural_safety"],
        facility_condition=dims["facility_condition"],
        environmental_quality=dims["environmental_quality"],
        energy_performance=dims["energy_performance"],
        fire_safety=dims["fire_safety"],
        score=score,
        calculation_version=BHI_CALCULATION_VERSION,
        explanation=explanation,
    )


# =================================================================
# 维度评分派生（用于在 building 数据 + monitoring 数据上直接计算）
# =================================================================
def score_structural_from_anomalies(
    n_high: int, n_medium: int, n_low: int, base: float = 100.0
) -> float:
    """
    结构安全评分：基础分 100，按异常严重度扣分。
    使用对数扣分（异常数量越多边际扣分越小），避免一次事件拖垮整栋。
    """
    import math
    score = (
        base
        - math.log1p(n_high) * 18.0
        - math.log1p(n_medium) * 6.0
        - math.log1p(n_low) * 2.0
    )
    return _clamp(score)


def score_facility_from_age(current_age: int, design_life: int) -> float:
    """
    设施评分：基于已用年限 / 设计年限的比例。
    设计年限内线性下降，超出后加速下降。
    """
    if design_life <= 0:
        return 50.0
    ratio = current_age / design_life
    if ratio <= 1.0:
        # 设计年限内：从 95 降到 75
        score = 95.0 - 20.0 * ratio
    else:
        # 超出设计年限：每超出 10% 扣 10 分，封底 30
        over = ratio - 1.0
        score = max(30.0, 75.0 - (over * 100.0))
    return _clamp(score)


def score_environment_from_series(
    temperature_series: List[float], humidity_series: List[float]
) -> float:
    """
    环境质量评分：温度稳定 + 湿度稳定。
    温度 stdev < 3 ℃ 满分 100；湿度 stdev < 5 % 满分 100。
    """
    temp_score = 100.0
    hum_score = 100.0

    if temperature_series and len(temperature_series) >= 5:
        try:
            t_std = statistics.stdev(temperature_series)
            temp_score = max(0.0, 100.0 - (t_std - 3.0) * 8.0)
        except statistics.StatisticsError:
            temp_score = 80.0
    else:
        temp_score = 80.0

    if humidity_series and len(humidity_series) >= 5:
        try:
            h_std = statistics.stdev(humidity_series)
            hum_score = max(0.0, 100.0 - (h_std - 5.0) * 5.0)
        except statistics.StatisticsError:
            hum_score = 80.0
    else:
        hum_score = 80.0

    return _clamp((temp_score + hum_score) / 2.0)


def score_energy_from_series(electricity_series: List[float]) -> float:
    """能耗表现评分：用电变异系数越低越好。CV<0.15 满分；CV>0.6 零分。"""
    if not electricity_series or len(electricity_series) < 5:
        return 80.0
    mean = statistics.fmean(electricity_series)
    if mean == 0:
        return 80.0
    try:
        stdev = statistics.stdev(electricity_series)
    except statistics.StatisticsError:
        return 80.0
    cv = stdev / abs(mean)
    if cv <= 0.15:
        return 100.0
    score = max(0.0, 100.0 - (cv - 0.15) * 220.0)
    return _clamp(score)


def score_fire_placeholder(floors: int, current_age: int) -> float:
    """消防评分占位：楼层越高、年龄越大，扣分越多。"""
    score = 90.0
    if floors >= 20:
        score -= 8.0
    elif floors >= 10:
        score -= 4.0
    if current_age > 30:
        score -= 5.0
    elif current_age > 15:
        score -= 2.0
    return _clamp(score)
