"""Risk API · /api/buildings/{id}/risk"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db import models as m
from app.analytics.config import RISK_CLASSIFICATION_VERSION
from app.schemas.api import RiskAlertRead, RiskClassificationRead
from app.services import assessment as svc

router = APIRouter(prefix="/buildings", tags=["risk"])


@router.get("/{building_id}/risk", response_model=RiskClassificationRead)
def get_risk(building_id: int, db: Session = Depends(get_db)):
    """
    返回该建筑的风险等级 + main risk factors。
    实时基于 BHI + 异常数据计算，不存表。
    """
    b = db.get(m.Building, building_id)
    if b is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Building {building_id} not found",
        )

    latest = (
        db.query(m.HealthAssessment)
        .filter(m.HealthAssessment.building_id == building_id)
        .order_by(m.HealthAssessment.created_at.desc())
        .first()
    )
    if latest is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No HealthAssessment found for building {building_id}; "
                   f"call POST /api/buildings/{building_id}/health/recompute first",
        )

    anomalies = svc.run_anomaly_detection(db, building_id)
    cls = svc.classify_risk_for_building(latest.score, anomalies)

    # 取 top_reason（来自 classification explanation）
    return {
        "building_id": building_id,
        "risk_level": cls["risk_level"],
        "bhi": cls["bhi"],
        "explanation": cls["explanation"],
        "n_high": cls["n_high"],
        "n_medium": cls["n_medium"],
        "n_low": cls["n_low"],
        "calculation_version": RISK_CLASSIFICATION_VERSION,
    }


@router.get("/{building_id}/alerts", response_model=List[RiskAlertRead])
def list_alerts(
    building_id: int,
    active_only: bool = True,
    db: Session = Depends(get_db),
):
    """列出该建筑的所有 RiskAlert（默认只 active）。"""
    b = db.get(m.Building, building_id)
    if b is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Building {building_id} not found",
        )
    q = db.query(m.RiskAlert).filter(m.RiskAlert.building_id == building_id)
    if active_only:
        q = q.filter(m.RiskAlert.status == "active")
    return q.order_by(m.RiskAlert.timestamp.desc()).all()
