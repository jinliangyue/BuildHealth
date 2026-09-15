"""Monitoring API · /api/monitoring"""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db import models as m
from app.schemas.api import MonitoringRecordRead

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get("/", response_model=List[MonitoringRecordRead])
def query_monitoring(
    building_id: Optional[int] = None,
    sensor_id: Optional[int] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    limit: int = Query(1000, ge=1, le=10000),
    db: Session = Depends(get_db),
):
    """支持 building_id / sensor_id / 时间窗口 过滤的监测数据查询。"""
    q = db.query(m.MonitoringRecord).join(m.Sensor, m.MonitoringRecord.sensor_id == m.Sensor.id)

    if building_id is not None:
        b = db.get(m.Building, building_id)
        if b is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Building {building_id} not found",
            )
        q = q.filter(m.Sensor.building_id == building_id)

    if sensor_id is not None:
        s = db.get(m.Sensor, sensor_id)
        if s is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sensor {sensor_id} not found",
            )
        q = q.filter(m.MonitoringRecord.sensor_id == sensor_id)

    if start is not None:
        q = q.filter(m.MonitoringRecord.timestamp >= start)
    if end is not None:
        q = q.filter(m.MonitoringRecord.timestamp <= end)

    q = q.order_by(m.MonitoringRecord.timestamp).limit(limit)
    return q.all()
