"""
Database Layer 测试 · 初始化 / 关系 / 基础 CRUD
"""
import pytest
from datetime import datetime

from app.db.base import Base
from app.db import models as m


def test_all_tables_created(test_engine):
    """所有 6 张表被创建"""
    inspector_tables = set(Base.metadata.tables.keys())
    expected = {
        "buildings", "components", "sensors",
        "monitoring_records", "health_assessments", "risk_alerts",
    }
    assert expected.issubset(inspector_tables)


def test_init_db_creates_every_declared_table(test_engine):
    """Regression guard: every table declared on ``Base.metadata`` must
    actually exist on a freshly-created engine.

    Why this lives in ``test_database.py`` next to ``test_all_tables_created``
    instead of in ``test_audit.py``:

    * It is a schema-completeness invariant, not an audit feature test.
    * The 4c215de-AuditLog-bug class of regression ("model added but table
      missing on the live DB") can only be caught by comparing the
      declared set against reality. ``test_all_tables_created`` only
      checks the 6 Phase-1 tables; this test covers the full 9-table
      current declaration so a missing model import in ``app/db/models.py``
      or a typo in a ``__tablename__`` fails CI immediately.
    """
    from sqlalchemy import inspect
    declared = set(Base.metadata.tables.keys())
    real = set(inspect(test_engine).get_table_names())
    missing = declared - real
    assert not missing, (
        f"Declared tables missing from DB after create_all: {sorted(missing)}. "
        f"Hint: a new model class was added in app/db/models.py but not "
        f"imported (the import is what registers it on Base.metadata). "
        f"Adding the missing import fixes the failure."
    )
    # Symmetry: nothing lurking in the DB that isn't declared.
    assert real == declared, (
        f"DB contains tables not declared on Base.metadata: "
        f"{sorted(real - declared)}. Check that create_all + drop_all "
        f"in the test_engine fixture are still symmetric."
    )


def test_building_crud(test_session):
    b = m.Building(
        name="X", address="Y", year_built=2000, building_type="office",
        structure_type="frame", floors=5, area=1000.0,
        design_life=50, current_age=26,
    )
    test_session.add(b)
    test_session.commit()
    assert b.id is not None

    found = test_session.get(m.Building, b.id)
    assert found.name == "X"
    assert found.created_at is not None


def test_building_component_relationship(test_session):
    b = m.Building(
        name="X", address="Y", year_built=2000, building_type="office",
        structure_type="frame", floors=5, area=1000.0,
        design_life=50, current_age=26,
    )
    test_session.add(b)
    test_session.flush()

    c = m.Component(
        building_id=b.id, name="col1", component_type="column",
        location="F1", condition_status="normal",
    )
    test_session.add(c)
    test_session.commit()

    assert len(b.components) == 1
    assert b.components[0].name == "col1"
    assert c.building.name == "X"


def test_sensor_component_relationship(test_session):
    b = m.Building(
        name="X", address="Y", year_built=2000, building_type="office",
        structure_type="frame", floors=5, area=1000.0,
        design_life=50, current_age=26,
    )
    test_session.add(b)
    test_session.flush()
    c = m.Component(
        building_id=b.id, name="col1", component_type="column",
        location="F1", condition_status="normal",
    )
    test_session.add(c)
    test_session.flush()

    s = m.Sensor(
        building_id=b.id, component_id=c.id, sensor_type="crack_width",
        name="s1", unit="mm", location="F1", status="active",
    )
    test_session.add(s)
    test_session.commit()

    assert c.sensors[0].id == s.id
    assert s.component.name == "col1"


def test_monitoring_record_relationship(test_session):
    b = m.Building(
        name="X", address="Y", year_built=2000, building_type="office",
        structure_type="frame", floors=5, area=1000.0,
        design_life=50, current_age=26,
    )
    test_session.add(b)
    test_session.flush()
    s = m.Sensor(
        building_id=b.id, sensor_type="crack_width", name="s1",
        unit="mm", location="F1", status="active",
    )
    test_session.add(s)
    test_session.flush()

    for i in range(5):
        test_session.add(m.MonitoringRecord(
            sensor_id=s.id, timestamp=datetime.utcnow(), value=0.1 + i*0.01,
            quality_flag="simulated",
        ))
    test_session.commit()

    assert len(s.records) == 5


def test_health_assessment_fields(test_session):
    b = m.Building(
        name="X", address="Y", year_built=2000, building_type="office",
        structure_type="frame", floors=5, area=1000.0,
        design_life=50, current_age=26,
    )
    test_session.add(b)
    test_session.flush()

    h = m.HealthAssessment(
        building_id=b.id, score=85.5,
        structural_safety=90, facility_condition=80,
        environmental_quality=85, energy_performance=88, fire_safety=82,
        calculation_version="BHI-v1.0",
        explanation="test",
    )
    test_session.add(h)
    test_session.commit()

    assert h.id is not None
    assert h.calculation_version == "BHI-v1.0"


def test_risk_alert_fields(test_session):
    b = m.Building(
        name="X", address="Y", year_built=2000, building_type="office",
        structure_type="frame", floors=5, area=1000.0,
        design_life=50, current_age=26,
    )
    test_session.add(b)
    test_session.flush()
    s = m.Sensor(
        building_id=b.id, sensor_type="crack_width", name="s1",
        unit="mm", location="F1", status="active",
    )
    test_session.add(s)
    test_session.flush()

    a = m.RiskAlert(
        building_id=b.id, sensor_id=s.id, metric="crack_width",
        timestamp=datetime.utcnow(), current_value=0.5,
        baseline_value=0.3, change=0.2, detection_method="threshold",
        severity="high", explanation="test", status="active",
    )
    test_session.add(a)
    test_session.commit()

    assert a.id is not None
    assert a.severity == "high"
    assert a.status == "active"


def test_cascade_delete_component(test_session):
    b = m.Building(
        name="X", address="Y", year_built=2000, building_type="office",
        structure_type="frame", floors=5, area=1000.0,
        design_life=50, current_age=26,
    )
    test_session.add(b)
    test_session.flush()
    c = m.Component(
        building_id=b.id, name="col1", component_type="column",
        location="F1", condition_status="normal",
    )
    test_session.add(c)
    test_session.flush()
    s = m.Sensor(
        building_id=b.id, component_id=c.id, sensor_type="crack_width",
        name="s1", unit="mm", location="F1", status="active",
    )
    test_session.add(s)
    test_session.commit()

    building_id = b.id
    sensor_id = s.id
    test_session.delete(b)
    test_session.commit()

    # 级联删除
    assert test_session.get(m.Sensor, sensor_id) is None
    assert test_session.query(m.Component).filter_by(building_id=building_id).count() == 0
