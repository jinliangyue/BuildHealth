# BuildHealth Backend

Phase 0 Skeleton · FastAPI + SQLAlchemy + Pydantic

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
│   ├── main.py          # FastAPI app + CORS + 路由挂载
│   ├── api/             # REST 路由（Phase 1 实现）
│   ├── db/              # 数据库（Phase 1 完善）
│   ├── schemas/         # Pydantic 模型（Phase 1 实现）
│   ├── core/            # 配置（已实现 config.py）
│   └── services/        # 业务编排（Phase 1 实现）
├── tests/               # 测试
├── scripts/             # 辅助脚本
├── requirements.txt
└── .env.example
```

## 当前状态（Phase 0）

- ✅ FastAPI 应用骨架
- ✅ CORS 配置
- ✅ 健康检查端点
- ✅ 配置占位（BHI 权重 / 风险阈值 / 传感器阈值）
- ⏳ 6 张表的 ORM 模型未实现
- ⏳ 16 项业务 API 未实现
- ⏳ Analytics Engine 未挂载

详见 `../docs/03_System_Architecture.md` 与 `../docs/04_Data_Model.md`。
