"""
Audit query endpoints · BuildHealth Phase 7
============================================

Two read-only endpoints:

  - GET /api/audit          paginated list of audit rows, newest first
  - GET /api/audit/stats    aggregate counts over a recent window

Both endpoints are intentionally cheap: a single indexed query each.
There is no write endpoint — audit rows are append-only and managed by
the middleware.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.db import models
from app.db.session import get_db
from app.audit.schemas import AuditLogEntry, AuditLogPage, AuditLogStats, PathCount

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("", response_model=AuditLogPage)
def list_audit_logs(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    method: Optional[str] = Query(None, description="Filter by HTTP method (exact match)"),
    status_min: Optional[int] = Query(None, ge=100, le=599, description="Only rows with status_code >= this"),
    db: Session = Depends(get_db),
) -> AuditLogPage:
    base = select(models.AuditLog)
    count_q = select(func.count()).select_from(models.AuditLog)
    if method:
        base = base.where(models.AuditLog.method == method.upper())
        count_q = count_q.where(models.AuditLog.method == method.upper())
    if status_min is not None:
        base = base.where(models.AuditLog.status_code >= status_min)
        count_q = count_q.where(models.AuditLog.status_code >= status_min)

    total = db.execute(count_q).scalar_one()
    rows: List[models.AuditLog] = db.execute(
        base.order_by(desc(models.AuditLog.timestamp)).limit(limit).offset(offset)
    ).scalars().all()

    return AuditLogPage(
        items=[AuditLogEntry.model_validate(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/stats", response_model=AuditLogStats)
def audit_stats(
    hours: int = Query(24, ge=1, le=168, description="Lookback window in hours (max 7 days)"),
    db: Session = Depends(get_db),
) -> AuditLogStats:
    window_end = datetime.utcnow()
    window_start = window_end - timedelta(hours=hours)

    base = select(models.AuditLog).where(models.AuditLog.timestamp >= window_start)

    total_requests = db.execute(
        select(func.count()).select_from(base.subquery())
    ).scalar_one()

    error_count = db.execute(
        select(func.count())
        .select_from(models.AuditLog)
        .where(
            models.AuditLog.timestamp >= window_start,
            models.AuditLog.status_code >= 500,
        )
    ).scalar_one()

    avg_duration = db.execute(
        select(func.avg(models.AuditLog.duration_ms))
        .where(models.AuditLog.timestamp >= window_start)
    ).scalar_one() or 0.0

    # Top paths by hit count
    path_rows = db.execute(
        select(models.AuditLog.path, func.count().label("c"))
        .where(models.AuditLog.timestamp >= window_start)
        .group_by(models.AuditLog.path)
        .order_by(desc("c"))
        .limit(10)
    ).all()

    return AuditLogStats(
        total_requests=total_requests,
        error_count=error_count,
        avg_duration_ms=round(float(avg_duration), 3),
        top_paths=[PathCount(path=p, count=int(c)) for p, c in path_rows],
        window_start=window_start,
        window_end=window_end,
    )
