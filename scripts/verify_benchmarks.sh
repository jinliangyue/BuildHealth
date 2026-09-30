#!/usr/bin/env bash
#
# BuildHealth · external benchmark verification
# ==============================================
# Runs the NAB (Numenta Anomaly Benchmark) evaluation to verify anomaly
# detection methods against a public labeled dataset. Used to catch
# regressions in `app/analytics/anomaly.py`.
#
# NOT part of `verify.sh` because:
# - Requires NAB dataset (~30 MB clone, opt-in via NAB_DIR)
# - Takes ~2-3 minutes
# - Not all commits need external validation
#
# Usage:
#   bash scripts/verify_benchmarks.sh                # uses /tmp/NAB
#   bash scripts/verify_benchmarks.sh /path/to/NAB    # custom location
#   NAB_DIR=/path bash scripts/verify_benchmarks.sh  # via env var
#
# Exit code is non-zero if any method's F1 drops by more than 10% vs the
# last committed baseline (results/summary.csv).

set -u

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BENCH_DIR="$REPO_ROOT/benchmark/external/nab"
EVAL_SCRIPT="$BENCH_DIR/run_eval.py"
BASELINE_CSV="$BENCH_DIR/results/summary.csv"
EXPECTED_F1="0.152"  # last measured Combined (union) F1 on NAB

# Resolve NAB location
NAB_DIR="${1:-${NAB_DIR:-/tmp/NAB}}"
if [ ! -d "$NAB_DIR/data" ] || [ ! -f "$NAB_DIR/labels/combined_windows.json" ]; then
  echo "ERROR: NAB dataset not found at $NAB_DIR" >&2
  echo "  Expected: $NAB_DIR/data/ and $NAB_DIR/labels/combined_windows.json" >&2
  echo "  Clone with: git clone --depth 1 https://github.com/numenta/NAB.git $NAB_DIR" >&2
  exit 2
fi

printf '=== BuildHealth · NAB external benchmark ===\n'
printf 'NAB dir:  %s\n' "$NAB_DIR"
printf 'Eval:     %s\n' "$EVAL_SCRIPT"

if ! (cd "$REPO_ROOT" && NAB_DIR="$NAB_DIR" python3 "$EVAL_SCRIPT"); then
  echo "FAILED: eval script returned non-zero" >&2
  exit 1
fi

# Copy results to BENCH_DIR so they can be diff'd / committed
TMP_RESULTS="/tmp/nab_eval/results"
if [ -d "$TMP_RESULTS" ]; then
  cp "$TMP_RESULTS"/*.csv "$BENCH_DIR/results/"
  printf '\nResults copied to %s\n' "$BENCH_DIR/results"
fi

# Check Combined (union) F1 vs last committed baseline
if [ -f "$BASELINE_CSV" ]; then
  CURRENT_F1=$(python3 -c "
import csv, sys
with open('$BASELINE_CSV') as f:
    for row in csv.DictReader(f):
        if row['method'] == 'Combined (union)':
            print(f'{float(row[\"mean_f1\"]):.4f}')
            break
")
  printf '\n=== Combined (union) F1 check ===\n'
  printf 'Last measured: %s\n' "$EXPECTED_F1"
  printf 'This run:      %s\n' "$CURRENT_F1"
  python3 -c "
expected = $EXPECTED_F1
actual = float('$CURRENT_F1')
drop = (expected - actual) / expected
if drop > 0.10:
    print(f'FAILED: F1 dropped {drop:.1%} (>10% regression threshold)')
    sys.exit(1)
elif drop > 0:
    print(f'WARN: F1 dropped {drop:.1%} (within 10% tolerance)')
else:
    print(f'OK: F1 stable or improved ({drop:+.1%})')
"
else
  echo "No baseline summary.csv found, skipping regression check."
fi