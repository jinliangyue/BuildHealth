"""
CSV import · import_csv.py
==========================
Phase 7 tests. Covers happy path, all per-row validation failures,
idempotency, dry-run, anomaly re-detection trigger, exit codes, and
header-level errors.

Each test gets a fresh in-memory SQLite (per conftest.test_engine)
and a minimal seed: 1 building, 2 components, 2 sensors.
"""
import csv
import json
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.db import models as m
from scripts import import_csv


# --------------------------------------------------------------------- fixtures
@pytest.fixture
def import_session_factory(test_engine):
    """Session factory bound to the in-memory test engine.

    `expire_on_commit=False` keeps attribute access cheap after commit
    (no DetachedInstanceError on b.id lookups during the test body).

    import_csv.main() is invoked with `session_factory=` so it writes
    into the same engine that conftest.test_session is bound to.
    """
    return sessionmaker(bind=test_engine, expire_on_commit=False)


@pytest.fixture
def seeded(import_session_factory):
    """One building, two sensors (crack_width + tilt) ready to receive data.

    Writes through the same factory the import script uses, and keeps
    the seeding session open across the test so returned ORM objects
    remain attached (id lookups, relationship walks, etc.).
    """
    s = import_session_factory()
    try:
        b = m.Building(
            name="Import Test Building",
            address="test addr",
            year_built=2010,
            building_type="office",
            structure_type="frame",
            floors=10,
            area=5000.0,
            design_life=50,
            current_age=15,
        )
        s.add(b)
        s.flush()
        c1 = m.Component(building_id=b.id, name="C1", component_type="column", location="loc")
        c2 = m.Component(building_id=b.id, name="C2", component_type="beam", location="loc")
        s.add(c1); s.add(c2); s.flush()
        s1 = m.Sensor(
            building_id=b.id, component_id=c1.id, sensor_type="crack_width",
            name="crack_sensor", unit="mm", location="loc", status="active",
        )
        s2 = m.Sensor(
            building_id=b.id, component_id=c2.id, sensor_type="tilt",
            name="tilt_sensor", unit="‰", location="loc", status="active",
        )
        s.add(s1); s.add(s2); s.flush()
        s.commit()
        yield {"building": b, "sensors": [s1, s2]}
    finally:
        s.close()


def _write_csv(tmp_path: Path, name: str, header, rows) -> Path:
    p = tmp_path / name
    with p.open("w", encoding="utf-8", newline="") as fp:
        w = csv.writer(fp)
        w.writerow(header)
        for r in rows:
            w.writerow(r)
    return p


def _run_import(csv_path, *, import_session_factory, dry_run=False, run_anomaly=False):
    argv = [str(csv_path)]
    if dry_run:
        argv.append("--dry-run")
    if run_anomaly:
        argv.append("--run-anomaly")
    return import_csv.main(argv, session_factory=import_session_factory)


def _parse_last_report(capsys) -> dict:
    """import_csv prints one or more JSON objects; return the final one."""
    out = capsys.readouterr().out
    blocks = [blk for blk in out.strip().split("\n\n") if blk.startswith("{")]
    assert blocks, f"no JSON report on stdout:\n{out}"
    return json.loads(blocks[-1])


# --------------------------------------------------------------------- happy path
def test_happy_path_imports_rows(tmp_path, test_session, seeded, import_session_factory, capsys):
    b = seeded["building"]
    s1, s2 = seeded["sensors"]

    rows = [
        (b.id, s1.id, 0.15, "2026-09-01T00:00:00", "simulated"),
        (b.id, s1.id, 0.18, "2026-09-02T00:00:00", "simulated"),
        (b.id, s2.id, 2.1,  "2026-09-01T00:00:00", "simulated"),
    ]
    csv_path = _write_csv(tmp_path, "ok.csv",
                          ["building_id", "sensor_id", "value", "recorded_at", "quality_flag"],
                          rows)

    rc = _run_import(csv_path, import_session_factory=import_session_factory)
    assert rc == 0

    report = _parse_last_report(capsys)
    assert report["total_rows"] == 3
    assert report["inserted"] == 3
    assert report["row_errors"] == []
    assert sorted(report["sensors_touched"]) == sorted([s1.id, s2.id])

    # And the rows actually landed in the DB
    stored = test_session.execute(select(m.MonitoringRecord)).scalars().all()
    assert len(stored) == 3
    assert {r.sensor_id for r in stored} == {s1.id, s2.id}


def test_happy_path_real_quality_flag_accepted(tmp_path, test_session, seeded, import_session_factory):
    b = seeded["building"]
    s1, _ = seeded["sensors"]
    csv_path = _write_csv(
        tmp_path, "ok_real.csv",
        ["building_id", "sensor_id", "value", "recorded_at", "quality_flag"],
        [(b.id, s1.id, 0.20, "2026-09-01T00:00:00", "real")],
    )
    rc = _run_import(csv_path, import_session_factory=import_session_factory)
    assert rc == 0
    stored = test_session.execute(select(m.MonitoringRecord)).scalars().all()
    assert len(stored) == 1
    assert stored[0].quality_flag == "real"


# --------------------------------------------------------------------- validation failures
def test_missing_required_header_column(tmp_path, seeded, import_session_factory):
    b = seeded["building"]
    s1, _ = seeded["sensors"]
    csv_path = _write_csv(
        tmp_path, "bad_header.csv",
        # missing quality_flag
        ["building_id", "sensor_id", "value", "recorded_at"],
        [(b.id, s1.id, 0.15, "2026-09-01T00:00:00")],
    )
    rc = _run_import(csv_path, import_session_factory=import_session_factory)
    assert rc == 1


def test_unknown_sensor_id_rejected(tmp_path, test_session, seeded, import_session_factory):
    b = seeded["building"]
    s1, _ = seeded["sensors"]
    csv_path = _write_csv(
        tmp_path, "unknown_sensor.csv",
        ["building_id", "sensor_id", "value", "recorded_at", "quality_flag"],
        [
            (b.id, s1.id, 0.15, "2026-09-01T00:00:00", "simulated"),
            (b.id, 99999, 0.20, "2026-09-02T00:00:00", "simulated"),
        ],
    )
    rc = _run_import(csv_path, import_session_factory=import_session_factory)
    assert rc == 2
    stored = test_session.execute(select(m.MonitoringRecord)).scalars().all()
    assert len(stored) == 1
    assert stored[0].sensor_id == s1.id


def test_sensor_wrong_building_rejected(tmp_path, test_session, seeded, import_session_factory):
    b = seeded["building"]
    s1, _ = seeded["sensors"]
    csv_path = _write_csv(
        tmp_path, "wrong_building.csv",
        ["building_id", "sensor_id", "value", "recorded_at", "quality_flag"],
        [(b.id + 999, s1.id, 0.15, "2026-09-01T00:00:00", "simulated")],
    )
    rc = _run_import(csv_path, import_session_factory=import_session_factory)
    assert rc == 2
    assert test_session.execute(select(m.MonitoringRecord)).scalars().all() == []


def test_invalid_value_rejected(tmp_path, test_session, seeded, import_session_factory):
    b = seeded["building"]
    s1, _ = seeded["sensors"]
    csv_path = _write_csv(
        tmp_path, "bad_value.csv",
        ["building_id", "sensor_id", "value", "recorded_at", "quality_flag"],
        [(b.id, s1.id, "not-a-number", "2026-09-01T00:00:00", "simulated")],
    )
    rc = _run_import(csv_path, import_session_factory=import_session_factory)
    assert rc == 2
    assert test_session.execute(select(m.MonitoringRecord)).scalars().all() == []


def test_invalid_timestamp_rejected(tmp_path, test_session, seeded, import_session_factory):
    b = seeded["building"]
    s1, _ = seeded["sensors"]
    csv_path = _write_csv(
        tmp_path, "bad_ts.csv",
        ["building_id", "sensor_id", "value", "recorded_at", "quality_flag"],
        [(b.id, s1.id, 0.15, "2026/09/01", "simulated")],
    )
    rc = _run_import(csv_path, import_session_factory=import_session_factory)
    assert rc == 2
    assert test_session.execute(select(m.MonitoringRecord)).scalars().all() == []


def test_invalid_quality_flag_rejected(tmp_path, test_session, seeded, import_session_factory):
    b = seeded["building"]
    s1, _ = seeded["sensors"]
    csv_path = _write_csv(
        tmp_path, "bad_qf.csv",
        ["building_id", "sensor_id", "value", "recorded_at", "quality_flag"],
        [(b.id, s1.id, 0.15, "2026-09-01T00:00:00", "raw")],
    )
    rc = _run_import(csv_path, import_session_factory=import_session_factory)
    assert rc == 2
    assert test_session.execute(select(m.MonitoringRecord)).scalars().all() == []


def test_comment_lines_are_ignored(tmp_path, test_session, seeded, import_session_factory):
    """Header is the *first* line of the file; comment lines only appear
    in the data section. csv.DictReader treats the first non-empty line
    as fieldnames, so we put the header first, then sprinkle comments
    and blanks between data rows."""
    b = seeded["building"]
    s1, _ = seeded["sensors"]
    csv_path = tmp_path / "with_comments.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as fp:
        w = csv.writer(fp)
        w.writerow(["building_id", "sensor_id", "value", "recorded_at", "quality_flag"])
        fp.write("# row-level comment, should be skipped\n")
        w.writerow([b.id, s1.id, 0.15, "2026-09-01T00:00:00", "simulated"])
        fp.write("\n")  # blank line
        w.writerow([b.id, s1.id, 0.20, "2026-09-02T00:00:00", "simulated"])
    rc = _run_import(csv_path, import_session_factory=import_session_factory)
    assert rc == 0
    stored = test_session.execute(select(m.MonitoringRecord)).scalars().all()
    assert len(stored) == 2


# --------------------------------------------------------------------- idempotency
def test_import_is_idempotent_on_repeat(tmp_path, test_session, seeded, import_session_factory, capsys):
    b = seeded["building"]
    s1, _ = seeded["sensors"]
    rows = [
        (b.id, s1.id, 0.15, "2026-09-01T00:00:00", "simulated"),
        (b.id, s1.id, 0.18, "2026-09-02T00:00:00", "simulated"),
    ]
    csv_path = _write_csv(
        tmp_path, "idem.csv",
        ["building_id", "sensor_id", "value", "recorded_at", "quality_flag"],
        rows,
    )
    rc1 = _run_import(csv_path, import_session_factory=import_session_factory)
    assert rc1 == 0
    capsys.readouterr()  # discard first report
    rc2 = _run_import(csv_path, import_session_factory=import_session_factory)
    assert rc2 == 0  # duplicates are skipped, not errors

    stored = test_session.execute(select(m.MonitoringRecord)).scalars().all()
    assert len(stored) == 2  # not four
    report2 = _parse_last_report(capsys)
    assert report2["inserted"] == 0
    assert report2["skipped_duplicates"] == 2


# --------------------------------------------------------------------- dry run
def test_dry_run_writes_nothing(tmp_path, test_session, seeded, import_session_factory):
    b = seeded["building"]
    s1, _ = seeded["sensors"]
    csv_path = _write_csv(
        tmp_path, "dryrun.csv",
        ["building_id", "sensor_id", "value", "recorded_at", "quality_flag"],
        [(b.id, s1.id, 0.15, "2026-09-01T00:00:00", "simulated")],
    )
    rc = _run_import(csv_path, import_session_factory=import_session_factory, dry_run=True)
    assert rc == 0
    assert test_session.execute(select(m.MonitoringRecord)).scalars().all() == []


# --------------------------------------------------------------------- anomaly trigger
def test_run_anomaly_creates_risk_alerts(tmp_path, test_session, seeded, import_session_factory):
    b = seeded["building"]
    s1, _ = seeded["sensors"]
    rows = [
        (b.id, s1.id, 0.10, "2026-09-01T00:00:00", "simulated"),
        (b.id, s1.id, 0.12, "2026-09-02T00:00:00", "simulated"),
        (b.id, s1.id, 0.15, "2026-09-03T00:00:00", "simulated"),
        (b.id, s1.id, 0.18, "2026-09-04T00:00:00", "simulated"),
        (b.id, s1.id, 0.45, "2026-09-05T00:00:00", "simulated"),  # > 0.30 mm threshold
    ]
    csv_path = _write_csv(
        tmp_path, "anomaly.csv",
        ["building_id", "sensor_id", "value", "recorded_at", "quality_flag"],
        rows,
    )
    rc = _run_import(csv_path, import_session_factory=import_session_factory, run_anomaly=True)
    assert rc == 0
    alerts = test_session.execute(select(m.RiskAlert)).scalars().all()
    assert len(alerts) >= 1
    assert {a.sensor_id for a in alerts} == {s1.id}


# --------------------------------------------------------------------- exit code
def test_missing_file_returns_1(tmp_path, import_session_factory):
    rc = _run_import(tmp_path / "does-not-exist.csv", import_session_factory=import_session_factory)
    assert rc == 1
