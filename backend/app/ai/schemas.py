"""
AI Assistant Schemas · Phase 5 V3
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# ============ Response Sub-structures ============
class AIEvidenceRef(BaseModel):
    """单个 evidence 引用 - 可点击跳转到对应 API/页面."""
    source_type: str = Field(
        ...,
        description="sensor | anomaly | health | risk | retrofit_recommendation | engineering_note | building",
    )
    source_id: Optional[int] = None
    metric: Optional[str] = None
    description: str
    reference_path: Optional[str] = Field(
        default=None,
        description="可点击的相对路径, e.g. /api/buildings/1/health",
    )


class AIKeyFinding(BaseModel):
    title: str
    description: str
    severity: str = Field(..., description="info | low | medium | high")


class AIRecommendedAction(BaseModel):
    action: str
    reason: str
    urgency: str = Field(..., description="low | medium | high")


# ============ Main Response ============
class AIResponse(BaseModel):
    answer: str
    key_findings: List[AIKeyFinding] = Field(default_factory=list)
    evidence: List[AIEvidenceRef] = Field(default_factory=list)
    knowledge_evidence: List[dict] = Field(
        default_factory=list,
        description="Phase 6B RAG: list of {document, section, content, relevance_score, source, chunk_id}",
    )
    recommended_actions: List[AIRecommendedAction] = Field(default_factory=list)
    disclaimer: str
    provider: str = Field(..., description="mock | openai | anthropic | other")
    model: str
    calculation_version: str = Field(..., description="AI-v1.0")
    created_at: datetime


# ============ Health ============
class AIHealthStatus(BaseModel):
    status: str = Field(..., description="ok | provider_not_configured | provider_error")
    provider: str
    model: str
    message: str


# ============ Request ============
class AIAskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)


# ============ Engineering Context (Internal but typed) ============
class ContextBuildingInfo(BaseModel):
    building_id: int
    name: str
    address: str
    year_built: int
    current_age: int
    design_life: int
    building_type: str
    structure_type: str
    floors: int
    area: float


class ContextComponentInfo(BaseModel):
    id: int
    name: str
    component_type: str
    location: str
    condition_status: str


class ContextSensorInfo(BaseModel):
    id: int
    sensor_type: str
    name: str
    unit: str
    location: str
    status: str
    record_count: int = 0
    latest_value: Optional[float] = None
    latest_timestamp: Optional[datetime] = None


class ContextMonitoringSummary(BaseModel):
    total_records: int
    by_metric: dict
    anomaly_total: int
    anomaly_by_severity: dict
    anomaly_by_method: dict


class ContextHealthInfo(BaseModel):
    bhi: Optional[float] = None
    dimensions: Optional[dict] = None
    weakest_dimension: Optional[str] = None
    calculation_version: Optional[str] = None
    explanation: Optional[str] = None


class ContextRiskInfo(BaseModel):
    risk_level: Optional[str] = None
    explanation: Optional[str] = None
    n_high: int = 0
    n_medium: int = 0
    n_low: int = 0


class ContextRetrofitInfo(BaseModel):
    overall_priority: float
    overall_priority_level: str
    calculation_version: Optional[str] = None
    recommendation_count: int
    recommendations: list  # List of recommendation dicts
    engineering_notes: list


class EngineeringContext(BaseModel):
    building_id: int
    building: ContextBuildingInfo
    components: List[ContextComponentInfo] = Field(default_factory=list)
    sensors: List[ContextSensorInfo] = Field(default_factory=list)
    monitoring_summary: ContextMonitoringSummary
    health: ContextHealthInfo
    risk: ContextRiskInfo
    retrofit: ContextRetrofitInfo
    evidence_chain: List[AIEvidenceRef] = Field(default_factory=list)
    disclaimer: str
    generated_at: datetime
    context_version: str = Field(default="CTX-v1.0")


# ============ Phase 6B · Knowledge Evidence (RAG) ============
# AIResponse.knowledge_evidence uses a flexible Dict shape to avoid a
# hard import dependency from app.ai.schemas onto app.knowledge. The
# canonical typed model is app.knowledge.schemas.KnowledgeEvidence.


# ============ Phase 6A · Provider Errors ============
class AIProviderError(Exception):
    """
    Raised by AIProvider implementations to signal a structured failure.

    Codes:
    - "config_error"     · env config missing/invalid
    - "timeout"          · request timeout
    - "network_error"    · DNS / TCP / TLS failure
    - "auth_error"       · 401 / 403 (invalid key)
    - "rate_limit"       · 429
    - "client_error"     · 4xx (not 401/403/429)
    - "provider_error"   · 5xx or upstream unavailable
    - "malformed_response" · non-JSON or schema-invalid response
    - "safety_violation" · response contains forbidden phrases
    - "internal_error"   · unexpected internal error
    """

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[AIProvider:{code}] {message}")
