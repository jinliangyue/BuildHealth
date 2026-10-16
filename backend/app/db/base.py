"""
SQLAlchemy Declarative Base · Phase 1 引入
===========================================

所有 ORM 模型继承此 Base,通过 ``Base.metadata.tables`` 枚举
声明的表。当前声明 **9** 张表(buildings / components / sensors /
monitoring_records / health_assessments / risk_alerts /
retrofit_recommendations / engineering_notes / audit_logs)。

变更历史:Phase 0 (2026-09-15) 占位 → Phase 1 (2026-09-22) 引入
ORM → Phase 4 V2 (2026-09-26) 加入 audit_logs (commit 4c215de)
→ 2026-10-16 止血轮 R1 (commit 4167ad1) init_db() 在 lifespan 中
补全缺表。
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """所有 ORM 模型的基类"""
    pass
