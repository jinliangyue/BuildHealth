# 04 · 数据模型（Data Model）

## 1. ER 图

```
┌─────────────────────┐
│      Building       │
│─────────────────────│
│ id (PK)             │
│ name                │
│ address             │
│ city                │
│ building_type       │
│ built_year          │
│ total_floors        │
│ created_at          │
│ updated_at          │
└──────────┬──────────┘
           │ 1
           │
           │ N
┌──────────┴──────────┐         ┌─────────────────────┐
│     Component       │         │      Sensor         │
│─────────────────────│         │─────────────────────│
│ id (PK)             │  1   N  │ id (PK)             │
│ building_id (FK)    ├────────►│ component_id (FK)   │
│ name                │         │ metric              │
│ component_type      │         │ unit                │
│ location            │         │ install_date        │
│ created_at          │         │ is_active           │
└─────────────────────┘         └──────────┬──────────┘
                                           │ 1
                                           │
                                           │ N
┌──────────────────────────────────────────┴──────────┐
│               MonitoringRecord                       │
│─────────────────────────────────────────────────────│
│ id (PK)                                             │
│ sensor_id (FK)                                      │
│ ts (datetime, indexed)                              │
│ value (float)                                       │
│ is_simulated (bool, default=True)                   │
│ created_at                                          │
└─────────────────────────────────────────────────────┘
                                           │
                                           │ (computed)
                                           ▼
┌─────────────────────────────────────────────────────┐
│              HealthAssessment                       │
│─────────────────────────────────────────────────────│
│ id (PK)                                             │
│ building_id (FK)                                    │
│ assessment_date (date)                              │
│ structural_safety (0-100)                           │
│ facility_condition (0-100)                          │
│ environmental_quality (0-100)                       │
│ energy_performance (0-100)                          │
│ fire_safety (0-100)                                 │
│ bhi (0-100, computed)                               │
│ bhi_version (string, e.g. "v0.1")                   │
│ created_at                                          │
└─────────────────────────────────────────────────────┘
                                           │
                                           │ (computed)
                                           ▼
┌─────────────────────────────────────────────────────┐
│                  RiskAlert                          │
│─────────────────────────────────────────────────────│
│ id (PK)                                             │
│ building_id (FK)                                    │
│ alert_date (date)                                   │
│ risk_level (Normal/Attention/Abnormal/HighRisk)     │
│ bhi_at_alert (0-100)                                │
│ top_reason (string)                                 │
│ is_active (bool)                                    │
│ created_at                                          │
└─────────────────────────────────────────────────────┘
```

## 2. 表结构详解

### 2.1 Building（建筑档案）

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | INTEGER | PK | 自增 |
| name | TEXT | NOT NULL | 建筑名称（如"Building A-1"） |
| address | TEXT | NOT NULL | 地址（虚构） |
| city | TEXT | NOT NULL | 城市（虚构） |
| building_type | TEXT | NOT NULL | 类型：residential / office / mixed / industrial |
| built_year | INTEGER | NOT NULL | 建造年份 |
| total_floors | INTEGER | NOT NULL | 总层数 |
| created_at | DATETIME | DEFAULT now | 创建时间 |
| updated_at | DATETIME | ON UPDATE now | 更新时间 |

**索引**：`idx_building_city`、`idx_building_type`

### 2.2 Component（构件）

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | INTEGER | PK | 自增 |
| building_id | INTEGER | FK → Building.id | 所属建筑 |
| name | TEXT | NOT NULL | 构件名称（如"北立面承重墙"） |
| component_type | TEXT | NOT NULL | 类型：column / beam / wall / slab / foundation / roof |
| location | TEXT | NOT NULL | 位置描述（如"F3 北侧"） |
| created_at | DATETIME | DEFAULT now | |

**索引**：`idx_component_building`

### 2.3 Sensor（监测点）

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | INTEGER | PK | 自增 |
| component_id | INTEGER | FK → Component.id | 所属构件 |
| metric | TEXT | NOT NULL | 指标：crack_width / tilt / temperature / humidity / electricity |
| unit | TEXT | NOT NULL | 单位：mm / ‰ / ℃ / % / kWh |
| install_date | DATE | NOT NULL | 安装日期 |
| is_active | BOOLEAN | DEFAULT True | 是否启用 |
| created_at | DATETIME | DEFAULT now | |

**索引**：`idx_sensor_component`、`idx_sensor_metric`

### 2.4 MonitoringRecord（监测记录）

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | INTEGER | PK | 自增 |
| sensor_id | INTEGER | FK → Sensor.id | 所属传感器 |
| ts | DATETIME | NOT NULL | 时间戳（UTC） |
| value | FLOAT | NOT NULL | 数值 |
| is_simulated | BOOLEAN | DEFAULT True | **必为 True（V1 全部模拟）** |
| created_at | DATETIME | DEFAULT now | |

**索引**：`idx_monitoring_sensor_ts (sensor_id, ts)`

### 2.5 HealthAssessment（健康评估）

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | INTEGER | PK | 自增 |
| building_id | INTEGER | FK → Building.id | 所属建筑 |
| assessment_date | DATE | NOT NULL | 评估日期 |
| structural_safety | FLOAT | 0-100 | 维度 1 |
| facility_condition | FLOAT | 0-100 | 维度 2 |
| environmental_quality | FLOAT | 0-100 | 维度 3 |
| energy_performance | FLOAT | 0-100 | 维度 4 |
| fire_safety | FLOAT | 0-100 | 维度 5 |
| bhi | FLOAT | 0-100 | **加权综合分（计算字段）** |
| bhi_version | TEXT | NOT NULL | 公式版本号（如 "v0.1"） |
| created_at | DATETIME | DEFAULT now | |

**索引**：`idx_health_building_date`

### 2.6 RiskAlert（风险预警）

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | INTEGER | PK | 自增 |
| building_id | INTEGER | FK → Building.id | 所属建筑 |
| alert_date | DATE | NOT NULL | 预警日期 |
| risk_level | TEXT | NOT NULL | Normal / Attention / Abnormal / HighRisk |
| bhi_at_alert | FLOAT | 0-100 | 触发时的 BHI |
| top_reason | TEXT | | 主要风险原因（来自异常检测） |
| is_active | BOOLEAN | DEFAULT True | 当前是否生效 |
| created_at | DATETIME | DEFAULT now | |

**索引**：`idx_risk_building`、`idx_risk_active`

## 3. 关系图（级联与约束）

### 3.1 Building → Component

- 一对多（1:N）
- 删除 Building → 级联删除 Component（设计阶段）
- V1 默认不开放删除接口（数据完整性优先）

### 3.2 Component → Sensor

- 一对多（1:N）
- 同上

### 3.3 Sensor → MonitoringRecord

- 一对多（1:N）
- 监测数据只插入不更新（append-only）
- 单 Sensor 在 90 天 × 24h = 2160 条记录量级

### 3.4 Building → HealthAssessment

- 一对多（1:N）
- 每次评估生成一条新记录（不覆盖历史）

### 3.5 Building → RiskAlert

- 一对多（1:N）
- 每次风险等级变化生成一条新记录

## 4. 数据生命周期

```
Building (创建一次)
  → Component (创建 N 个)
    → Sensor (创建 N 个)
      → MonitoringRecord (持续写入 90 天)
        → Analytics Engine
          → HealthAssessment (写入 + 计算 bhi)
            → RiskAlert (写入 + 判定风险)
```

## 5. 种子数据（V1）

模拟数据生成器一次性产出：

- 3 栋建筑（Healthy / Attention / Abnormal）
- 每栋 5 个构件
- 每构件 2-3 个传感器
- 每传感器 90 天 × 每天 24 条 = 2160 条记录
- 每建筑 1 条 HealthAssessment（最新）
- 每建筑 1 条 RiskAlert（最新）

总计约：

- 3 × 5 × 2.5 × 2160 ≈ 81,000 条 MonitoringRecord
- 3 条 HealthAssessment
- 3 条 RiskAlert

## 6. SQLAlchemy 模型示例（设计稿）

```python
# backend/app/db/models.py
from sqlalchemy import Column, Integer, String, Float, DateTime, Date, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base

class Building(Base):
    __tablename__ = "buildings"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    address = Column(String, nullable=False)
    city = Column(String, nullable=False)
    building_type = Column(String, nullable=False)
    built_year = Column(Integer, nullable=False)
    total_floors = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    components = relationship("Component", back_populates="building", cascade="all, delete-orphan")

class Component(Base):
    __tablename__ = "components"
    id = Column(Integer, primary_key=True)
    building_id = Column(Integer, ForeignKey("buildings.id"), nullable=False)
    name = Column(String, nullable=False)
    component_type = Column(String, nullable=False)
    location = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    building = relationship("Building", back_populates="components")
    sensors = relationship("Sensor", back_populates="component", cascade="all, delete-orphan")

class Sensor(Base):
    __tablename__ = "sensors"
    id = Column(Integer, primary_key=True)
    component_id = Column(Integer, ForeignKey("components.id"), nullable=False)
    metric = Column(String, nullable=False)
    unit = Column(String, nullable=False)
    install_date = Column(Date, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    component = relationship("Component", back_populates="sensors")
    records = relationship("MonitoringRecord", back_populates="sensor", cascade="all, delete-orphan")

class MonitoringRecord(Base):
    __tablename__ = "monitoring_records"
    id = Column(Integer, primary_key=True)
    sensor_id = Column(Integer, ForeignKey("sensors.id"), nullable=False)
    ts = Column(DateTime, nullable=False)
    value = Column(Float, nullable=False)
    is_simulated = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    sensor = relationship("Sensor", back_populates="records")

    __table_args__ = (Index("idx_monitoring_sensor_ts", "sensor_id", "ts"),)

class HealthAssessment(Base):
    __tablename__ = "health_assessments"
    id = Column(Integer, primary_key=True)
    building_id = Column(Integer, ForeignKey("buildings.id"), nullable=False)
    assessment_date = Column(Date, nullable=False)
    structural_safety = Column(Float, nullable=False)
    facility_condition = Column(Float, nullable=False)
    environmental_quality = Column(Float, nullable=False)
    energy_performance = Column(Float, nullable=False)
    fire_safety = Column(Float, nullable=False)
    bhi = Column(Float, nullable=False)
    bhi_version = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (Index("idx_health_building_date", "building_id", "assessment_date"),)

class RiskAlert(Base):
    __tablename__ = "risk_alerts"
    id = Column(Integer, primary_key=True)
    building_id = Column(Integer, ForeignKey("buildings.id"), nullable=False)
    alert_date = Column(Date, nullable=False)
    risk_level = Column(String, nullable=False)
    bhi_at_alert = Column(Float, nullable=False)
    top_reason = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

## 7. 当前状态

**Phase 0** — 数据模型设计完成

- ✅ 6 张表结构已设计
- ✅ 索引策略已规划
- ✅ 关系与级联已说明
- ⏳ SQLAlchemy 模型未实际创建（仅本文档示例代码）
- ⏳ 数据库未实际生成

---

**文档版本**：v0.1 · Phase 0 起草
**最后更新**：2026-09-15
**状态**：Designed but not implemented
