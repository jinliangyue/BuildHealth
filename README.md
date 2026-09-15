# BuildHealth

> 既有建筑健康监测与智能更新决策平台
> Existing Building Health Monitoring & Intelligent Retrofit Decision Platform

## 当前状态

**Phase 2 — V1 Frontend & Backend Integration（已完成）**

完整数据链路：

```
SQLite (data/buildhealth.db)
    ↓
SQLAlchemy ORM (6 张表)
    ↓
Analytics Engine (anomaly / health / risk)
    ↓
FastAPI (9 个业务端点 + 2 health)
    ↓
Vite proxy /api
    ↓
React + TypeScript + ECharts
    ↓
6 个工程仪表盘页面
```

## 启动

### 后端

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 初始化模拟数据（一次性 · 会 wipe 现有数据库）
python -m scripts.seed_data

# 启动 FastAPI
uvicorn app.main:app --reload --port 8000
# → http://localhost:8000/docs
```

### 前端

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173/
```

Vite 已配置 `/api` proxy 自动转发到 `http://localhost:8000`。

## 文档

`docs/` 共 9 份设计文档，全部已更新到 Phase 2 状态：

- `01_Project_Overview.md` · 项目定位 + 范围 + 原则
- `02_Engineering_Requirements.md` · 工程真实性 10 条红线
- `03_System_Architecture.md` · 整体架构 + 模块边界
- `04_Data_Model.md` · 6 张表 ER + 索引 + 级联
- `05_Analytics_Design.md` · 3 种异常检测 + BHI 算法
- `06_Health_Assessment.md` · BHI 公式 + 5 维度派生
- `07_Risk_Classification.md` · 4 档分级 + 边界规则
- `08_Testing_Strategy.md` · 69 个 pytest 全部通过
- `09_Version_Roadmap.md` · Phase 0 → V1 → 未来

## 重要声明

- **数据来源**：全部为 `Simulated Data`（前端右下角常驻水印）
- **BHI 公式**：`Prototype Design Parameters (v1.0)`，非国家标准 / 行业标准 / 法定建筑安全等级
- **风险分级**：`Prototype Risk Classification`，仅辅助评估
- 系统**不**预测建筑倒塌、**不**替代专业结构检测、**不**替代安全鉴定、**不**生成自动加固方案

## 技术栈

| 层 | 技术 |
|---|---|
| Frontend | React 18 + TypeScript 5 + Vite 5 + Tailwind 3 + ECharts 5 + React Router 6 |
| Backend | Python 3.9 + FastAPI 0.115 + SQLAlchemy 2.0 + Pydantic 2.9 |
| Database | SQLite (开发期单文件 `data/buildhealth.db`) |
| Data Analysis | Pandas + NumPy + SciPy（已声明，Phase 3+ 使用） |
| Test | pytest 8.3 + FastAPI TestClient + StaticPool 内存 SQLite |

## 端到端验证状态

Phase 2 验证记录：

| 端点 | 验证状态 |
|---|---|
| GET `/api/buildings/` | ✓ 200 · 3 栋 |
| GET `/api/buildings/{id}` | ✓ 200 |
| GET `/api/buildings/{id}/sensors` | ✓ 200 · 5 个 |
| GET `/api/monitoring/` | ✓ 200 · 含时间窗口过滤 |
| GET `/api/buildings/{id}/health` | ✓ 200 |
| POST `/api/buildings/{id}/health/recompute` | ✓ 200 |
| GET `/api/buildings/{id}/risk` | ✓ 200 |
| GET `/api/buildings/{id}/alerts` | ✓ 200 |
| GET `/api/dashboard/summary` | ✓ 200 · 真实聚合 |

后端测试：69/69 pytest 通过。
前端构建：`npm run build` 成功（1314 KB bundle · 433 KB gzip）。
Vite proxy：前端 → 后端 → 数据库 完整链路 200 OK。

## License

Private / Proprietary — 仅限十八个人项目使用。
