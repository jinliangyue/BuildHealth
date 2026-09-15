"""
pytest fixtures · 内存 SQLite + FastAPI TestClient

关键：内存 SQLite 必须用 StaticPool + 共享连接字符串，
否则不同 session 会拿到不同的内存 DB（导致 "no such table"）。
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.db import models as m  # 确保模型注册到 Base.metadata
from app.main import app
from fastapi.testclient import TestClient


@pytest.fixture
def test_engine():
    """共享内存 SQLite 引擎（StaticPool + 单 connection）"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def test_session(test_engine):
    SessionLocal = sessionmaker(bind=test_engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def client(test_engine):
    """FastAPI TestClient with overridden DB dependency"""
    SessionLocal = sessionmaker(bind=test_engine)

    def override_get_db():
        try:
            db = SessionLocal()
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
