<!--
title: Health Assessment (BHI) Concepts
purpose: Conceptual explanation of the prototype Building Health Index.
source: BuildHealth Internal Engineering Notes
-->

# Health Assessment (BHI) Concepts

> **BuildHealth Internal Engineering Notes** · Prototype
> BHI is a single 0-100 number that summarizes 5 sub-dimensions. It is
> **NOT** a national or industry standard.

## Five Dimensions

BHI is a weighted sum of 5 sub-scores, each on a 0-100 scale where
higher is healthier.

| Dimension | What It Captures | Data Source |
|---|---|---|
| Structural Safety | Crack and tilt anomalies | Anomaly count by severity |
| Facility Condition | Age vs design life | Building's `current_age`, `design_life` |
| Environmental Quality | Temperature and humidity stability | Monitoring time series |
| Energy Performance | Electricity load stability | Monitoring time series |
| Fire Safety | Placeholder based on floors and age | Building metadata only |

Fire Safety is intentionally a placeholder in V1 because no fire-system
monitoring data is ingested. The placeholder contribution biases the
overall score but does not claim to measure real fire safety.

## Weights

The five weights are versioned constants in
`backend/app/analytics/config.py` (`BHI_WEIGHTS`). Structural Safety
carries the largest weight because of the irreversible nature of
structural damage. Energy Performance carries the smallest weight
because a single monitoring stream is too narrow to characterize
building energy health.

The five weights sum to 1.0; this is asserted at runtime.

## Calculation Versioning

Every `HealthAssessment` row stores the calculation version
(`calculation_version`, e.g. `BHI-v1.0`). If the formula is later
revised, new rows get the new version; old rows are preserved for
history. The "current BHI" displayed in the UI is the most recent
assessment row.

## Reading a BHI

A BHI of 96 on a brand-new 5-year-old office building means the
structural dimension is fine (no anomalies), the age dimension is fine
(5/50), the environmental and energy dimensions are fine (stable
monitoring), and the fire placeholder is fine (low floors, low age).
There is nothing to retrofit.

A BHI of 54 on a 31-year-old masonry building with 86 high-severity
crack anomalies means the structural dimension has been pulled down to
0 by log-decay of anomaly count. Other dimensions are still near
100. The retrofit system still issues recommendations on top of this
BHI; the BHI itself is **not** a "do something" signal — it is a
**context** signal.

## Disclaimer

BHI = Prototype Design Parameters, not a national or industry
standard, not a legal building safety grade. The system does not
predict building collapse, does not replace professional inspection,
and does not replace safety appraisal. The mandatory disclaimer
appears in every AI response and every Retrofit decision response.
