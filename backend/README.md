# BuildHealth Backend

**Phase 6B / v1.1.0** · FastAPI + SQLAlchemy + Pydantic · Python 3.12
(local venv 3.12.14; Docker base `python:3.12-slim`; CI matrix
3.9 / 3.11 / 3.12)

## 启动

```bash
# 安装依赖（建议先创建虚拟环境）
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 启动开发服务器
uvicorn app.main:app --reload --port 8000

# 或
python app/main.py
```

启动后访问：

- `http://localhost:8000/` — 项目标识
- `http://localhost:8000/api/health` — 健康检查
- `http://localhost:8000/docs` — Swagger UI
- `http://localhost:8000/redoc` — ReDoc

## 测试

```bash
pytest tests/ -v
```

## 目录

```
backend/
├── app/
│   ├── main.py          # FastAPI app + CORS + lifespan + 路由挂载
│   ├── api/             # REST 路由（10 个子路由文件 / 17 endpoints）
│   ├── audit/           # Phase 7 审计中间件 + 查询路由（2 endpoints）
│   ├── ai/              # AI Engineering Assistant（Phase 5 V3 / mock + openai-compatible）
│   ├── analytics/       # 三方法异常检测 + BHI + 风险分类 + Retrofit priority
│   ├── db/              # 9 表 ORM + 会话管理 + 缺表补全 init_db()
│   ├── schemas/         # Pydantic 模型（Phase 1 实现）
│   ├── core/            # 配置（config.py,Phase 1 起完整实现）
│   ├── knowledge/       # 检索增强(jieba + 30 组工程同义词,commit 3d540a2)
│   ├── models/          # SQLAlchemy ORM 9 模型
│   ├── retrofit/        # Retrofit decision priority rule engine
│   ├── risk/            # 4 档风险分类(含 override rule)
│   └── services/        # 业务编排（Phase 1 实现）
├── tests/               # 33 个 test_*.py + conftest.py + __init__.py
├── scripts/             # 辅助脚本(seed_data / import_csv / retrieval_eval / llm_eval)
├── requirements.txt
└── venv/                # 本地虚拟环境(Python 3.12.14)
```

## 当前状态（Phase 6B · v1.1.0）

- ✅ FastAPI 应用 + CORS + 健康检查 + 21 个 API endpoints
- ✅ 配置完整(BHI v1.0 / RP-v1.0 / Risk v1.0 参数版本化)
- ✅ 9 张 ORM 表全部定义 + 启动期 `init_db()` 幂等补全
- ✅ Analytics Engine(三方法异常 / BHI / 风险 / Retrofit priority)
- ✅ AI Engineering Assistant(Mock 默认 + 可选 openai-compatible,43 禁词 + 强制 disclaimer)
- ✅ RAG 检索评估集(50 query,recall@3=0.64 / MRR=0.54)
- ✅ Audit 中间件(每个 HTTP 请求一行 metadata,不存 body 与 AI 文本)
- ✅ 测试覆盖:CI **473 passed, 1 skipped**(CI 不装 deepeval → `test_deepeval_integration.py` 整模块 `importorskip`,只计 1 个 skip);本地装有 deepeval 时收集 483 = **478 passed + 5 skipped**(那 5 个 live 用例需 `OPENAI_API_KEY`)

详见 `../docs/03_System_Architecture.md` · `../docs/04_Data_Model.md` ·
`../docs/28_Project_Fact_Sheet.md` §17–§21。
