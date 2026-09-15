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
