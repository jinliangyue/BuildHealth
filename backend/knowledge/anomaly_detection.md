<!--
title: Anomaly Detection Concepts
purpose: Conceptual explanation of the three prototype anomaly detection methods.
source: BuildHealth Internal Engineering Notes
-->

# Anomaly Detection Concepts

> **BuildHealth Internal Engineering Notes** · Prototype
> The three anomaly-detection methods are explained here conceptually.
> Quantitative thresholds live in `backend/app/analytics/config.py`.

## Three Methods Overview

The system uses three independent methods, each capturing a different
shape of "abnormal". When any method fires, the system records a RiskAlert
in the database with a severity (low / medium / high) and a method tag.

### Threshold Method

Triggers when a single reading exceeds a fixed absolute bound for that
metric. This is the most conservative detector: it requires no historical
context, so it works the moment a sensor comes online, but it also
misses slow drift and cannot distinguish "noisy sensor" from "real
spike" without a separate human review.

Threshold rules exist for crack_width, tilt, temperature, and humidity.
Electricity uses no absolute threshold because its baseline depends on
the building's installed equipment and operating schedule.

### Rate of Change Method

Triggers when the **relative** change between two consecutive readings
exceeds a percentage bound, **and** the absolute change exceeds a
minimum physical threshold. This catches drift that the threshold
method would only see once a value is already alarming.

For example, crack_width growing by 0.10 mm in 24 hours fires rate_of_change
even if 0.10 mm is below the absolute threshold. The dual-gate
(relative + absolute) prevents false positives from sensor noise on
a tight band.

### Z-score Method

Triggers when a reading's statistical distance from the recent history
exceeds a fixed sigma. Operates on a rolling 7-day window. Captures
behaviour the first two methods miss: a reading that is **unusual for
this building's history** but does not yet cross any absolute or
relative bound.

Disabled for electricity and humidity, because their natural variance
is so high that a z-score would be noisy and unhelpful.

## Practical Limits

- All three methods operate on the existing monitoring stream only.
  None infers anomalies from missing data, from power outages, or from
  sensor dropout.
- An anomaly is **not** an engineering conclusion. It is a
  signal that engineering review is warranted. The risk classification
  layer applies the override rule on top of anomaly counts.
- Anomaly severity is **not** a legal grade. The threshold and
  rate-of_change magnitudes live in `app/analytics/config.py` and
  are tagged as Prototype parameters.

## Composition

Multiple methods may fire on the same reading. A reading above the
absolute threshold **and** with a high z-score receives two RiskAlerts
in the same window. The 6-hour dedup logic prevents the same
(sensor, metric, method, severity) from re-firing within 6 hours, so a
spike does not flood the alerts table.
