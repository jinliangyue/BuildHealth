"""Retrofit Decision API · Phase 4 V2"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.api import (
    RetrofitDecisionRead,
    RetrofitRecommendationDetailRead,
    RetrofitOverviewResponse,
)
from app.services import retrofit_service as svc

router = APIRouter(tags=["retrofit"])


@router.get(
    "/buildings/{building_id}/retrofit",
    response_model=RetrofitDecisionRead,
)
def get_building_retrofit(building_id: int, db: Session = Depends(get_db)):
    """
    返回单建筑的完整 retrofit decision:
      - building
      - overall_priority (0-100)
      - overall_priority_level (Low/Medium/High/Very High)
      - recommendations (按 priority_score 降序, 含 evidence chain + breakdown)
      - engineering_notes
      - disclaimer
    """
    decision = svc.get_retrofit_decision(db, building_id)
    if decision is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Building {building_id} not found",
        )
    return decision


@router.get(
    "/buildings/{building_id}/retrofit/{recommendation_id}",
    response_model=RetrofitRecommendationDetailRead,
)
def get_building_retrofit_recommendation(
    building_id: int,
    recommendation_id: int,
    db: Session = Depends(get_db),
):
    """返回单条 recommendation 的完整 detail (含 priority breakdown)."""
    # 先校验 building 存在
    from app.db import models as m

    b = db.get(m.Building, building_id)
    if b is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Building {building_id} not found",
        )

    detail = svc.get_retrofit_recommendation(db, building_id, recommendation_id)
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Recommendation {recommendation_id} not found for "
                f"building {building_id}; valid IDs are 1..N where N is "
                f"the count of recommendations for this building"
            ),
        )
    return detail


@router.get(
    "/retrofit/overview",
    response_model=RetrofitOverviewResponse,
)
def get_retrofit_overview(db: Session = Depends(get_db)):
    """
    跨建筑 retrofit 概览, 用于 /retrofit 页面.
    """
    return svc.get_retrofit_overview(db)
