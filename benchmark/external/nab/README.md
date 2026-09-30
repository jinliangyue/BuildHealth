# BuildHealth × NAB External Evaluation

External benchmark of BuildHealth's anomaly detection methods against
[NAB (Numenta Anomaly Benchmark)](https://github.com/numenta/NAB) — 58
publicly labeled time series, 52 with anomaly windows.

## What this is

A point-level precision/recall evaluation of seven anomaly detection
methods on a third-party dataset with ground-truth anomaly windows:

- **Threshold (percentile)**: data-driven percentile thresholds
  (95/97/99 = LOW/MEDIUM/HIGH). Adapts BuildHealth's hardcoded
  metric thresholds (0.30 mm, 4.0 ‰, etc.) to generic time series.
- **Rate of Change**: dual-gate (absolute + relative), with std-
  normalized absolute gate.
- **Z-score (7d)**: 7-day rolling window, |z| > 4. Identical to
  BuildHealth's `detect_zscore`.
- **Rolling MAD**: robust alternative using median + MAD. New
  baseline for comparison.
- **Isolation Forest**: sklearn's IsolationForest, contamination=0.01.
  Standard ML baseline.
- **Combined (union)**: BuildHealth's actual architecture — union of
  three methods after deduplication.
- **Naive (1% random)**: sanity check to verify other methods beat
  chance.

## What this is not

- Not a claim of SOTA performance on NAB. Top published NAB methods
  (Numenta HTM, etc.) achieve F1 ≈ 0.40 with deep NAB-specific tuning.
- Not a hyperparameter search. Methods use BuildHealth defaults
  adapted for unit-agnostic evaluation.
- Not a substitute for in-domain validation. Building engineering
  still needs real labeled structural data, which doesn't exist publicly.

## How to run

```bash
# 1. Get NAB dataset (one-time, ~30 MB)
git clone --depth 1 https://github.com/numenta/NAB.git /tmp/NAB

# 2. Run evaluation
cd BuildHealth
python benchmark/external/nab/run_eval.py
```

The script reads from `/tmp/NAB/` and writes CSV results to
`benchmark/external/nab/results/`. Runtime ≈ 2-3 minutes on M2 Air.

## Results (last run: 2026-09-30)

Point-level metrics (macro-average across 43 files, 9 skipped for being
too short for the 7-day window):

| Method | Precision | Recall | F1 | Window Recall |
|---|---|---|---|---|
| **Combined (union)** | 0.182 | **0.152** | **0.152** | **0.960** |
| Rolling MAD | 0.324 | 0.135 | 0.146 | 0.593 |
| Threshold (percentile) | 0.188 | 0.121 | 0.132 | 0.952 |
| Z-score (7d) | **0.456** | 0.036 | 0.075 | 0.559 |
| Isolation Forest | 0.376 | 0.037 | 0.068 | 0.925 |
| Rate of Change | 0.185 | 0.029 | 0.046 | 0.907 |
| Naive (1% random) | 0.102 | 0.009 | 0.017 | 0.926 |

Window Recall = fraction of anomaly windows that had ≥1 detection.

## What the numbers mean

**Combined (BuildHealth's actual architecture) has the highest F1.**
This is the headline result: combining three methods with deduplication
outperforms any single method, including Isolation Forest.

**Z-score has the highest precision (0.456)** but the worst window
recall (0.559). It is conservative — when it flags, it is right ~46%
of the time, but it misses most anomaly windows entirely. Combined's
union design trades precision for recall, which is the standard
trade-off for anomaly detection.

**All BuildHealth logic methods (Threshold, RoC, Z-score, Combined)
beat the naive baseline** at point-level F1.

**Window-level recall is dominated by prediction count, not quality.**
Naive 1% random achieves 92.6% window recall — nearly identical to
Isolation Forest (92.5%). This is because NAB anomaly windows are
typically wide enough that random flagging at 1% density touches most
of them. Window-level recall alone is not a strong quality signal;
point-level precision matters more.

## What to put in a résumé

Acceptable framing (point-level, BuildHealth-favorable):

> Three-method anomaly detection (threshold, rate-of-change, z-score)
> achieves F1 = 0.152 on the NAB benchmark, outperforming any single
> method (best single: F1 = 0.146) and 9× the naive baseline (F1 =
> 0.017). The combined architecture (union after deduplication) was
> the design intent; external data confirmed it.

What to avoid saying:

- "BuildHealth beats state-of-the-art on NAB" — false. Top methods are
  F1 ≈ 0.40.
- "Combined beats Isolation Forest 2:1" — both have F1 ≈ 0.07-0.15;
  Combined is better, not by 2×. (2× is the BuildHealth F1 vs naive F1,
  not vs IF.)

## Limitations of this benchmark

- Point-level scoring rewards methods that flag many points; window-
  level scoring is less informative because NAB windows are wide.
- No hyperparameter tuning per file — methods use defaults. Per-file
  tuning would inflate numbers without informing method choice.
- NAB anomaly types differ from building engineering anomalies
  (level shifts, drift, outages vs structural cracks, gradual
  deterioration). Results are indicative, not directly transferable
  to building domain.
- 9 of 52 files were skipped for being shorter than the 7-day
  rolling window.

## Files

- `run_eval.py` — standalone evaluation script
- `results/per_file_metrics.csv` — 301 rows (43 files × 7 methods)
- `results/summary.csv` — 7 rows, aggregate metrics
- `results/per_category_f1.csv` — per-NAB-category F1 breakdown