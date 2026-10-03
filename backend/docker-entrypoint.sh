#!/bin/sh
# BuildHealth backend entrypoint
# =================================
# Idempotent DB seed: if the SQLite file does not exist or is empty,
# run scripts.seed_data so the API has buildings / sensors / readings
# to serve. This is a one-shot, not a watcher; rerunning is a no-op
# once buildhealth.db is populated.
#
# After seeding, exec the CMD (uvicorn by default) so that signals
# (SIGTERM from `docker stop`) reach the application, not this shell.

set -e

DB_PATH="/app/data/buildhealth.db"

if [ ! -s "$DB_PATH" ]; then
    echo "[entrypoint] No database found at $DB_PATH; running seed_data.py..."
    python -m scripts.seed_data
    echo "[entrypoint] Seed complete."
else
    echo "[entrypoint] Existing database at $DB_PATH; skipping seed."
fi

echo "[entrypoint] Starting: $*"
exec "$@"
