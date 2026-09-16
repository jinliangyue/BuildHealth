"""
Mock AI Provider · Phase 5 V3
=============================

确定性 / 无 LLM 调用 / 基于 context 直接生成结构化响应.

5 个问题模式 (关键词匹配):
  1. 总结/健康/summary     → 综述 (BHI + Risk + Priority)
  2. 风险/risk             → 重点解释 risk
  3. 改造/retrofit/优先级  → 重点解释 retrofit
  4. 异常/anomaly/裂缝     → 重点解释 anomaly
  5. default              → 综述

Mock 输出约束:
- answer 字符串中禁止出现 ER 红线禁词 (test_ai_redlines 强制)
- 所有数字必须从 context 读, 不允许硬编或计算
- evidence 每项必有 source_type + description
- disclaimer 必含
"""
from datetime import datetime
from typing import List, Optional

from app.ai.schemas import (
    AIEvidenceRef,
    AIHealthStatus,
    AIKeyFinding,
    AIRecommendedAction,
    AIResponse,
    EngineeringContext,
)
from app.ai.redlines import scan_response_for_redlines
from app.ai.schemas import AIProviderError
from app.core.config import AI_DISCLAIMER, AI_VERSION, AI_MODEL


class MockProvider:
    name = "mock"

    # ------------------------------------------------------------------
    # Safety gate (mirrors OpenAICompatibleProvider)
    # ------------------------------------------------------------------
    def _guard_safety(self, response: AIResponse) -> AIResponse:
        """
        Runtime redline gate, identical in effect to the real provider's.

        The mock composes text from templates, but it interpolates database
        values (building name, metric labels, risk level, explanations). If any
        of those ever carried a forbidden phrase, the response must not be
        served — the same rule the real provider enforces. Without this, mock
        and real providers would not behave consistently.
        """
        forbidden = scan_response_for_redlines(
            answer=response.answer,
            key_findings_text=" ".join(
                f"{kf.title} {kf.description}" for kf in response.key_findings
            ),
            recommended_actions_text=" ".join(
                f"{a.action} {a.reason}" for a in response.recommended_actions
            ),
            evidence_descriptions=" ".join(
                e.description for e in response.evidence
            ),
        )
        if forbidden:
            raise AIProviderError(
                "safety_violation",
                f"mock response contained forbidden phrase(s): {forbidden[:3]}",
            )
        return response
    model = AI_MODEL  # "mock-deterministic-v1"

    def health_check(self) -> AIHealthStatus:
        return AIHealthStatus(
            status="ok",
            provider=self.name,
            model=self.model,
            message=(
                "Mock AI Provider in demonstration mode. "
                "No real LLM is invoked. All responses are derived "
                "deterministically from the Engineering Context."
            ),
        )

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    def generate_summary(
        self,
        context: EngineeringContext,
        knowledge_evidence: Optional[List[dict]] = None,
    ) -> AIResponse:
        h = context.health
        r = context.risk
        rf = context.retrofit
        b = context.building

        bhi_str = f"{h.bhi:.2f}" if h.bhi is not None else "N/A"
        risk_str = r.risk_level or "N/A"
        priority_str = f"{rf.overall_priority:.2f}" if rf.overall_priority else "0.00"
        level_str = rf.overall_priority_level or "Low"

        # Answer 模板 (从 context 直接读, 不编造)
        answer_parts: List[str] = []
        answer_parts.append(
            f"Building '{b.name}' (id={b.building_id}) is a {b.building_type} "
            f"with {b.floors} floors, structure type '{b.structure_type}', "
            f"currently {b.current_age} years old "
            f"(design life {b.design_life})."
        )
        if h.bhi is not None:
            answer_parts.append(
                f"Prototype Building Health Index (BHI) is {bhi_str} "
                f"(calculation_version={h.calculation_version}); "
                f"weakest dimension: {h.weakest_dimension or 'N/A'}."
            )
        if r.risk_level:
            answer_parts.append(
                f"Prototype Risk Classification: {risk_str} "
                f"(high={r.n_high}, medium={r.n_medium}, low={r.n_low} anomalies). "
                f"This is a prototype parameter, not a legal safety grade."
            )
        if rf.recommendation_count > 0:
            answer_parts.append(
                f"Retrofit decision support identifies {rf.recommendation_count} "
                f"prototype recommendation(s); top priority score {priority_str} "
                f"({level_str}). All recommendations require qualified "
                f"professional review."
            )
        else:
            answer_parts.append(
                "No active retrofit recommendations from the prototype rule "
                "engine; continue routine monitoring per prototype thresholds."
            )
        answer_parts.append(
            f"All engineering metrics above are derived from V1 (BHI / "
            f"anomaly detection) and V2 (retrofit rule engine) deterministic "
            f"services. This AI summary is an explanation layer only."
        )
        answer = " ".join(answer_parts)

        # Key findings: 来自 BHI / Risk / Retrofit
        key_findings: List[AIKeyFinding] = []
        if h.bhi is not None:
            if h.bhi < 60:
                sev = "high"
            elif h.bhi < 75:
                sev = "medium"
            elif h.bhi < 90:
                sev = "low"
            else:
                sev = "info"
            key_findings.append(
                AIKeyFinding(
                    title="Building Health Index (BHI)",
                    description=(
                        f"Prototype BHI = {bhi_str}. "
                        f"Weakest dimension: {h.weakest_dimension or 'N/A'}."
                    ),
                    severity=sev,
                )
            )
        if r.risk_level:
            sev = "high" if r.risk_level == "HighRisk" else (
                "medium" if r.risk_level == "Abnormal" else (
                    "low" if r.risk_level == "Attention" else "info"
                )
            )
            key_findings.append(
                AIKeyFinding(
                    title=f"Prototype Risk: {r.risk_level}",
                    description=(
                        f"{r.n_high} HIGH, {r.n_medium} MEDIUM, "
                        f"{r.n_low} LOW prototype anomalies."
                    ),
                    severity=sev,
                )
            )
        if rf.recommendation_count > 0:
            top = rf.recommendations[0] if rf.recommendations else None
            if top:
                sev = "high" if top.get("urgency") in ("high", "critical") else (
                    "medium" if top.get("urgency") == "medium" else "low"
                )
                key_findings.append(
                    AIKeyFinding(
                        title=f"Top retrofit: {top.get('title', 'N/A')}",
                        description=(
                            f"Category={top.get('category')}, "
                            f"priority={top.get('priority_score'):.2f}, "
                            f"urgency={top.get('urgency')}."
                        ),
                        severity=sev,
                    )
                )
        if context.monitoring_summary.anomaly_total > 0:
            key_findings.append(
                AIKeyFinding(
                    title="Active prototype anomalies",
                    description=(
                        f"{context.monitoring_summary.anomaly_total} "
                        f"prototype anomalies across "
                        f"{len(context.monitoring_summary.by_metric)} "
                        f"metric(s)."
                    ),
                    severity=(
                        "high" if context.monitoring_summary.anomaly_by_severity.get("high", 0) > 0
                        else "info"
                    ),
                )
            )

        # Recommended actions: 来自 retrofit recommendations
        recommended_actions: List[AIRecommendedAction] = []
        for rec in rf.recommendations[:3]:
            recommended_actions.append(
                AIRecommendedAction(
                    action=rec.get("next_action", "Review by qualified engineering personnel"),
                    reason=rec.get("rationale", "Based on prototype rule engine output."),
                    urgency=rec.get("urgency", "low"),
                )
            )
        if not recommended_actions:
            recommended_actions.append(
                AIRecommendedAction(
                    action="Continue routine prototype monitoring.",
                    reason="No active prototype retrofit recommendations.",
                    urgency="low",
                )
            )

        return self._guard_safety(AIResponse(
            answer=answer,
            key_findings=key_findings,
            evidence=context.evidence_chain,
            knowledge_evidence=list(knowledge_evidence or []),
            recommended_actions=recommended_actions,
            disclaimer=AI_DISCLAIMER,
            provider=self.name,
            model=self.model,
            calculation_version=AI_VERSION,
            created_at=datetime.utcnow(),
        ))

    # ------------------------------------------------------------------
    # Answer (问题路由)
    # ------------------------------------------------------------------
    def generate_answer(
        self,
        context: EngineeringContext,
        question: str,
        knowledge_evidence: Optional[List[dict]] = None,
    ) -> AIResponse:
        q_lower = question.lower()
        # 关键词路由
        if any(kw in q_lower for kw in ("总结", "summarize", "summary", "健康", "health", "状况", "condition")):
            return self.generate_summary(context, knowledge_evidence=knowledge_evidence)
        if any(kw in q_lower for kw in ("风险", "risk", "highrisk", "abnormal")):
            return self._explain_risk(context, knowledge_evidence=knowledge_evidence)
        if any(kw in q_lower for kw in ("改造", "retrofit", "优先级", "priority", "recommend")):
            return self._explain_retrofit(context, knowledge_evidence=knowledge_evidence)
        if any(kw in q_lower for kw in ("异常", "anomaly", "裂缝", "crack", "倾斜", "tilt", "湿度", "humidity")):
            return self._explain_anomaly(context, knowledge_evidence=knowledge_evidence)
        # default = summary
        return self.generate_summary(context, knowledge_evidence=knowledge_evidence)

    # ------------------------------------------------------------------
    # 细分问题回答
    # ------------------------------------------------------------------
    def _explain_risk(
        self,
        context: EngineeringContext,
        knowledge_evidence: Optional[List[dict]] = None,
    ) -> AIResponse:
        r = context.risk
        h = context.health
        b = context.building
        rf = context.retrofit

        bhi_str = f"{h.bhi:.2f}" if h.bhi is not None else "N/A"
        answer = (
            f"Prototype Risk Classification for '{b.name}' is {r.risk_level or 'N/A'}. "
            f"Inputs: BHI={bhi_str} (calculation_version={h.calculation_version}); "
            f"anomalies high={r.n_high}, medium={r.n_medium}, low={r.n_low}. "
            f"Calculation version: {h.calculation_version} for BHI, "
            f"{rf.calculation_version} for retrofit priority. "
            f"This is a Prototype Risk Classification, not a legally "
            f"binding building safety grade. Qualified professional review "
            f"is required for any safety-relevant conclusion."
        )

        key_findings = []
        if r.risk_level:
            sev = "high" if r.risk_level == "HighRisk" else (
                "medium" if r.risk_level == "Abnormal" else (
                    "low" if r.risk_level == "Attention" else "info"
                )
            )
            key_findings.append(
                AIKeyFinding(
                    title=f"Risk: {r.risk_level}",
                    description=r.explanation or "Prototype risk classification.",
                    severity=sev,
                )
            )
        if h.weakest_dimension:
            key_findings.append(
                AIKeyFinding(
                    title=f"Weakest BHI dimension: {h.weakest_dimension}",
                    description=f"BHI={bhi_str}; dimension value is the lowest of 5.",
                    severity="info",
                )
            )

        return self._guard_safety(AIResponse(
            answer=answer,
            key_findings=key_findings,
            evidence=context.evidence_chain,
            knowledge_evidence=list(knowledge_evidence or []),
            recommended_actions=[
                AIRecommendedAction(
                    action="Review prototype risk classification with qualified engineering personnel.",
                    reason="Risk level is a prototype parameter; professional review required for actionable decisions.",
                    urgency="high" if r.risk_level == "HighRisk" else "medium",
                )
            ],
            disclaimer=AI_DISCLAIMER,
            provider=self.name,
            model=self.model,
            calculation_version=AI_VERSION,
            created_at=datetime.utcnow(),
        ))

    def _explain_retrofit(
        self,
        context: EngineeringContext,
        knowledge_evidence: Optional[List[dict]] = None,
    ) -> AIResponse:
        rf = context.retrofit
        b = context.building

        rec_lines = []
        for i, rec in enumerate(rf.recommendations[:5], start=1):
            rec_lines.append(
                f"  {i}. [{rec.get('category')}] {rec.get('title')} "
                f"(priority={rec.get('priority_score'):.2f}, "
                f"urgency={rec.get('urgency')}, cost={rec.get('estimated_cost_level')})"
            )
        rec_block = "\n".join(rec_lines) if rec_lines else "  (none)"

        priority_str = f"{rf.overall_priority:.2f}"
        level_str = rf.overall_priority_level
        answer = (
            f"Retrofit decision support for '{b.name}' "
            f"(calculation_version={rf.calculation_version}):\n"
            f"  Overall priority: {priority_str} ({level_str})\n"
            f"  Recommendation count: {rf.recommendation_count}\n"
            f"  Recommendations (priority descending):\n{rec_block}\n"
            f"Note: priority scores and recommendations are computed by the "
            f"prototype rule engine from existing monitoring / anomaly / "
            f"health / risk data. This is engineering decision support only; "
            f"all recommendations require qualified professional review."
        )

        key_findings = []
        for rec in rf.recommendations[:3]:
            sev = "high" if rec.get("urgency") in ("high", "critical") else (
                "medium" if rec.get("urgency") == "medium" else "low"
            )
            key_findings.append(
                AIKeyFinding(
                    title=rec.get("title", "Recommendation"),
                    description=(
                        f"Priority={rec.get('priority_score'):.2f}; "
                        f"rationale: {rec.get('rationale', '')[:120]}"
                    ),
                    severity=sev,
                )
            )

        recommended_actions = [
            AIRecommendedAction(
                action=rec.get("next_action", "Review by qualified engineering personnel"),
                reason=rec.get("rationale", "Prototype rule engine output."),
                urgency=rec.get("urgency", "low"),
            )
            for rec in rf.recommendations[:3]
        ]
        if not recommended_actions:
            recommended_actions.append(
                AIRecommendedAction(
                    action="Continue routine prototype monitoring.",
                    reason="No active prototype retrofit recommendations.",
                    urgency="low",
                )
            )

        return self._guard_safety(AIResponse(
            answer=answer,
            key_findings=key_findings,
            evidence=context.evidence_chain,
            knowledge_evidence=list(knowledge_evidence or []),
            recommended_actions=recommended_actions,
            disclaimer=AI_DISCLAIMER,
            provider=self.name,
            model=self.model,
            calculation_version=AI_VERSION,
            created_at=datetime.utcnow(),
        ))

    def _explain_anomaly(
        self,
        context: EngineeringContext,
        knowledge_evidence: Optional[List[dict]] = None,
    ) -> AIResponse:
        ms = context.monitoring_summary
        b = context.building

        # 抽取 HIGH anomaly evidence
        high_evs = [e for e in context.evidence_chain if e.source_type == "anomaly"]
        high_count = ms.anomaly_by_severity.get("high", 0)
        med_count = ms.anomaly_by_severity.get("medium", 0)
        low_count = ms.anomaly_by_severity.get("low", 0)

        # Anomaly 详细列表 (从 evidence_chain 读)
        if high_evs:
            anom_lines = [f"  - {e.description}" for e in high_evs[:5]]
            anom_block = "\n".join(anom_lines)
        else:
            anom_block = "  (no HIGH severity prototype anomalies)"

        answer = (
            f"Prototype anomaly summary for '{b.name}':\n"
            f"  Total: {ms.anomaly_total} ({high_count} HIGH, "
            f"{med_count} MEDIUM, {low_count} LOW)\n"
            f"  Detection methods: {ms.anomaly_by_method}\n"
            f"  Recent HIGH-severity prototype anomalies:\n{anom_block}\n"
            f"Note: prototype anomalies are produced by V1 deterministic "
            f"anomaly detectors (threshold / rate-of-change / z-score). "
            f"This is not a real-world safety warning. Professional review "
            f"required for engineering action."
        )

        key_findings = []
        if high_count > 0:
            key_findings.append(
                AIKeyFinding(
                    title=f"{high_count} HIGH-severity prototype anomalies",
                    description="Detected by V1 anomaly detectors; engineering review recommended.",
                    severity="high",
                )
            )
        if med_count > 0:
            key_findings.append(
                AIKeyFinding(
                    title=f"{med_count} MEDIUM-severity prototype anomalies",
                    description="Continue monitoring; professional review if trend continues.",
                    severity="medium",
                )
            )
        if not key_findings:
            key_findings.append(
                AIKeyFinding(
                    title="No active HIGH/MEDIUM prototype anomalies",
                    description="All monitored metrics within prototype thresholds.",
                    severity="info",
                )
            )

        recommended_actions = [
            AIRecommendedAction(
                action="Review HIGH-severity prototype anomalies with engineering personnel.",
                reason=f"{high_count} HIGH-severity prototype anomalies detected; prototype thresholds may be exceeded.",
                urgency="high" if high_count > 0 else "low",
            ),
            AIRecommendedAction(
                action="Continue routine monitoring; consider recalibration if anomalies persist.",
                reason="Prototype anomaly counts should be reviewed over time.",
                urgency="low",
            ),
        ]

        return self._guard_safety(AIResponse(
            answer=answer,
            key_findings=key_findings,
            evidence=context.evidence_chain,
            knowledge_evidence=list(knowledge_evidence or []),
            recommended_actions=recommended_actions,
            disclaimer=AI_DISCLAIMER,
            provider=self.name,
            model=self.model,
            calculation_version=AI_VERSION,
            created_at=datetime.utcnow(),
        ))
