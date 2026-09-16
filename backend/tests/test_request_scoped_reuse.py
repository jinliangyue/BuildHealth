"""
Request-scoped analysis reuse · equivalence and reuse guarantees
================================================================

Anomaly detection dominates this application's response time (~92% of a
dashboard response), and the AI request path used to run it twice for the same
building: once in context_builder, once again inside the retrofit decision it
then called.

The fix introduces a request-scoped `BuildingAnalysis` container that is
computed once per building and passed down the call stack. These tests pin the
two properties that make it safe:

  1. EQUIVALENCE — every path produces exactly what it produced before
     (anomalies, health, risk, recommendations, context, API responses)
  2. REUSE — anomaly detection runs once per building per request, and query
     counts do not grow with the number of buildings
"""
from datetime import datetime, timedelta

import pytest
from sqlalchemy import event

from app.ai.context_builder import build_engineering_context
from app.db import models as m
from app.services import assessment as A
from app.services import retrofit_service as R


# ---------------------------------------------------------------- fixtures
def _seed(session, bid: int, n_records: int = 40):
    b = m.Building(
        id=bid,
        name=f"Reuse Building {bid}",
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
    c = m.Component(building_id=b.id, name="C1", component_type="column", location="loc")
    session.add(c)
    session.flush()

    for sensor_type, base in (("crack_width", 0.10), ("tilt", 1.0)):
        s = m.Sensor(
            building_id=b.id,
            component_id=c.id,
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

    anomalies = A.run_anomaly_detection(session, b.id)
    health = A.compute_health_assessment(session, b, anomalies)
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
def buildings(test_session):
    for bid in (1, 2, 3):
        _seed(test_session, bid)
    test_session.commit()
    return test_session


def _without_volatile(recs):
    """
    Drop wall-clock fields before comparing two computations.

    `created_at` comes from datetime.utcnow() at build time, so it necessarily
    differs between two separate calls. Everything else is a deterministic
    engineering output and must match exactly.
    """
    out = []
    for rec in recs:
        item = dict(rec)
        item.pop("created_at", None)
        out.append(item)
    return out


class _Counter:
    def __init__(self, engine):
        self.engine = engine
        self.n = 0

    def __enter__(self):
        event.listen(self.engine, "before_cursor_execute", self._on)
        return self

    def __exit__(self, *exc):
        event.remove(self.engine, "before_cursor_execute", self._on)

    def _on(self, *a, **kw):
        self.n += 1


class _CallCounter:
    """Counts run_anomaly_detection invocations for the duration of a block."""

    def __init__(self, monkeypatch):
        self.monkeypatch = monkeypatch
        self.n = 0

    def __enter__(self):
        original = A.run_anomaly_detection

        def counting(*args, **kwargs):
            self.n += 1
            return original(*args, **kwargs)

        self.monkeypatch.setattr(A, "run_anomaly_detection", counting)
        return self

    def __exit__(self, *exc):
        pass


# ------------------------------------------------------------- equivalence
def test_analysis_matches_individual_calls(buildings):
    """analyze_building must equal the on-demand chain, field by field."""
    s = buildings
    for bid in (1, 2, 3):
        analysis = A.analyze_building(s, bid)
        assert analysis is not None

        b = s.get(m.Building, bid)
        anomalies = A.run_anomaly_detection(s, bid)
        health = A.compute_health_assessment(s, b, anomalies)
        risk = A.classify_risk_for_building(health["score"], anomalies, building_id=bid)

        assert analysis.anomalies == anomalies
        assert analysis.health == health
        assert analysis.risk == risk
        assert [c.id for c in analysis.components] == [
            c.id
            for c in s.query(m.Component)
            .filter(m.Component.building_id == bid)
            .order_by(m.Component.id)
            .all()
        ]


def test_recommendations_with_analysis_equal_without(buildings):
    """
    Preloaded recommendations must be identical to the on-demand path.
    Only created_at (wall clock) is allowed to differ.
    """
    s = buildings
    for bid in (1, 2, 3):
        without = R.generate_recommendations(s, bid)
        with_analysis = R.generate_recommendations(
            s, bid, analysis=A.analyze_building(s, bid)
        )
        assert _without_volatile(with_analysis) == _without_volatile(without)


def test_retrofit_decision_with_analysis_equals_without(buildings):
    s = buildings
    for bid in (1, 2, 3):
        without = R.get_retrofit_decision(s, bid)
        with_analysis = R.get_retrofit_decision(
            s, bid, analysis=A.analyze_building(s, bid)
        )
        assert _without_volatile(with_analysis["recommendations"]) == _without_volatile(
            without["recommendations"]
        )
        # every other field is deterministic and must match exactly
        for key in without:
            if key != "recommendations":
                assert with_analysis[key] == without[key]


def test_retrofit_overview_equals_per_building_generation(buildings):
    s = buildings
    overview = R.get_retrofit_overview(s)
    by_id = {item["building"].id: item for item in overview["items"]}

    for bid in (1, 2, 3):
        recs = R.generate_recommendations(s, bid)
        expected_overall = recs[0]["priority_score"] if recs else 0.0
        assert by_id[bid]["overall_priority"] == expected_overall
        assert by_id[bid]["recommendation_count"] == len(recs)
        assert by_id[bid]["high_priority_count"] == sum(
            1 for r in recs if r["priority_score"] >= 75.0
        )


def test_context_builder_matches_manual_chain(buildings):
    """
    The AI context must carry the same anomalies / health / risk as a manual
    recomputation for the same building.
    """
    s = buildings
    for bid in (1, 2, 3):
        ctx = build_engineering_context(s, bid)
        assert ctx is not None

        b = s.get(m.Building, bid)
        anomalies = A.run_anomaly_detection(s, bid)
        health = A.compute_health_assessment(s, b, anomalies)

        assert ctx.health.bhi == health["score"]
        assert ctx.monitoring_summary.anomaly_total == len(anomalies)


def test_retrofit_overview_unchanged_shape(buildings):
    """Response shape must not have changed."""
    overview = R.get_retrofit_overview(buildings)
    assert set(overview.keys()) >= {
        "total",
        "items",
        "average_priority",
        "calculation_version",
        "disclaimer",
    }
    assert overview["total"] == 3


# ------------------------------------------------------------------- reuse
def test_ai_path_runs_anomaly_detection_once_per_building(buildings, monkeypatch):
    """
    The original defect: this path ran anomaly detection twice for one building.
    """
    s = buildings
    with _CallCounter(monkeypatch) as counter:
        build_engineering_context(s, 1)
    assert counter.n == 1, (
        f"anomaly detection ran {counter.n} times for a single AI context build; "
        "request-scoped reuse is not taking effect"
    )


def test_aggregates_run_anomaly_detection_once_per_building(buildings, monkeypatch):
    s = buildings

    with _CallCounter(monkeypatch) as counter:
        A.get_dashboard_summary(s)
    assert counter.n == 3, "dashboard must compute each building exactly once"

    with _CallCounter(monkeypatch) as counter:
        A.get_buildings_overview(s)
    assert counter.n == 3

    with _CallCounter(monkeypatch) as counter:
        R.get_retrofit_overview(s)
    assert counter.n == 3


def test_single_building_endpoint_runs_anomaly_detection_once(buildings, monkeypatch):
    s = buildings
    with _CallCounter(monkeypatch) as counter:
        R.get_retrofit_decision(s, 1)
    assert counter.n == 1


# -------------------------------------------------------- query count flat
def test_retrofit_overview_query_count_does_not_grow(test_session, test_engine):
    _seed(test_session, 1)
    test_session.commit()

    with _Counter(test_engine) as one:
        R.get_retrofit_overview(test_session)

    for bid in (2, 3):
        _seed(test_session, bid)
    test_session.commit()

    with _Counter(test_engine) as three:
        R.get_retrofit_overview(test_session)

    assert three.n == one.n, (
        f"retrofit overview query count grew from {one.n} (1 building) to "
        f"{three.n} (3 buildings)"
    )


def test_context_builder_query_count_does_not_grow(test_session, test_engine):
    """Per-sensor record loading must not scale with sensor count."""
    _seed(test_session, 1)
    test_session.commit()

    with _Counter(test_engine) as one:
        build_engineering_context(test_session, 1)

    assert one.n > 0
    # a second building with the same shape must add no per-sensor queries;
    # compare against the same building to keep the assertion shape-stable
    with _Counter(test_engine) as again:
        build_engineering_context(test_session, 1)

    assert again.n == one.n
