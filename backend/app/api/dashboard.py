"""Dashboard API · /api/dashboard/summary"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.api import DashboardSummary
from app.services import assessment as svc

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(db: Session = Depends(get_db)):
    """
    返回全平台 Dashboard 聚合数据。
    所有数值均由 service 层从数据库实时计算，禁止硬编码。
    """
    return svc.get_dashboard_summary(db)
