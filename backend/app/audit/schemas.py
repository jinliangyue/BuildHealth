"""
Audit API schemas · BuildHealth Phase 7
=======================================

Pydantic shapes returned by the audit router. All entry models use
`from_attributes=True` so they can be built directly from SQLAlchemy
ORM rows (`model_validate(orm_obj)`); the simpler `model_validate(dict)`
path still works.
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class AuditLogEntry(BaseModel):
    """A single audit row, as returned by GET /api/audit."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    timestamp: datetime
    method: str
    path: str
    query_string: Optional[str] = None
    status_code: int
    duration_ms: float
    client_ip: str
    user_agent: Optional[str] = None
    request_id: Optional[str] = None


class AuditLogPage(BaseModel):
    """Paginated audit page."""

    items: List[AuditLogEntry]
    total: int = Field(..., description="Total matching rows, ignoring limit/offset")
    limit: int
    offset: int


class AuditLogStats(BaseModel):
    """Summary statistics over a time window."""

    total_requests: int
    error_count: int = Field(..., description="5xx responses in the window")
    avg_duration_ms: float
    top_paths: List["PathCount"]
    window_start: datetime
    window_end: datetime


class PathCount(BaseModel):
    path: str
    count: int


AuditLogStats.model_rebuild()
