"""
Retrieval Query Builder · Phase 6B
====================================

Builds an enhanced retrieval query from a user question + the current
EngineeringContext. The goal is to surface relevant knowledge chunks
without modifying the user's question semantics.

Examples:
    User: "Why is this building at high risk?"
    Enhanced: "Why is this building at high risk? crack_width tilt
              temperature humidity electricity risk HighRisk
              structural comprehensive_assessment"
"""
from typing import List

from app.ai.schemas import EngineeringContext


def build_retrieval_query(
    user_question: str,
    context: EngineeringContext,
) -> str:
    """
    增强 query, 加入 context 关键词, 提升 retrieval 精度.
    """
    parts: List[str] = [user_question]

    # 加入 sensor metric names (e.g. "crack_width" -> "crack width")
    for s in context.sensors:
        metric_readable = s.sensor_type.replace("_", " ")
        if metric_readable and metric_readable not in parts:
            parts.append(metric_readable)

    # 加入 risk 相关
    if context.risk.risk_level and context.risk.risk_level != "Normal":
        parts.append(f"risk {context.risk.risk_level}")

    # 加入 retrofit categories / issue types
    for rec in context.retrofit.recommendations[:3]:
        cat = (rec.get("category") or "").lower().strip()
        if cat:
            parts.append(cat)
        issue = (rec.get("issue_type") or "").replace("_", " ").strip()
        if issue:
            parts.append(issue)

    # 加入 weakness hint
    if context.health.weakest_dimension:
        parts.append(context.health.weakest_dimension.replace("_", " "))

    return " ".join(filter(None, parts))
