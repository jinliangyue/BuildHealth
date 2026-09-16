"""AI Engineering Assistant API · Phase 5 V3 + Phase 6A"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db import models as m
from app.ai.schemas import AIAskRequest, AIHealthStatus, AIProviderError, AIResponse
from app.ai.service import get_ai_service

router = APIRouter(prefix="/ai", tags=["ai"])


# Phase 6A: structured error mapping
# 503 = service unavailable (upstream / config issues, retry may help after fix)
# 500 = internal server error (genuine server bug)
_TRANSIENT_ERROR_CODES = {
    "timeout",
    "network_error",
    "provider_error",
    "rate_limit",
    "config_error",  # AI misconfigured → service not really available
}


def _http_status_for(code: str) -> int:
    if code in _TRANSIENT_ERROR_CODES:
        return status.HTTP_503_SERVICE_UNAVAILABLE
    return status.HTTP_500_INTERNAL_SERVER_ERROR


@router.get("/health", response_model=AIHealthStatus)
def ai_healthcheck():
    """AI provider 健康检查. 返回 status (ok / provider_not_configured / provider_error)."""
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
    try:
        resp = get_ai_service().summarize_building(db, building_id)
    except AIProviderError as e:
        raise HTTPException(
            status_code=_http_status_for(e.code),
            detail={"provider_error": e.code, "message": e.message},
        )
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
    """基于 building 上下文回答 question (Mock keyword routing 或 real LLM call)."""
    if db.get(m.Building, building_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Building {building_id} not found",
        )
    try:
        resp = get_ai_service().ask_about_building(
            db, building_id, payload.question
        )
    except AIProviderError as e:
        raise HTTPException(
            status_code=_http_status_for(e.code),
            detail={"provider_error": e.code, "message": e.message},
        )
    if resp is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unable to build context for building {building_id}",
        )
    return resp
