"""Sensors API · /api/buildings/{id}/sensors"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db import models as m
from app.schemas.api import SensorRead

router = APIRouter(prefix="/buildings", tags=["sensors"])


@router.get("/{building_id}/sensors", response_model=List[SensorRead])
def list_sensors(building_id: int, db: Session = Depends(get_db)):
    b = db.get(m.Building, building_id)
    if b is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Building {building_id} not found",
        )
    return (
        db.query(m.Sensor)
        .filter(m.Sensor.building_id == building_id)
        .order_by(m.Sensor.id)
        .all()
    )
