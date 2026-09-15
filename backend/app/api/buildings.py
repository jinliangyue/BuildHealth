"""Buildings API · /api/buildings"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db import models as m
from app.schemas.api import BuildingRead, BuildingsOverviewResponse, BuildingOverviewItem
from app.services import assessment as svc

router = APIRouter(prefix="/buildings", tags=["buildings"])


@router.get("/", response_model=List[BuildingRead])
def list_buildings(db: Session = Depends(get_db)):
    return db.query(m.Building).order_by(m.Building.id).all()


@router.get("/overview", response_model=BuildingsOverviewResponse)
def buildings_overview(db: Session = Depends(get_db)):
    """
    Batch overview for Buildings page.
    单次请求返回所有建筑的 BHI + Risk + active alert count。
    单建筑异常被隔离，整个接口不会失败。
    """
    items = svc.get_buildings_overview(db)
    return {"total": len(items), "items": items}


@router.get("/{building_id}", response_model=BuildingRead)
def get_building(building_id: int, db: Session = Depends(get_db)):
    b = db.get(m.Building, building_id)
    if b is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Building {building_id} not found",
        )
    return b
