"""Buildings API · /api/buildings"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db import models as m
from app.schemas.api import BuildingRead

router = APIRouter(prefix="/buildings", tags=["buildings"])


@router.get("/", response_model=List[BuildingRead])
def list_buildings(db: Session = Depends(get_db)):
    return db.query(m.Building).order_by(m.Building.id).all()


@router.get("/{building_id}", response_model=BuildingRead)
def get_building(building_id: int, db: Session = Depends(get_db)):
    b = db.get(m.Building, building_id)
    if b is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Building {building_id} not found",
        )
    return b
