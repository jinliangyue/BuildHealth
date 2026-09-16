"""
Pydantic Schemas · API Request/Response Models
所有数值字段都明确标注范围 + 描述。
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
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
    # Prototype Risk Classification version (RISK-v1.0). Additive field:
    # the tier is a prototype parameter set, so it carries its version like
    # BHI / RP / REC / AI already do.
    calculation_version: str = "RISK-v1.0"


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


# ===================== Buildings Overview (Batch) =====================
class BuildingOverviewItem(BaseModel):
    building: BuildingRead
    health: Optional[HealthAssessmentRead] = None
    risk: Optional[RiskClassificationRead] = None
    active_alert_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class BuildingsOverviewResponse(BaseModel):
    total: int
    items: List[BuildingOverviewItem]


# ===================== Retrofit Decision (V2) =====================
class RetrofitPriorityLevelEnum(str, Enum):
    Low = "Low"
    Medium = "Medium"
    High = "High"
    VeryHigh = "Very High"


class RetrofitEvidenceSensor(BaseModel):
    sensor_id: int
    metric: str
    name: str
    unit: str
    location: str
    recent_values: List[Dict[str, Any]] = Field(default_factory=list)
    anomaly_count_by_severity: Dict[str, int] = Field(default_factory=dict)


class RetrofitEvidenceContext(BaseModel):
    sensors: List[RetrofitEvidenceSensor] = Field(default_factory=list)
    anomalies: List[Dict[str, Any]] = Field(default_factory=list)
    bhi_context: Optional[Dict[str, Any]] = None
    risk_context: Optional[Dict[str, Any]] = None
    anomaly_summary: Optional[Dict[str, int]] = None


class PriorityScoreBreakdownRead(BaseModel):
    risk_severity: float = Field(..., ge=0, le=100)
    risk_severity_contribution: float
    trend: float = Field(..., ge=0, le=100)
    trend_contribution: float
    component_importance: float = Field(..., ge=0, le=100)
    component_importance_contribution: float
    urgency: float = Field(..., ge=0, le=100)
    urgency_contribution: float
    cost_efficiency: float = Field(..., ge=0, le=100)
    cost_efficiency_contribution: float
    total: float = Field(..., ge=0, le=100)
    calculation_version: str


class RetrofitRecommendationRead(BaseModel):
    id: int
    building_id: int
    component_id: Optional[int] = None
    category: str
    issue_type: str
    title: str
    recommendation: str
    rationale: str
    next_action: str
    urgency: str
    estimated_cost_level: str
    expected_benefit: str
    source: str
    calculation_version: str
    created_at: datetime
    evidence: RetrofitEvidenceContext

    model_config = ConfigDict(from_attributes=True)


class RetrofitRecommendationDetailRead(RetrofitRecommendationRead):
    priority_score: float = Field(..., ge=0, le=100)
    priority_breakdown: PriorityScoreBreakdownRead


class EngineeringNoteRead(BaseModel):
    id: int
    building_id: int
    component_id: Optional[int] = None
    text: str
    source: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RetrofitDecisionRead(BaseModel):
    building_id: int
    building: BuildingRead
    overall_priority: float = Field(..., ge=0, le=100)
    overall_priority_level: RetrofitPriorityLevelEnum
    calculation_version: str
    recommendations: List[RetrofitRecommendationDetailRead] = Field(default_factory=list)
    engineering_notes: List[EngineeringNoteRead] = Field(default_factory=list)
    disclaimer: str


class RetrofitOverviewItem(BaseModel):
    building: BuildingRead
    overall_priority: float
    overall_priority_level: RetrofitPriorityLevelEnum
    recommendation_count: int
    high_priority_count: int
    top_category: str


class RetrofitOverviewResponse(BaseModel):
    total: int
    items: List[RetrofitOverviewItem] = Field(default_factory=list)
    average_priority: float
    calculation_version: str
    disclaimer: str


# ===================== Engineering Parameters (read-only) =====================
# Prototype configuration exposed for display. These values come from
# app/analytics/config.py; the frontend must not re-derive engineering logic
# from them — it only renders them.


class EngineeringParameterBand(BaseModel):
    level: str
    min: int
    max: int


class EngineeringDetectionThreshold(BaseModel):
    metric: str
    medium: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    unit: str
    direction: str


class EngineeringParametersResponse(BaseModel):
    """Read-only prototype parameters. Versioned via calculation_versions."""

    calculation_versions: Dict[str, str]
    bhi_weights: Dict[str, float]
    bhi_risk_bands: List[EngineeringParameterBand]
    retrofit_priority_bands: List[EngineeringParameterBand]
    retrofit_priority_weights: Dict[str, float]
    detection_thresholds: List[EngineeringDetectionThreshold]
    notice: str
