"""
Pydantic Schemas · API Request/Response Models
所有数值字段都明确标注范围 + 描述。
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


# ===================== Building =====================
class BuildingBase(BaseModel):
    name: str
    address: str
    year_built: int = Field(..., ge=1800, le=2100)
    building_type: str
    structure_type: str
    floors: int = Field(..., ge=1, le=200)
    area: float = Field(..., gt=0)
    design_life: int = Field(..., gt=0, le=200)
    current_age: int = Field(..., ge=0, le=200)
    description: Optional[str] = None


class BuildingRead(BuildingBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ===================== Component =====================
class ComponentRead(BaseModel):
    id: int
    building_id: int
    name: str
    component_type: str
    location: str
    condition_status: str
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ===================== Sensor =====================
class SensorRead(BaseModel):
    id: int
    building_id: int
    component_id: Optional[int] = None
    sensor_type: str
    name: str
    unit: str
    location: str
    status: str

    model_config = ConfigDict(from_attributes=True)


# ===================== MonitoringRecord =====================
class MonitoringRecordRead(BaseModel):
    id: int
    sensor_id: int
    timestamp: datetime
    value: float
    quality_flag: str

    model_config = ConfigDict(from_attributes=True)


# ===================== HealthAssessment =====================
class HealthAssessmentRead(BaseModel):
    id: int
    building_id: int
    score: float = Field(..., ge=0, le=100)
    structural_safety: float = Field(..., ge=0, le=100)
    facility_condition: float = Field(..., ge=0, le=100)
    environmental_quality: float = Field(..., ge=0, le=100)
    energy_performance: float = Field(..., ge=0, le=100)
    fire_safety: float = Field(..., ge=0, le=100)
    calculation_version: str
    explanation: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ===================== RiskAlert =====================
class RiskAlertRead(BaseModel):
    id: int
    building_id: int
    sensor_id: Optional[int] = None
    metric: str
    timestamp: datetime
    current_value: float
    baseline_value: Optional[float] = None
    change: Optional[float] = None
    detection_method: str
    severity: str
    explanation: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ===================== Risk Classification (computed) =====================
class RiskClassificationRead(BaseModel):
    building_id: int
    risk_level: str
    bhi: float
    explanation: str
    n_high: int
    n_medium: int
    n_low: int


# ===================== Dashboard =====================
class RiskDistribution(BaseModel):
    Normal: int = 0
    Attention: int = 0
    Abnormal: int = 0
    HighRisk: int = 0


class BuildingRankingItem(BaseModel):
    building_id: int
    name: str
    bhi: float
    risk_level: str


class DashboardSummary(BaseModel):
    total_buildings: int
    monitoring_points: int
    active_alerts: int
    average_health_score: float
    risk_distribution: RiskDistribution
    building_ranking: List[BuildingRankingItem]
    recent_alerts: List[RiskAlertRead]


# ===================== API Error =====================
class APIError(BaseModel):
    detail: str
