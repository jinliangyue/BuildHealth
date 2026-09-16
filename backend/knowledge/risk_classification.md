<!--
title: Risk Classification Concepts
purpose: Conceptual explanation of the prototype 4-tier risk classification.
source: BuildHealth Internal Engineering Notes
-->

# Risk Classification Concepts

> **BuildHealth Internal Engineering Notes** · Prototype
> 4-tier risk derived from BHI and anomaly counts. **NOT** a legal
> building safety grade.

## Four Tiers

The system maps each building to exactly one of four tiers, using
the most recent Health Assessment score plus the current active
anomaly counts.

| Tier | Boundary | What It Means |
|---|---|---|
| Normal | BHI ≥ 90 | All dimensions healthy, no significant anomalies |
| Attention | BHI 75-89 | Some concerns; continued monitoring advised |
| Abnormal | BHI 60-74 | Active deterioration signals; engineering review warranted |
| HighRisk | BHI < 60 | Multiple severe signals; immediate professional review required |

These thresholds are the same as BHI's tier boundaries, but the
risk classification is its own label and is not the same as "BHI
tier". The risk classification applies an additional **override
rule** on top of the BHI bands.

## HIGH Override Rule

If the building has **any** HIGH-severity active anomaly, the risk
classification is forced to at least `Attention`, even if BHI is in
the Normal range. The rationale: a Normal-tier BHI that masks
HIGH-severity events is a false negative in the prototype, so the
override prevents that failure mode.

This rule is asymmetric — it can only push risk **up**, never down.

## Prototype Status

This is a **Prototype Risk Classification**, not a national standard
and not a legal building safety grade. The mandatory disclaimer
appears in every API response and every AI response. The system must
not be used as a substitute for professional inspection, safety
appraisal, or regulatory compliance review.

## What Risk Classification Is Not

- It is **not** a probabilistic statement ("there is an X% chance
  this building is unsafe").
- It is **not** a structural-engineering verdict.
- It is **not** a regulatory compliance check.
- It does **not** imply a recommended action; that is the job of
  the retrofit decision layer.

## Relationship to Retrofit

Risk classification is one input to the retrofit priority score
(RP-v1.0). Specifically, the `risk_severity` sub-score of priority
maps risk tiers to severity numbers, with HighRisk giving the
highest severity contribution. A building can have a low priority
despite a HighRisk tier if its retrofit decisions all involve cheap
low-urgency actions; conversely, a building with Normal risk can
have a high retrofit priority if it has a single very urgent
recommendation.
