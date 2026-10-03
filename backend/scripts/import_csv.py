"""
CSV ingestion · BuildHealth Phase 7
====================================

Append monitoring records from a CSV file into the SQLite database.

CSV format
----------
Header row is required. Accepted column order:

    building_id,sensor_id,value,recorded_at,quality_flag

    - building_id    integer; must exist in `buildings`.
    - sensor_id      integer; must exist in `sensors` AND must belong
                     to `building_id`. Catches cross-building typos.
    - value          float. Unit is whatever the sensor's `unit` column
                     says; no conversion is performed here.
    - recorded_at    ISO 8601 datetime, e.g. 2026-09-15T00:00:00.
                     Naive datetimes are treated as UTC.
    - quality_flag   one of "simulated" | "verified" | "test" | "real".

Lines starting with `#` and blank lines are ignored.

Usage
-----
    cd backend && python -m scripts.import_csv path/to/file.csv
    cd backend && python -m scripts.import_csv --dry-run path/to/file.csv
    cd backend && python -m scripts.import_csv --batch-size 500 \
            --run-anomaly path/to/file.csv

Exit codes
----------
    0  all rows imported
    1  file / format error (header missing, unreadable, etc.)
    2  validation error (some rows rejected; report printed to stdout)
    3  database error

The final line is always a JSON object summarising the run. Errors per
row are listed under `row_errors` with their 1-indexed line number.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.db.session import SessionLocal
from app.db import models as m

ALLOWED_QUALITY_FLAGS = frozenset({"simulated", "verified", "test", "real"})
REQUIRED_COLUMNS = (
    "building_id",
    "sensor_id",
    "value",
    "recorded_at",
    "quality_flag",
)
DEFAULT_BATCH_SIZE = 1000


# ----------------------------------------------------------------------------
# Validation result
# ----------------------------------------------------------------------------
@dataclass
class RowError:
    line: int          # 1-indexed source line number (header excluded)
    sensor_id: Optional[int]
    error: str

    def to_dict(self) -> Dict:
        return {"line": self.line, "sensor_id": self.sensor_id, "error": self.error}


@dataclass
class ImportReport:
    total_rows: int = 0
    inserted: int = 0
    skipped_duplicates: int = 0
    row_errors: List[RowError] = field(default_factory=list)
    sensors_touched: List[int] = field(default_factory=list)
    anomaly_runs_triggered: int = 0
    started_at: str = ""
    finished_at: str = ""

    def to_dict(self) -> Dict:
        return {
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "total_rows": self.total_rows,
            "inserted": self.inserted,
            "skipped_duplicates": self.skipped_duplicates,
            "row_errors": [e.to_dict() for e in self.row_errors],
            "sensors_touched": sorted(set(self.sensors_touched)),
            "anomaly_runs_triggered": self.anomaly_runs_triggered,
            "exit_status": _status_from_report(self),
        }


def _status_from_report(report: ImportReport) -> str:
    if report.row_errors and report.inserted > 0:
        return "partial"
    if report.row_errors:
        return "failed_validation"
    return "ok"


# ----------------------------------------------------------------------------
# Row-level validation
# ----------------------------------------------------------------------------
class RowValidationError(Exception):
    """A single row failed validation. Carries the sensor_id for the report."""


def _parse_row(
    raw: Dict[str, str],
    line_no: int,
    sensor_index: Dict[int, m.Sensor],
) -> m.MonitoringRecord:
    # Required columns
    missing = [c for c in REQUIRED_COLUMNS if c not in raw or raw[c] is None]
    if missing:
        raise RowValidationError(
            f"missing required column(s): {', '.join(missing)}"
        )

    sensor_id_str = raw["sensor_id"].strip()
    building_id_str = raw["building_id"].strip()

    # Integer ids
    try:
        sensor_id = int(sensor_id_str)
    except ValueError as exc:
        raise RowValidationError(f"sensor_id not an integer: {sensor_id_str!r}") from exc
    try:
        building_id = int(building_id_str)
    except ValueError as exc:
        raise RowValidationError(f"building_id not an integer: {building_id_str!r}") from exc

    # Sensor must exist and belong to building
    sensor = sensor_index.get(sensor_id)
    if sensor is None:
        raise RowValidationError(f"unknown sensor_id={sensor_id}")
    if sensor.building_id != building_id:
        raise RowValidationError(
            f"sensor_id={sensor_id} belongs to building_id={sensor.building_id}, "
            f"not building_id={building_id}"
        )

    # Value: float
    try:
        value = float(raw["value"].strip())
    except ValueError as exc:
        raise RowValidationError(f"value not a float: {raw['value']!r}") from exc

    # Timestamp: ISO 8601
    ts_raw = raw["recorded_at"].strip()
    try:
        timestamp = datetime.fromisoformat(ts_raw)
    except ValueError as exc:
        raise RowValidationError(
            f"recorded_at not ISO 8601: {ts_raw!r}"
        ) from exc

    # quality_flag
    quality_flag = raw["quality_flag"].strip().lower()
    if quality_flag not in ALLOWED_QUALITY_FLAGS:
        raise RowValidationError(
            f"quality_flag={quality_flag!r} not in "
            f"{sorted(ALLOWED_QUALITY_FLAGS)}"
        )

    return m.MonitoringRecord(
        sensor_id=sensor_id,
        timestamp=timestamp,
        value=value,
        quality_flag=quality_flag,
    )


# ----------------------------------------------------------------------------
# Streaming reader
# ----------------------------------------------------------------------------
def _iter_csv_rows(path: Path) -> Iterable[Tuple[int, Dict[str, str]]]:
    """Yield (line_number, row_dict) for every non-comment row in `path`.

    Lines that are blank or start with `#` (after stripping) are skipped
    silently. The line_number is the 1-indexed source line (header
    excluded) for error reporting.
    """
    with path.open("r", encoding="utf-8", newline="") as fp:
        reader = csv.DictReader(fp)
        if reader.fieldnames is None:
            raise ValueError("CSV file is empty")
        # Header check (case-sensitive by spec)
        missing = [c for c in REQUIRED_COLUMNS if c not in reader.fieldnames]
        if missing:
            raise ValueError(
                f"CSV header missing required columns: {', '.join(missing)}. "
                f"Got: {list(reader.fieldnames)}"
            )
        for line_no, row in enumerate(reader, start=1):
            # Skip fully blank lines or comment lines
            if not row or all(
                (v is None or str(v).strip() == "") for v in row.values()
            ):
                continue
            first_value = next(iter(row.values()), None)
            if isinstance(first_value, str) and first_value.lstrip().startswith("#"):
                continue
            yield line_no, row


# ----------------------------------------------------------------------------
# Anomaly re-detection for touched sensors
# ----------------------------------------------------------------------------
def _rerun_anomaly_for_sensors(
    session,
    sensor_ids: List[int],
) -> int:
    """Re-run anomaly detection for each touched sensor.

    Returns the number of sensors processed. Implementation lives in
    `app.analytics.anomaly`; we import lazily to keep this script's
    startup cost low when --run-anomaly is not used.
    """
    from app.analytics import anomaly as anom

    runs = 0
    seen_buildings: Dict[Tuple[int, int], List] = {}  # (building_id, sensor_id) -> records
    for sid in set(sensor_ids):
        sensor = session.get(m.Sensor, sid)
        if sensor is None:
            continue
        records = (
            session.execute(
                select(m.MonitoringRecord)
                .where(m.MonitoringRecord.sensor_id == sid)
                .order_by(m.MonitoringRecord.timestamp)
            )
            .scalars()
            .all()
        )
        if not records:
            continue
        prev_value = None
        history: List[float] = []
        for rec in records:
            results = anom.detect_for_record(
                sensor_id=sid,
                building_id=sensor.building_id,
                metric=sensor.sensor_type,
                timestamp=rec.timestamp,
                value=rec.value,
                previous_value=prev_value,
                history_values=history,
            )
            prev_value = rec.value
            history.append(rec.value)
            for r in results:
                # Dedup against existing alerts within ANOMALY_DEDUP_HOURS
                existing = session.execute(
                    select(m.RiskAlert)
                    .where(
                        m.RiskAlert.sensor_id == sid,
                        m.RiskAlert.metric == sensor.sensor_type,
                        m.RiskAlert.detection_method == r.detection_method,
                        m.RiskAlert.severity == r.severity,
                        m.RiskAlert.timestamp == rec.timestamp,
                    )
                    .limit(1)
                ).scalar_one_or_none()
                if existing is not None:
                    continue
                session.add(m.RiskAlert(
                    building_id=sensor.building_id,
                    sensor_id=sid,
                    metric=sensor.sensor_type,
                    timestamp=rec.timestamp,
                    current_value=r.current_value,
                    baseline_value=r.baseline_value,
                    change=r.change,
                    detection_method=r.detection_method,
                    severity=r.severity,
                    explanation=r.explanation,
                    status="active",
                ))
        runs += 1
    return runs


# ----------------------------------------------------------------------------
# Main entry point
# ----------------------------------------------------------------------------
def main(
    argv: Optional[List[str]] = None,
    *,
    session_factory=None,
) -> int:
    parser = argparse.ArgumentParser(
        description="Import monitoring records from CSV into BuildHealth."
    )
    parser.add_argument("csv_path", type=Path, help="Path to the CSV file.")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Rows per transaction (default {DEFAULT_BATCH_SIZE}).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate every row but do not insert anything.",
    )
    parser.add_argument(
        "--run-anomaly",
        action="store_true",
        help="After import, re-run anomaly detection for every touched "
             "sensor and add any new RiskAlert rows.",
    )
    args = parser.parse_args(argv)

    report = ImportReport(started_at=datetime.utcnow().isoformat() + "Z")

    # Allow tests to inject a session factory bound to an isolated
    # engine. Production callers omit the kwarg and get the default.
    factory = session_factory or SessionLocal

    try:
        session = factory()
        try:
            # Pre-load sensor index for fast validation
            sensors = session.execute(select(m.Sensor)).scalars().all()
            sensor_index: Dict[int, m.Sensor] = {s.id: s for s in sensors}

            validated_batch: List[m.MonitoringRecord] = []
            touched_sensors: List[int] = []

            for line_no, raw_row in _iter_csv_rows(args.csv_path):
                report.total_rows += 1
                try:
                    rec = _parse_row(raw_row, line_no, sensor_index)
                except RowValidationError as exc:
                    report.row_errors.append(
                        RowError(line=line_no, sensor_id=None, error=str(exc))
                    )
                    continue
                validated_batch.append(rec)
                touched_sensors.append(rec.sensor_id)
                report.sensors_touched.append(rec.sensor_id)

                if len(validated_batch) >= args.batch_size:
                    inserted, dup = _flush(session, validated_batch, args.dry_run)
                    report.inserted += inserted
                    report.skipped_duplicates += dup
                    validated_batch = []

            if validated_batch:
                inserted, dup = _flush(session, validated_batch, args.dry_run)
                report.inserted += inserted
                report.skipped_duplicates += dup

            if args.run_anomaly and not args.dry_run and touched_sensors:
                report.anomaly_runs_triggered = _rerun_anomaly_for_sensors(
                    session, touched_sensors,
                )

            if not args.dry_run:
                session.commit()

        finally:
            session.close()

    except FileNotFoundError:
        print(json.dumps({"error": f"file not found: {args.csv_path}"}))
        return 1
    except ValueError as exc:
        # Header errors, malformed CSV
        print(json.dumps({"error": str(exc)}))
        return 1
    except SQLAlchemyError as exc:
        print(json.dumps({"error": f"database error: {exc.__class__.__name__}: {exc}"}))
        return 3

    report.finished_at = datetime.utcnow().isoformat() + "Z"
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))

    if report.row_errors:
        return 2
    return 0


def _flush(
    session,
    batch: List[m.MonitoringRecord],
    dry_run: bool,
) -> Tuple[int, int]:
    """Insert one batch; return (inserted, duplicates_skipped)."""
    if dry_run:
        return 0, 0
    inserted = 0
    duplicates = 0
    for rec in batch:
        # Check for duplicate (sensor_id, timestamp) to keep import idempotent.
        existing = session.execute(
            select(m.MonitoringRecord.id)
            .where(
                m.MonitoringRecord.sensor_id == rec.sensor_id,
                m.MonitoringRecord.timestamp == rec.timestamp,
            )
            .limit(1)
        ).scalar_one_or_none()
        if existing is not None:
            duplicates += 1
            continue
        session.add(rec)
        try:
            session.flush()
            inserted += 1
        except IntegrityError:
            session.rollback()
            duplicates += 1
    return inserted, duplicates


if __name__ == "__main__":
    sys.exit(main())
