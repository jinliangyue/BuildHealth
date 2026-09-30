"""
External dataset evaluation: NAB (Numenta Anomaly Benchmark).

Goal: Test BuildHealth's three anomaly detection methods (threshold,
rate-of-change, z-score) on a publicly labeled dataset, with a
standard ML baseline (Isolation Forest) for comparison.

Method adaptation:
- Threshold: absolute-value rule. Hard-coded metric thresholds in
  BuildHealth (0.30 mm crack, 4.0 tilt) don't apply to NAB's generic
  time series. We use data-driven percentiles: 95/97/99 = LOW/MEDIUM/HIGH.
  This preserves the "value above a threshold = anomaly" logic.
- Rate of change: dual-gate (absolute + relative). Same logic as
  BuildHealth, but absolute gate uses 3 * rolling_std to be unit-agnostic.
- Z-score: 7-day rolling window (5-min interval -> 2016 samples), |z| > 4.
  Identical to BuildHealth's detect_zscore.
- Combined: union of three methods (matches BuildHealth's deduped output).

Evaluation:
- Point-level. Each timestamp: predicted anomaly or not.
- Anomaly masks built from NAB's per-file anomaly windows.
- Per-file: precision, recall, F1.
- Aggregated: macro-average across files with anomalies.
- Excluded: files with no anomaly windows (no positives to detect).

Output:
- Per-file metrics CSV
- Method summary (mean/median P/R/F1)
- Console report
"""

import json
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest


NAB_ROOT = Path("/tmp/NAB")
LABELS_PATH = NAB_ROOT / "labels" / "combined_windows.json"
DATA_ROOT = NAB_ROOT / "data"
OUT_DIR = Path("/tmp/nab_eval/results")
OUT_DIR.mkdir(parents=True, exist_ok=True)


# ===== Method 1: Threshold (percentile-based, unit-agnostic) =====
def detect_threshold_percentile(values: np.ndarray) -> np.ndarray:
    """Flag points where value > 99th percentile (= HIGH), 97 (MEDIUM), 95 (LOW).
    Any severity = anomaly."""
    p95 = np.percentile(values, 95)
    p97 = np.percentile(values, 97)
    p99 = np.percentile(values, 99)
    flagged = (values >= p95).astype(int)
    return flagged


# ===== Method 2: Rate of Change (dual-gate, std-normalized) =====
def detect_rate_of_change(values: np.ndarray, k_std: float = 3.0, rel_pct: float = 30.0) -> np.ndarray:
    """Flag points where |delta| > k_std * rolling_std AND |delta_pct| > rel_pct.
    Mirrors BuildHealth's dual-gate logic with std-normalized absolute gate."""
    flagged = np.zeros(len(values), dtype=int)
    # rolling std on a 50-sample window (covers ~4 hours at 5-min interval)
    # need at least 1 sample to compute std
    win = 50
    for i in range(1, len(values)):
        prev = values[i - 1]
        curr = values[i]
        if prev == 0:
            rel = float("inf") if abs(curr - prev) > 0 else 0.0
        else:
            rel = abs(curr - prev) / abs(prev) * 100.0

        abs_delta = abs(curr - prev)
        # local std over preceding window (or whole series if not enough)
        if i >= win:
            local_std = np.std(values[i - win: i])
        else:
            local_std = np.std(values[:i]) if i > 1 else 0.0

        if local_std == 0:
            continue

        if abs_delta > k_std * local_std and rel > rel_pct:
            flagged[i] = 1
    return flagged


# ===== Method 3: Z-score (7-day rolling window) =====
def detect_zscore(values: np.ndarray, window: int = 2016, threshold: float = 4.0) -> np.ndarray:
    """Flag points where |z| > threshold using preceding `window` samples.
    Identical logic to BuildHealth's detect_zscore."""
    flagged = np.zeros(len(values), dtype=int)
    for i in range(window, len(values)):
        hist = values[i - window: i]
        mean = hist.mean()
        std = hist.std()
        if std == 0:
            continue
        z = (values[i] - mean) / std
        if abs(z) > threshold:
            flagged[i] = 1
    return flagged


# ===== Method 4: Isolation Forest (sklearn, ML baseline) =====
def detect_isoforest(values: np.ndarray, contamination: float = 0.01, random_state: int = 42) -> np.ndarray:
    """Univariate isolation forest: reshape to (n, 1), fit, predict."""
    X = values.reshape(-1, 1)
    iso = IsolationForest(contamination=contamination, random_state=random_state, n_estimators=100)
    iso.fit(X)
    pred = iso.predict(X)  # -1 = anomaly, 1 = normal
    flagged = (pred == -1).astype(int)
    return flagged


# ===== Method 5: Combined (union of methods 1-3) =====
def detect_combined(values: np.ndarray) -> np.ndarray:
    """Union of threshold, rate-of-change, z-score.
    Matches BuildHealth's deduplication behavior (any method flagging = anomaly)."""
    t = detect_threshold_percentile(values)
    r = detect_rate_of_change(values)
    z = detect_zscore(values)
    combined = ((t + r + z) > 0).astype(int)
    return combined


# ===== Method 6: Rolling MAD (Median Absolute Deviation) =====
def detect_rolling_mad(values: np.ndarray, window: int = 2016, k: float = 4.0) -> np.ndarray:
    """Flag points where |x - rolling_median| / rolling_mad > k.
    Robust alternative to z-score (resistant to outliers in the window)."""
    flagged = np.zeros(len(values), dtype=int)
    for i in range(window, len(values)):
        hist = values[i - window: i]
        median = np.median(hist)
        mad = np.median(np.abs(hist - median))
        if mad == 0:
            continue
        score = abs(values[i] - median) / (1.4826 * mad)  # 1.4826 makes MAD consistent with std for normal
        if score > k:
            flagged[i] = 1
    return flagged


# ===== Method 7: Naive baseline (random flagging) =====
def detect_naive(values: np.ndarray, rate: float = 0.01, seed: int = 42) -> np.ndarray:
    """Flag random points at given rate. Baseline to show methods beat chance."""
    rng = np.random.default_rng(seed)
    flagged = (rng.random(len(values)) < rate).astype(int)
    return flagged


# ===== Metrics =====
def window_recall(y_true: np.ndarray, y_pred: np.ndarray, windows: list, timestamps) -> dict:
    """Window-level recall: of all anomaly windows, how many had >= 1 detection.
    More aligned with NAB's intent than point-level recall."""
    window_hits = 0
    for win in windows:
        start = pd.to_datetime(win[0])
        end = pd.to_datetime(win[1])
        mask = (timestamps >= start) & (timestamps <= end)
        idx = np.where(mask)[0]
        if len(idx) == 0:
            continue
        if y_pred[idx].sum() > 0:
            window_hits += 1
    return {"window_recall": window_hits / len(windows) if windows else float("nan")}


def prf1(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """Standard precision, recall, F1.
    Edge cases:
    - No positives and no predictions: skip (returns None).
    - No positives but some predictions: precision undefined (0/0); treat as NaN.
    - Positives but no predictions: recall = 0, precision undefined."""
    tp = int(((y_true == 1) & (y_pred == 1)).sum())
    fp = int(((y_true == 0) & (y_pred == 1)).sum())
    fn = int(((y_true == 1) & (y_pred == 0)).sum())

    precision = tp / (tp + fp) if (tp + fp) > 0 else float("nan")
    recall = tp / (tp + fn) if (tp + fn) > 0 else float("nan")
    if precision != precision or recall != recall:  # NaN check
        f1 = float("nan")
    elif (precision + recall) == 0:
        f1 = 0.0
    else:
        f1 = 2 * precision * recall / (precision + recall)
    return {
        "tp": tp, "fp": fp, "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "n_pos": int((y_true == 1).sum()),
        "n_pred": int((y_pred == 1).sum()),
    }


# ===== Load NAB file + build ground-truth mask =====
def load_file(path: Path, windows: list) -> tuple:
    """Returns (values, y_true) where y_true is 0/1 anomaly mask."""
    df = pd.read_csv(path)
    timestamps = pd.to_datetime(df["timestamp"])
    values = df["value"].astype(float).to_numpy()
    y_true = np.zeros(len(values), dtype=int)
    for win in windows:
        start = pd.to_datetime(win[0])
        end = pd.to_datetime(win[1])
        mask = (timestamps >= start) & (timestamps <= end)
        y_true |= mask.astype(int).to_numpy()
    return values, y_true


# ===== Main =====
def main():
    with open(LABELS_PATH) as f:
        labels = json.load(f)

    files_with_anomalies = {k: v for k, v in labels.items() if v}
    print(f"NAB: {len(files_with_anomalies)} files with anomalies (out of {len(labels)} total)")

    methods = {
        "Threshold (percentile)": detect_threshold_percentile,
        "Rate of Change": detect_rate_of_change,
        "Z-score (7d)": detect_zscore,
        "Rolling MAD": detect_rolling_mad,
        "Isolation Forest": detect_isoforest,
        "Combined (union)": detect_combined,
        "Naive (1% random)": detect_naive,
    }

    rows = []
    file_results = defaultdict(list)  # method -> list of metric dicts

    for fname, windows in sorted(files_with_anomalies.items()):
        path = DATA_ROOT / fname
        if not path.exists():
            print(f"  [skip] {fname}: not found")
            continue

        values, y_true = load_file(path, windows)
        if len(values) < 2100:
            print(f"  [skip] {fname}: too short ({len(values)} points)")
            continue

        for method_name, method_fn in methods.items():
            y_pred = method_fn(values)
            m = prf1(y_true, y_pred)
            timestamps = pd.to_datetime(pd.read_csv(path)["timestamp"])
            wr = window_recall(y_true, y_pred, windows, timestamps)
            m["window_recall"] = wr["window_recall"]
            m["file"] = fname
            m["method"] = method_name
            rows.append(m)
            file_results[method_name].append(m)

    df = pd.DataFrame(rows)
    df.to_csv(OUT_DIR / "per_file_metrics.csv", index=False)

    # ===== Aggregate =====
    print("\n" + "=" * 80)
    print("AGGREGATE RESULTS (macro-average across files)")
    print("=" * 80)

    summary = []
    for method_name, ms in file_results.items():
        # only files where ground truth has at least 1 positive
        valid = [m for m in ms if m["n_pos"] > 0]
        if not valid:
            continue
        prec = np.nanmean([m["precision"] for m in valid])
        rec = np.nanmean([m["recall"] for m in valid])
        f1 = np.nanmean([m["f1"] for m in valid])
        wr = np.nanmean([m["window_recall"] for m in valid])
        med_prec = np.nanmedian([m["precision"] for m in valid])
        med_rec = np.nanmedian([m["recall"] for m in valid])
        med_f1 = np.nanmedian([m["f1"] for m in valid])
        summary.append({
            "method": method_name,
            "n_files": len(valid),
            "mean_precision": prec,
            "mean_recall": rec,
            "mean_f1": f1,
            "mean_window_recall": wr,
            "median_precision": med_prec,
            "median_recall": med_rec,
            "median_f1": med_f1,
        })

    summary_df = pd.DataFrame(summary)
    summary_df.to_csv(OUT_DIR / "summary.csv", index=False)
    print(summary_df.to_string(index=False, float_format=lambda x: f"{x:.4f}" if isinstance(x, float) else str(x)))

    # ===== Per-category breakdown =====
    print("\n" + "=" * 80)
    print("PER-CATEGORY BREAKDOWN (mean F1)")
    print("=" * 80)
    df["category"] = df["file"].apply(lambda x: x.split("/")[0])
    cat_breakdown = df.groupby(["category", "method"]).agg(
        n=("f1", "count"),
        mean_f1=("f1", lambda s: np.nanmean(s)),
        mean_precision=("precision", lambda s: np.nanmean(s)),
        mean_recall=("recall", lambda s: np.nanmean(s)),
    ).reset_index()
    cat_pivot = cat_breakdown.pivot(index="category", columns="method", values="mean_f1")
    print(cat_pivot.to_string(float_format=lambda x: f"{x:.3f}" if isinstance(x, float) else str(x)))
    cat_pivot.to_csv(OUT_DIR / "per_category_f1.csv")

    # ===== Window-level recall ranking =====
    print("\n" + "=" * 80)
    print("WINDOW-LEVEL RECALL (mean across files: of all anomaly windows, "
          "what fraction had >= 1 detection)")
    print("=" * 80)
    wr_ranking = sorted(summary, key=lambda x: x["mean_window_recall"], reverse=True)
    for s in wr_ranking:
        bar = "█" * int(s["mean_window_recall"] * 50)
        print(f"  {s['method']:25s}  {s['mean_window_recall']:.3f}  {bar}")

    print(f"\nResults written to {OUT_DIR}/")
    print(f"  per_file_metrics.csv ({len(df)} rows)")
    print(f"  summary.csv ({len(summary_df)} rows)")
    print(f"  per_category_f1.csv")


if __name__ == "__main__":
    main()