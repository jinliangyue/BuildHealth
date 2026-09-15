# 03 · 系统架构（System Architecture）

## 1. 总体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (React SPA)                      │
│  Dashboard │ Buildings │ Building Detail │ Monitoring │ ... │
│            Vite + TypeScript + Tailwind + ECharts           │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP / JSON
                           │ (OpenAPI auto-generated docs)
┌──────────────────────────┴──────────────────────────────────┐
│                    Backend (FastAPI)                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐    │
│  │Building  │ │Component │ │ Sensor   │ │Monitoring    │    │
│  │  API     │ │   API    │ │  API     │ │   API        │    │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └──────┬───────┘    │
│       │            │            │              │            │
│  ┌────┴────────────┴────────────┴──────────────┴───────┐    │
│  │         SQLAlchemy ORM (Models + Session)          │    │
│  └────────────────────────┬──────────────────────────┘    │
└───────────────────────────┼───────────────────────────────┘
                            │
┌───────────────────────────┴───────────────────────────────┐
│                  SQLite (dev)                               │
│   data/buildhealth.db                                       │
└────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│             Analytics Engine (独立 Python 模块)             │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐     │
│  │ Trend Engine │ │Anomaly Engine│ │Health Assess Eng │     │
│  └──────────────┘ └──────────────┘ └──────────────────┘     │
│  ┌──────────────────┐ ┌─────────────────────────────┐      │
│  │Risk Class Engine │ │Simulated Data Generator     │      │
│  └──────────────────┘ └─────────────────────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

## 2. 模块边界

### 2.1 Frontend（React SPA）

**职责**：用户交互 + 数据可视化

**目录结构（设计）**：

```
frontend/
├── src/
│   ├── pages/
│   │   ├── Dashboard.tsx
│   │   ├── Buildings.tsx
│   │   ├── BuildingDetail.tsx
│   │   ├── Monitoring.tsx
│   │   ├── RiskHealth.tsx
│   │   └── Settings.tsx
│   ├── components/
│   │   ├── charts/
│   │   │   ├── TrendChart.tsx
│   │   │   ├── BhiRadar.tsx
│   │   │   └── DistributionPie.tsx
│   │   ├── layout/
│   │   │   ├── Sidebar.tsx
│   │   │   └── TopBar.tsx
│   │   └── ui/
│   │       ├── Card.tsx
│   │       ├── Badge.tsx
│   │       └── DataTable.tsx
│   ├── api/
│   │   ├── client.ts         # axios instance
│   │   ├── buildings.ts
│   │   ├── sensors.ts
│   │   ├── monitoring.ts
│   │   └── health.ts
│   ├── types/
│   │   └── api.ts            # 共享 TS 类型（与后端 Pydantic 对应）
│   ├── hooks/
│   ├── App.tsx
│   └── main.tsx
├── package.json
├── vite.config.ts
├── tailwind.config.js
└── tsconfig.json
```

**禁止**：硬编码 BHI / 风险等级 / 异常数量 / 监测数据 / 建筑数量（仅静态文案除外）

### 2.2 Backend（FastAPI）

**职责**：REST API + 业务逻辑编排

**目录结构（设计）**：

```
backend/
├── app/
│   ├── main.py               # FastAPI app + CORS + router 挂载
│   ├── api/
│   │   ├── buildings.py
│   │   ├── components.py
│   │   ├── sensors.py
│   │   ├── monitoring.py
│   │   ├── health.py
│   │   ├── risk.py
│   │   └── analytics.py
│   ├── db/
│   │   ├── session.py        # SQLAlchemy session
│   │   ├── base.py           # Declarative Base
│   │   └── models.py         # ORM 模型（6 张表）
│   ├── schemas/
│   │   ├── building.py       # Pydantic 模型
│   │   ├── component.py
│   │   ├── sensor.py
│   │   ├── monitoring.py
│   │   ├── health.py
│   │   └── risk.py
│   ├── core/
│   │   ├── config.py         # 配置（权重、阈值）
│   │   └── deps.py           # 依赖注入
│   └── services/
│       └── (业务编排层，预留)
├── tests/
│   ├── test_health.py
│   ├── test_risk.py
│   └── test_api.py
├── requirements.txt
└── .env.example
```

### 2.3 Analytics Engine（独立 Python 包）

**职责**：纯函数式计算 + 可独立测试

**目录结构（设计）**：

```
analytics/                       # 设计阶段
├── __init__.py
├── trend.py                     # 移动平均 / 同比 / 环比
├── anomaly.py                   # Threshold / Rate / Z-score
├── health.py                    # BHI 计算
├── risk.py                      # 风险分级
└── sim_data.py                  # 模拟数据生成器
```

**特点**：

- 不依赖 FastAPI / SQLAlchemy
- 输入：DataFrame 或 dict
- 输出：dict / DataFrame
- 100% 可单元测试

### 2.4 Database（SQLite）

**职责**：持久化

**位置**：`data/buildhealth.db`（运行时生成）

**6 张表**：Building / Component / Sensor / MonitoringRecord / HealthAssessment / RiskAlert

详见 `docs/04_Data_Model.md`。

## 3. 数据流（自下而上）

```
Simulated Data Generator
        │
        ▼
SQLite (MonitoringRecord 批量插入)
        │
        ▼
Analytics Engine (Trend / Anomaly / Health / Risk)
        │
        ▼
SQLite (HealthAssessment / RiskAlert 写入)
        │
        ▼
FastAPI Routes (查询 / 聚合 / 过滤)
        │
        ▼
React Components (axios GET)
        │
        ▼
ECharts (时序图 / 雷达图 / 分布图)
```

**反向追溯**：前端任意一个数值都可以通过 API → DB 查询定位到原始记录行。

## 4. 关键设计决策

### 4.1 为什么 Analytics Engine 独立成包？

- 纯函数 → 易测试
- 不耦合 Web 框架 → 未来可移植到 Airflow / Cron 离线任务
- 与后端 API 层解耦 → API 只负责 IO，逻辑层负责计算

### 4.2 为什么 SQLite？

- V1 单机原型，零部署成本
- SQLAlchemy 抽象，未来可平滑切换到 PostgreSQL
- 文件级备份方便

### 4.3 为什么 ECharts 而不是 Recharts？

- ECharts 文档更全，中文社区成熟
- 工程类仪表盘场景 ECharts 表现更稳定
- 时序图 / 雷达图 / 复杂可视化 ECharts 更专业

### 4.4 为什么不用 Tailwind UI / shadcn 等组件库？

- 避免引入不必要的依赖（CLAUDE.md §十四）
- 自定义设计更符合"Modern Engineering / Technical Dashboard"风格
- 减少 bundle 体积

## 5. CORS 与安全（V1）

**CORS**：开发期放开 `http://localhost:5173`（Vite 默认端口）

**鉴权**：V1 无用户权限系统，仅本地访问

**敏感数据**：无（全部为模拟数据）

## 6. 部署（V1 仅本地）

- 后端：`uvicorn app.main:app --reload --port 8000`
- 前端：`npm run dev`（Vite dev server · port 5173）
- 数据库：`data/buildhealth.db`（自动创建）

## 7. 当前状态

**Phase 0** — 架构设计完成

- ✅ 整体架构图已设计
- ✅ 目录结构已规划
- ⏳ 后端代码仅 main.py + health check
- ⏳ 前端代码仅 Vite 默认 scaffold
- ⏳ Analytics Engine 仅空目录

---

**文档版本**：v0.1 · Phase 0 起草
**最后更新**：2026-09-15
**状态**：Designed but not implemented
