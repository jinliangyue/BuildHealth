<!--
title: Retrofit Decision Concepts (RP-v1.0)
purpose: Conceptual explanation of the prototype retrofit priority formula.
source: BuildHealth Internal Engineering Notes
-->

# Retrofit Decision Concepts (RP-v1.0)

> **BuildHealth Internal Engineering Notes** · Prototype
> 5-dimension weighted priority score, top-K recommendations with
> evidence chain. **NOT** an automatic structural design tool.

## Five Priority Dimensions

Each retrofit recommendation is assigned a 0-100 priority score
weighted from five dimensions.

| Dimension | Weight | What It Captures |
|---|---|---|
| Risk Severity | 0.35 | The building's current risk tier |
| Trend / Deterioration | 0.25 | Multi-metric drift severity |
| Component Importance | 0.20 | structural load-bearing role of the affected component |
| Intervention Urgency | 0.10 | The recommendation's own urgency label |
| Cost Efficiency | 0.10 | low / medium / high cost level (lower cost = higher efficiency) |

The five weights are constants in
`backend/app/analytics/config.py` (`RETROFIT_PRIORITY_WEIGHTS`).
They sum to 1.0; runtime-asserted.

## Priority Level Mapping

| Score | Level |
|---|---|
| 90-100 | Very High |
| 75-89 | High |
| 60-74 | Medium |
| 0-59 | Low |

A score of 100 is **not** achievable because the cost-efficiency
sub-score is capped at 90 (low cost). The maximum observable total
is 99. This is a property of the prototype parameter set, not a bug.

## Recommendation Rules

The system runs five independent rule functions over the latest
monitoring data, anomaly history, BHI, and risk tier. Each rule that
**matches** produces one RetrofitRecommendation record. A building
with no matching rules has zero recommendations, which is the
expected state for a healthy building.

| Rule | Category | Trigger | Default Urgency |
|---|---|---|---|
| crack_growth | Structural | crack_width anomaly OR z-score > 2 | HIGH if any HIGH anomaly else medium |
| tilt_trend | Structural | tilt anomaly OR z-score > 2 | HIGH if any HIGH anomaly else medium |
| moisture_control | Environment | humidity anomaly OR env score < 80 | HIGH if env < 60 else medium |
| energy_efficiency | Energy | electricity anomaly OR energy score < 80 | medium if energy < 60 else low |
| comprehensive_assessment | Structural | risk in (Abnormal, HighRisk) | HIGH if HighRisk else medium |

## Evidence Chain

Each RetrofitRecommendation row carries an `evidence_json` payload
describing the sensors, anomalies, BHI context, and risk context that
triggered the rule. The AI Engineering Assistant can surface this
chain directly to the user. The chain is the **only** way the system
justifies a recommendation — there is no other path from raw data
to a recommendation.

## Disclaimer

Priority is a **Prototype Retrofit Priority Parameter**, not a legal
or industry standard. Recommendations are engineering decision
support, not automatic structural design, not reinforcement design,
not a substitute for professional engineering review. The cost level
(low/medium/high) is a coarse bucket, not a project cost estimate.
