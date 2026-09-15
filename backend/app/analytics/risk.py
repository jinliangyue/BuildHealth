"""
Risk Classification Engine
规则（边界明确）：
  100 → Normal
  90  → Normal
  89  → Attention
  75  → Attention
  74  → Abnormal
  60  → Abnormal
  59  → High Risk
  0   → High Risk

返回：
  risk_level, explanation（明确 Prototype Risk Classification）
  当存在 HIGH 异常时，即使 BHI 处于 Normal 也会覆盖为 Attention（最小升级规则）。
"""
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional


@dataclass
class RiskClassification:
    building_id: int
    bhi: float
    risk_level: str  # Normal / Attention / Abnormal / HighRisk
    explanation: str
    n_high_anomalies: int = 0
    n_medium_anomalies: int = 0
    n_low_anomalies: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def classify_risk(
    bhi: float,
    building_id: Optional[int] = None,
    n_high: int = 0,
    n_medium: int = 0,
    n_low: int = 0,
) -> RiskClassification:
    """
    根据 BHI 给出风险等级。
    边界规则（BHI 整数测试值）：
      100/90 → Normal, 89/75 → Attention, 74/60 → Abnormal, 59/0 → High Risk
    """
    if bhi > 100 or bhi < 0:
        raise ValueError(f"BHI must be in [0, 100], got {bhi}")

    # 主判定
    if bhi >= 90:
        level = "Normal"
    elif bhi >= 75:
        level = "Attention"
    elif bhi >= 60:
        level = "Abnormal"
    else:
        level = "HighRisk"

    # 最小升级规则：HIGH 异常存在时不允许停留在 Normal
    if level == "Normal" and n_high > 0:
        level = "Attention"

    # 顶层原因
    if n_high > 0:
        reason = (
            f"detected {n_high} HIGH-severity prototype anomalies; "
            f"monitoring trend indicates elevated risk"
        )
    elif bhi < 60:
        reason = f"BHI={bhi:.2f} is significantly below prototype normal range"
    elif bhi < 75:
        reason = f"BHI={bhi:.2f} suggests multiple prototype indicators below normal"
    elif bhi < 90 and (n_medium + n_low) > 0:
        reason = (
            f"BHI={bhi:.2f} with {n_medium} medium and {n_low} low prototype anomalies"
        )
    else:
        reason = f"BHI={bhi:.2f} within prototype normal range"

    explanation = (
        f"Prototype Risk Classification → {level}. "
        f"Based on BHI={bhi:.2f}, {reason}. "
        f"Prototype assessment suggests further professional inspection is recommended."
    )

    return RiskClassification(
        building_id=building_id if building_id is not None else 0,
        bhi=round(bhi, 2),
        risk_level=level,
        explanation=explanation,
        n_high_anomalies=n_high,
        n_medium_anomalies=n_medium,
        n_low_anomalies=n_low,
    )
