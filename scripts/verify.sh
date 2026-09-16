#!/usr/bin/env bash
#
# BuildHealth · unified verification
# ==================================
# Runs the core checks SERIALLY (this project is developed on an 8GB M2 Air;
# running the frontend build and the test suites at the same time causes
# memory-pressure thrashing that looks like a hang).
#
# Usage:
#   bash scripts/verify.sh              # backend + frontend + tsc + build
#   bash scripts/verify.sh --skip-build # skip the production build
#
# Exit code is non-zero if any stage fails. Nothing here is a substitute for
# the API smoke test, which needs a running server (see README).

set -u

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$REPO_ROOT/backend"
FRONTEND="$REPO_ROOT/frontend"

SKIP_BUILD=0
for arg in "$@"; do
  case "$arg" in
    --skip-build) SKIP_BUILD=1 ;;
    -h|--help)
      sed -n '2,14p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *)
      echo "Unknown option: $arg" >&2
      exit 2
      ;;
  esac
done

FAILED=0
STAGE=""

stage() {
  STAGE="$1"
  printf '\n=== %s ===\n' "$STAGE"
}

fail() {
  printf 'FAILED: %s\n' "$STAGE" >&2
  FAILED=1
}

# ---------------------------------------------------------------- backend
stage "Backend tests"
if [ -x "$BACKEND/venv/bin/python" ]; then
  PY="$BACKEND/venv/bin/python"
else
  PY="python3"
  echo "(no backend/venv found, falling back to python3)"
fi
if (cd "$BACKEND" && "$PY" -m pytest tests/ -q); then
  echo "OK"
else
  fail
fi

# --------------------------------------------------------------- frontend
stage "Frontend tests"
if (cd "$FRONTEND" && npm test -- --run); then
  echo "OK"
else
  fail
fi

stage "TypeScript"
if (cd "$FRONTEND" && npx tsc --noEmit); then
  echo "OK"
else
  fail
fi

# ------------------------------------------------------------------ build
if [ "$SKIP_BUILD" -eq 0 ]; then
  stage "Production build"
  if (cd "$FRONTEND" && npm run build); then
    echo "OK"
  else
    fail
  fi
else
  echo ""
  echo "(--skip-build: production build skipped)"
fi

# ---------------------------------------------------------------- summary
printf '\n================================\n'
if [ "$FAILED" -eq 0 ]; then
  echo "ALL CHECKS PASSED"
else
  echo "ONE OR MORE CHECKS FAILED"
fi
printf '================================\n'
exit "$FAILED"
