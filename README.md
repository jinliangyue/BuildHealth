# BuildHealth

> 既有建筑健康监测与智能更新决策平台
> Existing Building Health Monitoring & Intelligent Retrofit Decision Platform

## 当前状态

**Phase 4 — V2 Retrofit Decision Support（已完成）**

V2 在 V1 监测+BHI+风险基础上,新增"改造决策支持"链路:

```
SQLite (data/buildhealth.db) · 8 张表 (V1 6 + V2 2)
    ↓
SQLAlchemy ORM
    ↓
Analytics Engine (V1: anomaly/health/risk · V2: priority/recommendation_rules)
    ↓
FastAPI (12 个业务端点 + 2 health)
    ↓
Vite proxy /api
    ↓
React + TypeScript + ECharts
    ↓
6 个工程仪表盘页面 (含新增 Retrofit Decision)
```

**V1 Capabilities (Phase 1-3):**
- Building / Component / Sensor / MonitoringRecord 管理
- 3 种异常检测 (threshold / rate_of_change / zscore)
- BHI (Building Health Index) 0-100, 5 维度加权
- 4 档 Risk Classification (Normal / Attention / Abnormal / HighRisk)
- 6 个仪表盘页面 + 9 个 API 端点

**V2 Capabilities (Phase 4):**
- RetrofitRecommendation 模型 + EngineeringNote
- 5 条规则引擎 (crack_growth / tilt_trend / moisture_control / energy_efficiency / comprehensive_assessment)
- RP-v1.0 加权优先级评分 (5 维度, 0-100)
- 完整 Evidence Chain (Sensors → Anomalies → BHI → Risk → Recommendation)
- 3 个新 API 端点
- 新增 `/retrofit` 页面 + Building Detail Retrofit Decision 段
- Engineering Notes 显示

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

`docs/` 共 13 份设计文档:

### V1 (Phase 0-3)
- `01_Project_Overview.md` · 项目定位 + 范围 + 原则
- `02_Engineering_Requirements.md` · 工程真实性 10 条红线
- `03_System_Architecture.md` · 整体架构 + 模块边界
- `04_Data_Model.md` · V1 6 张表 ER + 索引 + 级联
- `05_Analytics_Design.md` · 3 种异常检测 + BHI 算法
- `06_Health_Assessment.md` · BHI 公式 + 5 维度派生
- `07_Risk_Classification.md` · 4 档分级 + 边界规则
- `08_Testing_Strategy.md` · V1 测试策略
- `09_Version_Roadmap.md` · Phase 0 → V1 → 未来

### V2 (Phase 4)
- `10_Retrofit_Decision_Design.md` · Retrofit Decision 设计
- `11_Retrofit_Priority_Model.md` · RP-v1.0 优先级公式
- `12_Retrofit_Recommendation_Rules.md` · REC-v1.0 规则引擎
- `13_V2_Testing.md` · V2 测试策略

## 重要声明 (Engineering Disclaimer)

- **数据来源**: 全部为 `Simulated Data`（前端右下角常驻水印）
- **BHI 公式**: `Prototype Design Parameters (BHI-v1.0)`, 非国家标准 / 行业标准 / 法定建筑安全等级
- **风险分级**: `Prototype Risk Classification`, 仅辅助评估
- **改造优先级 (V2)**: `Prototype Retrofit Priority Parameters (RP-v1.0)`, 仅工程决策支持
- **改造建议 (V2)**: `Recommendation Rules v1.0 (REC-v1.0)`, 非自动结构设计

**系统能力边界:**
- ✓ 识别问题 · 解释风险 · 计算优先级 · 推荐改造方向 · 给出成本等级 · 建议下一步行动
- ✗ 不预测建筑倒塌 · 不替代专业结构检测 · 不替代安全鉴定 · 不生成自动加固方案 · 不出结构施工图 · 不生成钢筋设计 · 不替代结构工程师

**V2 不做的事:**
- ✗ 不接 IoT / 真实硬件
- ✗ 不做 BIM / GIS / 3D
- ✗ 不做云部署 / 支付 / 用户权限
- ✗ 不做自动结构设计 / 钢筋设计
- ✗ 不做真实建筑安全认证
- ✗ 不在核心计算中引入 LLM (Phase 5+ 计划加入)
- ✗ 不伪造精确造价或 ROI 数字
- ✗ 不修改 V1 BHI / Risk 算法

## 技术栈

| 层 | 技术 |
|---|---|
| Frontend | React 18 + TypeScript 5 + Vite 5 + Tailwind 3 + ECharts 5 + React Router 6 |
| Backend | Python 3.9 + FastAPI 0.115 + SQLAlchemy 2.0 + Pydantic 2.9 |
| Database | SQLite (开发期单文件 `data/buildhealth.db`) |
| Data Analysis | Pandas + NumPy + SciPy (已声明, V2 在 trend score 中使用) |
| Test | pytest 8.3 + FastAPI TestClient + StaticPool 内存 SQLite / Vitest + Testing Library |

## 端到端验证状态

### V1 (9 endpoints)
| 端点 | 验证 |
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

### V2 (3 endpoints)
| 端点 | 验证 |
|---|---|
| GET `/api/buildings/{id}/retrofit` | ✓ 200 · 含 evidence chain + priority breakdown |
| GET `/api/buildings/{id}/retrofit/{rec_id}` | ✓ 200 · 单条详情 |
| GET `/api/retrofit/overview` | ✓ 200 · 跨建筑聚合 |

**测试统计:**
- Backend: **199 tests passed** (V1 76 + V2 123)
- Frontend: **50 tests passed** (V1 30 + V2 20)
- Engineering Redlines: ~30 phrases 强制扫描
- Frontend build: ✓ PASS (1338 KB bundle · 439 KB gzip)
- TypeScript: 0 errors

## License

Private / Proprietary — 仅限十八个人项目使用。
