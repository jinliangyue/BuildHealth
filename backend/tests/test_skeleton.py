"""
Phase 0 Skeleton Test
验证 FastAPI 启动 + 基础端点
"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root():
    """根路径返回项目标识"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["project"] == "BuildHealth"
    assert "Phase 1" in data["phase"]


def test_health_check():
    """健康检查端点"""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_openapi_docs():
    """OpenAPI 文档自动生成"""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert data["info"]["title"] == "BuildHealth API"
