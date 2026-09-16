"""AI Engineering Assistant API · Phase 5 V3"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db import models as m
from app.ai.schemas import AIAskRequest, AIHealthStatus, AIResponse
from app.ai.service import get_ai_service

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/health", response_model=AIHealthStatus)
def ai_healthcheck():
    """AI provider 健康检查. 默认返回 mock provider 状态."""
    return get_ai_service().get_health()


@router.post(
    "/buildings/{building_id}/summary",
    response_model=AIResponse,
)
def ai_summarize(building_id: int, db: Session = Depends(get_db)):
    """生成建筑综合总结 (基于 V1/V2 已计算的工程数据)."""
    if db.get(m.Building, building_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Building {building_id} not found",
        )
    resp = get_ai_service().summarize_building(db, building_id)
    if resp is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unable to build context for building {building_id}",
        )
    return resp


@router.post(
    "/buildings/{building_id}/ask",
    response_model=AIResponse,
)
def ai_ask(
    building_id: int,
    payload: AIAskRequest,
    db: Session = Depends(get_db),
):
    """基于 building 上下文回答 question (Mock 关键词路由)."""
    if db.get(m.Building, building_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Building {building_id} not found",
        )
    resp = get_ai_service().ask_about_building(
        db, building_id, payload.question
    )
    if resp is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unable to build context for building {building_id}",
        )
    return resp
