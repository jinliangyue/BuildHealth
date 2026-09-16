"""
Aggregate Batch Optimization · Equivalence Tests
================================================

The aggregate endpoints (dashboard summary, buildings overview, retrofit
overview) used to query per building inside a loop, and the same monitoring
series was read up to three times per building.

They now preload buildings / latest assessments / sensors / monitoring series
in a bounded number of queries and pass that data down. These tests assert the
optimization changed nothing observable:

  * batched loaders return exactly what the per-item loaders returned
  * aggregate outputs equal a per-building recomputation
  * the number of queries no longer grows with the number of buildings

If any of these fail, the optimization changed behaviour and must be reverted.
"""
from datetime import datetime, timedelta

import pytest
from sqlalchemy import event

from app.db import models as m
from app.services import assessment as A
from app.services import retrofit_service as R


# ---------------------------------------------------------------- fixtures
def _add_building(session, bid: int, n_records: int = 40):
    b = m.Building(
        id=bid,
        name=f"Equiv Building {bid}",
        address="Test",
        year_built=2000 + bid,
        building_type="office",
        structure_type="frame",
        floors=5 + bid,
        area=1000.0,
        design_life=50,
        current_age=15 + bid,
    )
    session.add(b)
    session.flush()

    # two metrics so the series map is exercised with more than one key
    for sensor_type, base in (("crack_width", 0.10), ("tilt", 1.0)):
        s = m.Sensor(
            building_id=b.id,
            sensor_type=sensor_type,
            name=f"{sensor_type}_s",
            unit="mm",
            location="loc",
            status="active",
        )
        session.add(s)
        session.flush()
        for i in range(n_records):
            session.add(
                m.MonitoringRecord(
                    sensor_id=s.id,
                    timestamp=datetime.utcnow() - timedelta(days=n_records - i),
                    value=base + i * 0.01,
                    quality_flag="simulated",
                )
            )
    session.flush()

    # one health assessment so the aggregates have a BHI to work with
    A.compute_health_assessment(
        session,
        b,
        A.run_anomaly_detection(session, b.id),
    )
    scores = A.run_anomaly_detection(session, b.id)
    health = A.compute_health_assessment(session, b, scores)
    session.add(
        m.HealthAssessment(
            building_id=b.id,
            score=health["score"],
            structural_safety=health["structural_safety"],
            facility_condition=health["facility_condition"],
            environmental_quality=health["environmental_quality"],
            energy_performance=health["energy_performance"],
            fire_safety=health["fire_safety"],
            calculation_version=health["calculation_version"],
            explanation=health["explanation"],
        )
    )
    session.flush()
    return b


@pytest.fixture
def three_buildings(test_session):
    for bid in (1, 2, 3):
        _add_building(test_session, bid)
    test_session.commit()
    return test_session


class _QueryCounter:
    """Counts SQL statements issued against an engine."""

    def __init__(self, engine):
        self.engine = engine
        self.n = 0

    def __enter__(self):
        event.listen(self.engine, "before_cursor_execute", self._on)
        return self

    def __exit__(self, *exc):
        event.remove(self.engine, "before_cursor_execute", self._on)

    def _on(self, conn, cursor, statement, parameters, context, executemany):
        self.n += 1


# ------------------------------------------------- batched loader equivalence
def test_series_map_matches_per_metric_series(three_buildings):
    s = three_buildings
    for bid in (1, 2, 3):
        series_map = A.get_building_series_map(s, bid)
        for metric in ("crack_width", "tilt"):
            assert series_map.get(metric, []) == A.get_metric_series(s, bid, metric)


def test_series_map_by_building_matches_single(three_buildings):
    s = three_buildings
    batched = A.load_series_map_by_building(s, [1, 2, 3])
    for bid in (1, 2, 3):
        assert batched[bid] == A.get_building_series_map(s, bid)


def test_sensors_by_building_matches_per_building_query(three_buildings):
    s = three_buildings
    batched = A.load_sensors_by_building(s, [1, 2, 3])
    for bid in (1, 2, 3):
        direct = (
            s.query(m.Sensor).filter(m.Sensor.building_id == bid).order_by(m.Sensor.id).all()
        )
        assert [x.id for x in batched[bid]] == [x.id for x in direct]


def test_latest_assessments_matches_per_building_query(three_buildings):
    s = three_buildings
    batched = A.get_latest_assessments(s, [1, 2, 3])
    for bid in (1, 2, 3):
        direct = (
            s.query(m.HealthAssessment)
            .filter(m.HealthAssessment.building_id == bid)
            .order_by(m.HealthAssessment.created_at.desc())
            .first()
        )
        assert batched[bid].id == direct.id
        assert batched[bid].score == direct.score


# --------------------------------------------- preloaded vs on-demand compute
def test_anomaly_detection_preloaded_equals_on_demand(three_buildings):
    s = three_buildings
    for bid in (1, 2, 3):
        on_demand = A.run_anomaly_detection(s, bid)
        preloaded = A.run_anomaly_detection(
            s,
            bid,
            sensors=A.load_sensors_by_building(s, [bid])[bid],
            series_map=A.get_building_series_map(s, bid),
        )
        assert preloaded == on_demand


def test_health_assessment_preloaded_equals_on_demand(three_buildings):
    s = three_buildings
    for bid in (1, 2, 3):
        b = s.get(m.Building, bid)
        anomalies = A.run_anomaly_detection(s, bid)
        on_demand = A.compute_health_assessment(s, b, anomalies)
        preloaded = A.compute_health_assessment(
            s, b, anomalies, series_map=A.get_building_series_map(s, bid)
        )
        assert preloaded == on_demand


def test_recent_values_equals_per_sensor_query(three_buildings):
    """The batched recent-values loader must match a per-sensor query."""
    s = three_buildings
    sensors = s.query(m.Sensor).order_by(m.Sensor.id).all()
    batched = R._get_recent_values_by_sensor(s, sensors)

    from app.services.retrofit_service import (
        RULE_RECENT_WINDOW_DAYS,
        RULE_RECENT_VALUES_LIMIT,
    )

    cutoff = datetime.utcnow() - timedelta(days=RULE_RECENT_WINDOW_DAYS)
    for sensor in sensors:
        rows = (
            s.query(m.MonitoringRecord)
            .filter(m.MonitoringRecord.sensor_id == sensor.id)
            .filter(m.MonitoringRecord.timestamp >= cutoff)
            .order_by(m.MonitoringRecord.timestamp.desc())
            .limit(RULE_RECENT_VALUES_LIMIT)
            .all()
        )
        expected = [
            {"timestamp": r.timestamp.isoformat(), "value": r.value}
            for r in reversed(rows)
        ]
        assert batched[sensor.id] == expected


# ------------------------------------------------------ aggregate equivalence
def test_buildings_overview_matches_per_building_recompute(three_buildings):
    """Overview health / risk / alert counts must equal a manual recompute."""
    s = three_buildings
    items = A.get_buildings_overview(s)

    assert len(items) == 3
    for item in items:
        b = item["building"]
        anomalies = A.run_anomaly_detection(s, b.id)
        expected_risk = A.classify_risk_for_building(
            item["health"].score, anomalies, building_id=b.id
        )
        assert item["risk"]["risk_level"] == expected_risk["risk_level"]
        assert item["risk"]["bhi"] == expected_risk["bhi"]
        assert item["risk"]["n_high"] == expected_risk["n_high"]
        assert item["active_alert_count"] == sum(
            1 for a in anomalies if a.get("severity") in ("high", "medium")
        )


def test_dashboard_summary_matches_per_building_recompute(three_buildings):
    s = three_buildings
    summary = A.get_dashboard_summary(s)

    assert summary["total_buildings"] == 3

    # average BHI equals the mean of the latest assessment per building
    scores = []
    for bid in (1, 2, 3):
        latest = A.get_latest_assessments(s, [bid])[bid]
        scores.append(latest.score)
    assert summary["average_health_score"] == round(sum(scores) / len(scores), 2)

    # ranking and distribution agree with a per-building recompute
    expected_dist = {"Normal": 0, "Attention": 0, "Abnormal": 0, "HighRisk": 0}
    expected_ranking = []
    for bid in (1, 2, 3):
        latest = A.get_latest_assessments(s, [bid])[bid]
        anomalies = A.run_anomaly_detection(s, bid)
        cls = A.classify_risk_for_building(latest.score, anomalies)
        expected_dist[cls["risk_level"]] += 1
        expected_ranking.append(
            {
                "building_id": bid,
                "name": s.get(m.Building, bid).name,
                "bhi": latest.score,
                "risk_level": cls["risk_level"],
            }
        )
    expected_ranking.sort(key=lambda x: x["bhi"])

    assert summary["risk_distribution"] == expected_dist
    assert summary["building_ranking"] == expected_ranking


def test_retrofit_overview_matches_per_building_generation(three_buildings):
    s = three_buildings
    overview = R.get_retrofit_overview(s)
    assert overview["total"] == 3
    by_id = {item["building"].id: item for item in overview["items"]}

    priority_scores = []
    for bid in (1, 2, 3):
        recs = R.generate_recommendations(s, bid)
        expected_overall = recs[0]["priority_score"] if recs else 0.0
        assert by_id[bid]["overall_priority"] == expected_overall
        assert by_id[bid]["recommendation_count"] == len(recs)
        assert by_id[bid]["high_priority_count"] == sum(
            1 for r in recs if r["priority_score"] >= 75.0
        )
        priority_scores.append(expected_overall)

    assert overview["average_priority"] == round(
        sum(priority_scores) / len(priority_scores), 2
    )


# --------------------------------------------------- query growth is bounded
def test_dashboard_query_count_does_not_grow_with_buildings(test_session, test_engine):
    """
    The whole point of the batching: query count must be flat in the number of
    buildings, not linear.
    """
    _add_building(test_session, 1)
    test_session.commit()

    with _QueryCounter(test_engine) as one:
        A.get_dashboard_summary(test_session)

    for bid in (2, 3):
        _add_building(test_session, bid)
    test_session.commit()

    with _QueryCounter(test_engine) as three:
        A.get_dashboard_summary(test_session)

    assert three.n == one.n, (
        f"query count grew from {one.n} (1 building) to {three.n} (3 buildings); "
        "the aggregate is still querying per building"
    )


def test_buildings_overview_query_count_does_not_grow(test_session, test_engine):
    _add_building(test_session, 1)
    test_session.commit()

    with _QueryCounter(test_engine) as one:
        A.get_buildings_overview(test_session)

    for bid in (2, 3):
        _add_building(test_session, bid)
    test_session.commit()

    with _QueryCounter(test_engine) as three:
        A.get_buildings_overview(test_session)

    assert three.n == one.n, (
        f"query count grew from {one.n} to {three.n}; overview is still per building"
    )
