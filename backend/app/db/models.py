"""
SQLAlchemy ORM Models for BuildHealth
Phase 1 实现 · 6 张核心表

设计要点：
- 所有外键级联（删除父表记录时自动清理子表）
- 时间字段统一使用 UTC datetime
- 索引策略按 docs/04_Data_Model.md 实施
- is_simulated / quality_flag 用于明确数据来源（强制红线 ER-01）
"""
from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Date,
    Boolean,
    Text,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import relationship

from app.db.base import Base


class Building(Base):
    """建筑档案"""

    __tablename__ = "buildings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    address = Column(String(256), nullable=False)
    year_built = Column(Integer, nullable=False)  # 建造年份
    building_type = Column(String(32), nullable=False)  # residential/office/mixed/industrial
    structure_type = Column(String(32), nullable=False)  # frame/shear/wall/masonry
    floors = Column(Integer, nullable=False)
    area = Column(Float, nullable=False)  # 总面积（㎡）
    design_life = Column(Integer, nullable=False)  # 设计使用年限（年）
    current_age = Column(Integer, nullable=False)  # 当前已使用年限
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # 关系
    components = relationship(
        "Component", back_populates="building", cascade="all, delete-orphan"
    )
    sensors = relationship(
        "Sensor", back_populates="building", cascade="all, delete-orphan"
    )
    health_assessments = relationship(
        "HealthAssessment", back_populates="building", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_building_type", "building_type"),
    )


class Component(Base):
    """构件（建筑子部件）"""

    __tablename__ = "components"

    id = Column(Integer, primary_key=True, autoincrement=True)
    building_id = Column(
        Integer, ForeignKey("buildings.id", ondelete="CASCADE"), nullable=False
    )
    name = Column(String(128), nullable=False)
    component_type = Column(String(32), nullable=False)  # column/beam/wall/slab/foundation/roof
    location = Column(String(128), nullable=False)
    condition_status = Column(String(32), nullable=False, default="normal")
    description = Column(Text, nullable=True)

    # 关系
    building = relationship("Building", back_populates="components")
    sensors = relationship(
        "Sensor", back_populates="component", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_component_building", "building_id"),
    )


class Sensor(Base):
    """监测点"""

    __tablename__ = "sensors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    building_id = Column(
        Integer, ForeignKey("buildings.id", ondelete="CASCADE"), nullable=False
    )
    component_id = Column(
        Integer, ForeignKey("components.id", ondelete="SET NULL"), nullable=True
    )
    sensor_type = Column(String(32), nullable=False)  # crack_width/tilt/temperature/humidity/electricity
    name = Column(String(128), nullable=False)
    unit = Column(String(16), nullable=False)
    location = Column(String(128), nullable=False)
    status = Column(String(16), nullable=False, default="active")  # active/inactive/fault

    # 关系
    building = relationship("Building", back_populates="sensors")
    component = relationship("Component", back_populates="sensors")
    records = relationship(
        "MonitoringRecord", back_populates="sensor", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_sensor_building", "building_id"),
        Index("idx_sensor_component", "component_id"),
        Index("idx_sensor_type", "sensor_type"),
    )


class MonitoringRecord(Base):
    """监测记录（append-only · 严格不更新）"""

    __tablename__ = "monitoring_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sensor_id = Column(
        Integer, ForeignKey("sensors.id", ondelete="CASCADE"), nullable=False
    )
    timestamp = Column(DateTime, nullable=False)
    value = Column(Float, nullable=False)
    quality_flag = Column(String(16), nullable=False, default="simulated")  # simulated/real/test
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 关系
    sensor = relationship("Sensor", back_populates="records")

    __table_args__ = (
        Index("idx_monitoring_sensor_ts", "sensor_id", "timestamp"),
        Index("idx_monitoring_timestamp", "timestamp"),
    )


class HealthAssessment(Base):
    """建筑健康评估（每次评估一条新记录，append-only）"""

    __tablename__ = "health_assessments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    building_id = Column(
        Integer, ForeignKey("buildings.id", ondelete="CASCADE"), nullable=False
    )
    score = Column(Float, nullable=False)  # BHI 0-100
    structural_safety = Column(Float, nullable=False)
    facility_condition = Column(Float, nullable=False)
    environmental_quality = Column(Float, nullable=False)
    energy_performance = Column(Float, nullable=False)
    fire_safety = Column(Float, nullable=False)
    calculation_version = Column(String(32), nullable=False)  # e.g. "BHI-v1.0"
    explanation = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 关系
    building = relationship("Building", back_populates="health_assessments")

    __table_args__ = (
        Index("idx_health_building_date", "building_id", "created_at"),
    )


class RiskAlert(Base):
    """风险预警（与异常检测结果对应）"""

    __tablename__ = "risk_alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    building_id = Column(
        Integer, ForeignKey("buildings.id", ondelete="CASCADE"), nullable=False
    )
    sensor_id = Column(
        Integer, ForeignKey("sensors.id", ondelete="SET NULL"), nullable=True
    )
    metric = Column(String(32), nullable=False)  # sensor_type 的副本（便于聚合查询）
    timestamp = Column(DateTime, nullable=False)
    current_value = Column(Float, nullable=False)
    baseline_value = Column(Float, nullable=True)
    change = Column(Float, nullable=True)  # current - baseline
    detection_method = Column(String(32), nullable=False)  # threshold/rate_of_change/zscore
    severity = Column(String(16), nullable=False)  # low/medium/high
    explanation = Column(Text, nullable=True)
    status = Column(String(16), nullable=False, default="active")  # active/resolved/superseded
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_risk_building", "building_id"),
        Index("idx_risk_status", "status"),
        Index("idx_risk_severity", "severity"),
        Index("idx_risk_timestamp", "timestamp"),
    )
