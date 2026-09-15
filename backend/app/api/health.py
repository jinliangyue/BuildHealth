"""Health API · /api/buildings/{id}/health"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db import models as m
from app.schemas.api import HealthAssessmentRead
from app.services import assessment as svc

router = APIRouter(prefix="/buildings", tags=["health"])


@router.get("/{building_id}/health", response_model=HealthAssessmentRead)
def get_health(building_id: int, db: Session = Depends(get_db)):
    """返回该建筑最新一次 HealthAssessment 记录。"""
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
            detail=f"No HealthAssessment found for building {building_id}",
        )
    return latest


@router.post("/{building_id}/health/recompute", response_model=HealthAssessmentRead)
def recompute_health(building_id: int, db: Session = Depends(get_db)):
    """重新跑完整计算链路（异常检测 + BHI）并写入一条新 HealthAssessment。"""
    b = db.get(m.Building, building_id)
    if b is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Building {building_id} not found",
        )

    anomalies = svc.run_anomaly_detection(db, building_id)
    payload = svc.compute_health_assessment(db, b, anomalies)

    record = m.HealthAssessment(
        building_id=building_id,
        score=payload["score"],
        structural_safety=payload["structural_safety"],
        facility_condition=payload["facility_condition"],
        environmental_quality=payload["environmental_quality"],
        energy_performance=payload["energy_performance"],
        fire_safety=payload["fire_safety"],
        calculation_version=payload["calculation_version"],
        explanation=payload["explanation"],
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record
