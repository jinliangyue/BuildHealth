"""Buildings API · /api/buildings"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db import models as m
from app.schemas.api import (
    BuildingRead,
    BuildingsOverviewResponse,
    BuildingOverviewItem,
    RiskBoardResponse,
)
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


# 注意: 字面量路径必须注册在 `/{building_id}` **之前** — 否则 FastAPI
# 会把 "risk-board" 当成 building_id="risk-board" 拿去 `int()` 校验,
# 422 失败, 永远不会回退。性能轮 R2 加这条聚合端点时专门盯这个坑。
@router.get("/risk-board", response_model=RiskBoardResponse)
def buildings_risk_board(db: Session = Depends(get_db)):
    """
    RiskHealth 页面专用: 单次请求拿回 blocks + 全楼 active alerts。
    SQL 次数与建筑数量 N **无关** (固定 4+1), 见
    `tests/test_risk_board.py::test_risk_board_sql_count_*`。
    """
    board = svc.get_risk_board(db)
    return {"total": len(board["items"]), "items": board["items"], "alerts": board["alerts"]}


@router.get("/{building_id}", response_model=BuildingRead)
def get_building(building_id: int, db: Session = Depends(get_db)):
    b = db.get(m.Building, building_id)
    if b is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Building {building_id} not found",
        )
    return b
