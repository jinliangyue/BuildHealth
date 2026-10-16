"""
数据库 Session 管理
====================

完整实现见 Phase 1(2026-09-22)。当前职责:

* 创建全局 SQLAlchemy engine(SQLite,thread-share)。
* 暴露 ``SessionLocal`` + FastAPI ``get_db`` 依赖。
* 暴露 ``init_db()`` — 幂等的缺表补全入口,详见函数 docstring。
  项目**不**使用 alembic,见 init_db() 注释。

变更历史:Phase 0 (2026-09-15) 占位 → Phase 1 (2026-09-22) 完整实现
→ 2026-10-16 止血轮 R1 加入 init_db() + import-time/engine 创建分离。
"""
from app.core.config import DATABASE_URL
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite 必需
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """FastAPI 依赖注入：每次请求创建一个 Session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(bind=None) -> None:
    """Create any missing tables on ``bind`` (default: the live engine). Idempotent.

    This project has no migration tool (alembic is commented out in
    requirements.txt; seed_data.py runs ``Base.metadata.create_all``
    only against a fresh DB). So when a model is added later (e.g.
    AuditLog in commit 4c215de) the pre-existing on-disk SQLite is
    silently out of schema: AuditMiddleware._safe_write swallows
    OperationalError to WARNING, and ``/api/audit`` returns 500.

    ``init_db()`` runs ``create_all`` against the live engine — it
    issues only ``CREATE TABLE IF NOT EXISTS`` statements and never
    drops or rewrites existing data. Safe to call on every startup.

    Called once from the FastAPI ``lifespan`` in app.main. Tests do
    NOT trigger lifespan (conftest uses ``yield TestClient(app)``
    not ``with TestClient(app)``), so test fixtures stay in control
    of schema lifetime.

    ``bind`` is the seam that makes this function testable: production
    calls ``init_db()`` and the module-level ``engine`` is used, while a
    test can point it at a scratch engine, drop a table, and assert it
    gets filled back in. Without the seam a test can only re-run
    ``create_all`` against an already-complete fixture schema — which
    passes even when this function is deleted outright.
    """
    # Imported lazily so creating the engine doesn't require models
    # to be importable (engine is created at module import time, but
    # Base.metadata.create_all needs every model class registered).
    from app.db.base import Base
    from app.db import models  # noqa: F401  · ensure models register onto Base.metadata
    Base.metadata.create_all(bind=bind if bind is not None else engine)
