"""
数据库 Session 管理
Phase 0 占位 · Phase 1 实现完整逻辑
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


def init_db() -> None:
    """Create any missing tables on the live engine. Idempotent.

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
    """
    # Imported lazily so creating the engine doesn't require models
    # to be importable (engine is created at module import time, but
    # Base.metadata.create_all needs every model class registered).
    from app.db.base import Base
    from app.db import models  # noqa: F401  · ensure models register onto Base.metadata
    Base.metadata.create_all(bind=engine)
