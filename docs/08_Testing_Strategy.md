# 08 · 测试策略（Testing Strategy）

## 1. 测试金字塔

```
        ┌──────────┐
        │   E2E    │  ← Playwright（V1 不强制）
        ├──────────┤
        │Integration│ ← API 集成测试（pytest + FastAPI TestClient）
        ├──────────┤
        │  Unit    │  ← 核心计算逻辑 + 工具函数
        └──────────┘
```

**V1 重点**：Unit + Integration，E2E 留待 V2。

## 2. Unit Test（强制覆盖）

### 2.1 Analytics Engine（必须 100% 覆盖）

| 模块 | 最小测试数 | 测试场景 |
|---|---|---|
| trend.py | 5 | 稳态 / 上升 / 下降 / 空数据 / 单点数据 |
| anomaly.py | 8 | 阈值（高/中/低） / 变化率（升/降） / Z-score（正/负） / 无异常 / 多异常 |
| health.py | 6 | 满分 / 零分 / 边界 75 / 边界 60 / 权重异常 / 版本号缺失 |
| risk.py | 6 | Normal / Attention / Abnormal / HighRisk / HIGH 异常覆盖 / 顶层原因 |
| sim_data.py | 3 | 3 种建筑数据生成 / 时间连续性 / 异常触发生成 |

### 2.2 后端 API（关键路径）

| API | 最小测试数 |
|---|---|
| `GET /api/buildings` | 2（空 / 有数据） |
| `POST /api/buildings` | 2（成功 / 字段缺失） |
| `GET /api/monitoring/{sensor_id}` | 3（空 / 单点 / 时间窗口） |
| `GET /api/health/{building_id}` | 2（有 / 无） |
| `POST /api/health/recompute/{building_id}` | 1 |

## 3. Integration Test

使用 FastAPI `TestClient` + 内存 SQLite：

```python
# tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.db.base import Base
from app.db.session import get_db

@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    yield TestingSessionLocal
    engine.dispose()

@pytest.fixture
def client(test_db):
    def override_get_db():
        try:
            db = test_db()
            yield db
        finally:
            db.close()
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)
```

## 4. 前端测试（V1 最低要求）

- 至少 1 个组件渲染测试（用 Vitest + React Testing Library）
- API client 的 mock 测试

## 5. 工程真实性测试

在 `tests/test_engineering_redlines.py` 中：

```python
def test_no_national_standard_claim():
    """不得在任何静态文案中声称是国家/行业标准"""
    # 扫描 frontend/src 与 backend/app 中所有字符串
    forbidden = ["国家标准", "行业标准", "GB/T", "JGJ"]
    # 实际扫描逻辑
    ...

def test_no_real_building_claim():
    """不得声称部署在真实小区"""
    forbidden = ["真实小区", "已部署", "实际监测"]
    ...

def test_bhi_version_present():
    """每次写入 HealthAssessment 必须含 bhi_version"""
    ...
```

## 6. 测试运行

```bash
cd backend
pytest tests/ -v
pytest tests/ --cov=app --cov-report=term-missing
```

## 7. CI（未来）

Phase 0 不强制 CI。

未来建议：GitHub Actions 跑 pytest + 前端 lint + 集成测试。

## 8. 当前状态

**Phase 0** — 测试策略设计完成

- ✅ 测试金字塔已规划
- ✅ Unit test 场景清单已列出
- ✅ Integration test fixture 已设计
- ⏳ 测试用例实际未编写
- ⏳ 当前 `tests/` 目录仅占位

---

**文档版本**：v0.1 · Phase 0 起草
**最后更新**：2026-09-15
**状态**：Designed but not implemented
