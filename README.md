# BuildHealth

> 既有建筑健康监测与智能更新决策平台
> Existing Building Health Monitoring & Intelligent Retrofit Decision Platform

## 当前状态

**Phase 6B — Engineering Knowledge RAG & Evidence Grounding（已完成）**

V3.2 在 V3.1 Real LLM Provider 基础上, 引入**项目自有工程知识库 (RAG)**, 让 AI 的解释可以引用项目内部写定的工程知识文档, 同时严格区分「本建筑数据证据」与「通用工程知识背景」.

```
SQLite (data/buildhealth.db) · 8 张表 (V1 6 + V2 2)
    ↓
SQLAlchemy ORM
    ↓
Analytics Engine (V1: anomaly/health/risk · V2: priority/recommendation_rules)
    ↓
FastAPI (15 个业务端点 + 2 health)
    ↓
    ├── V1/V2 端点 (deterministic engineering data)
    └── V3 AI 端点 (Mock / OpenAI-compatible provider, explanation layer)
             ↑
             │  KnowledgeRetriever (TF-IDF + cosine · 纯标准库)
             │  backend/knowledge/*.md → 5 docs → 23 chunks → top-3
             └── KnowledgeEvidence → AIResponse.knowledge_evidence
    ↓
Vite proxy /api
    ↓
React + TypeScript + ECharts
    ↓
7 个工程仪表盘页面 (含 AI Assistant · ProviderBadge 显示 mode
                    · Knowledge Sources 分区)
```

**V1 Capabilities (Phase 1-3):** Building / Component / Sensor / MonitoringRecord · 3 种异常检测 · BHI 0-100 · 4 档 Risk · 6 仪表盘页面 + 9 API 端点

**V2 Capabilities (Phase 4):** RetrofitRecommendation · EngineeringNote · 5 条规则引擎 · RP-v1.0 优先级 · Evidence Chain · 3 新 API · `/retrofit` 页面

**V3 Capabilities (Phase 5):** AI Mock Mode · EngineeringContext · AIResponse · 5 quick question · evidence 可点击 · 3 新 API · `/ai-assistant` 页面

**V3.1 Capabilities (Phase 6A):**
- ✓ **OpenAI-compatible Real Provider** (纯 httpx, 不安装 SDK)
- ✓ Env-driven config (AI_PROVIDER / AI_API_KEY / AI_BASE_URL / AI_MODEL)
- ✓ Failure handling (timeout / 401 / 403 / 429 / 5xx / malformed JSON)
- ✓ Pydantic output validation + redline scan
- ✓ Disclaimer 强制覆盖 (LLM 输出也会被 AI_DISCLAIMER 替换)
- ✓ Prompt injection 防护 (system prompt 显式声明 user untrusted)
- ✓ _MisconfiguredProvider 显式降级 (缺 key/url → 503 + structured body)
- ✓ Frontend ProviderBadge (Mock Mode / Live AI / Not Configured)

**V3.2 Capabilities (Phase 6B):**
- ✓ **Project-only engineering knowledge base** (`backend/knowledge/` · 5 篇 Markdown)
- ✓ Deterministic loading + chunking (`##` 切分 · 5 docs → 23 chunks)
- ✓ **轻量 lexical retrieval**: TF-IDF + cosine, 纯 Python 标准库, 无 vector DB / 无 embedding / 无外部依赖
- ✓ `KnowledgeEvidence` schema (document / section / content / relevance_score / source / chunk_id)
- ✓ `AIResponse.knowledge_evidence` 字段 (与 `evidence` 永不合并)
- ✓ **Engineering Data Context 与 Knowledge Context 分离** (prompt 两个独立 key)
- ✓ Mock Provider 支持 knowledge evidence
- ✓ Real LLM Provider 支持 knowledge context + 强制 evidence 取自检索
- ✓ Frontend **Knowledge Sources** 分区展示 (与 Evidence 分区配色区分)
- ✓ RAG 专项红线 11 条 + 知识库语料自检 (无标准编号 / 无语料级禁词)
- ✓ 优雅降级 (retriever 缺失或异常 → RAG 关闭, AI 端点照常)
- ✗ Conversation (Phase 6C 留)
- ✗ Vector DB / embedding / 语义检索 (不在路线内)
- ✗ 互联网知识爬取 (不在路线内)

## 工程知识库 (Phase 6B)

`backend/knowledge/` 存放**项目自有**的工程知识文档, 供 AI 解释层引用.

| 文档 | 主题 |
|---|---|
| `anomaly_detection.md` | Threshold / rate-of-change / z-score 三方法 |
| `health_assessment.md` | BHI 0-100 + 5 维度 + 权重 |
| `risk_classification.md` | 4 档分级 + HIGH override 规则 |
| `retrofit_decision.md` | RP-v1.0 优先级 + REC-v1.0 规则 |
| `engineering_redlines.md` | 10 条红线 + 强制 disclaimer |
| `README.md` | 目录说明 · **不进入索引** |

**检索**: `tokenize → TF-IDF → cosine → top-3`, `relevance_score` ∈ [0, 1].
**查询增强**: 用户问题 + EngineeringContext 关键词 (metric / risk / category / weakest dimension).

**核心边界** — 知识库是背景, 不是证据:

| | Engineering Data Evidence | Knowledge Evidence |
|---|---|---|
| 字段 | `AIResponse.evidence` | `AIResponse.knowledge_evidence` |
| 含义 | **本建筑**实测与派生数据 | **通用**工程概念背景 |
| 优先级 | 绝对优先 | 仅背景解释 |
| 能否证明本建筑状况 | 能 | **不能** |

知识文档**不含**任何国家 / 行业标准编号, 不提供具体结构安全限值,
不构成工程鉴定或安全认证 (由 `tests/test_rag_redlines.py` 强制扫描).

## AI Assistant Modes

| Mode | 启用条件 | 行为 |
|---|---|---|
| **Mock Mode** (default) | 无 env, 或 `AI_PROVIDER=mock` | `MockProvider`, 确定性, 无外部调用, 完全离线 |
| **Live AI** | `AI_PROVIDER=openai-compatible` + `AI_API_KEY` + `AI_BASE_URL` | `OpenAICompatibleProvider` 调真实 LLM |
| **Not Configured** | `AI_PROVIDER=openai-compatible` 但缺 key/url | `_MisconfiguredProvider` 显式报错 (health 200 status="provider_not_configured", summary/ask → 503) |

切换到 Live AI 流程:
```bash
cp backend/.env.example backend/.env
# 编辑 backend/.env (本机, 不 commit):
# AI_PROVIDER=openai-compatible
# AI_API_KEY=sk-your-key
# AI_BASE_URL=https://api.openai.com/v1
# AI_MODEL=gpt-4o-mini
```

兼容端点: OpenAI / OpenRouter / Ollama / LM Studio / vLLM 等任何 OpenAI-compatible API.

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

`docs/` 共 21 份设计文档:

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

### V3 (Phase 5)
- `14_AI_Assistant_Design.md` · AI Assistant 设计
- `15_AI_Context_and_Grounding.md` · Context Builder + 证据落地
- `16_AI_Safety_Redlines.md` · AI 安全红线 + 强制 disclaimer
- `17_Phase5_Testing.md` · V3 测试策略

### V3.1 (Phase 6A)
- `18_Real_LLM_Provider.md` · Real Provider 设计
- `20_AI_Grounding_and_Safety.md` · V3 + V6A + V6B 合并安全
- `21_Phase6_Testing.md` · Phase 6A + 6B 测试策略

### V3.2 (Phase 6B)
- `19_Engineering_RAG.md` · **Engineering Knowledge Base + RAG + Evidence Grounding (implemented)**

## 重要声明 (Engineering Disclaimer)

- **数据来源**: 全部为 `Simulated Data`（前端右下角常驻水印）
- **BHI 公式**: `Prototype Design Parameters (BHI-v1.0)`, 非国家标准 / 行业标准
- **风险分级**: `Prototype Risk Classification`, 仅辅助评估
- **改造优先级 (V2)**: `Prototype Retrofit Priority Parameters (RP-v1.0)`, 仅工程决策支持
- **改造建议 (V2)**: `Recommendation Rules v1.0 (REC-v1.0)`, 非自动结构设计
- **AI Engineering Assistant (V3)**: `AI-v1.0`, 解释层 / 知识助手
- **Real LLM (V3.1)**: OpenAI-compatible, Pydantic + redline 验证, 仍是解释层

**系统能力边界:**
- ✓ 识别问题 · 解释风险 · 计算优先级 · 推荐改造方向 · 给出成本等级 · 建议下一步行动 · 解释已有工程数据 · 引用项目内部工程知识作背景
- ✗ 不预测建筑倒塌 · 不替代专业结构检测 · 不替代安全鉴定 · 不生成自动加固方案 · 不出结构施工图 · 不生成钢筋设计 · 不替代结构工程师 · 不自动完成工程鉴定 · 不声称符合标准

**V3.2 不做的事:**
- ✗ 不接 Vector DB / embedding / 语义检索
- ✗ 不做互联网知识爬取 / 不引入外部工程标准
- ✗ 不把知识库内容当作官方规范
- ✗ 不让 AI 替代专业工程判断 / 不做自动结构设计
- ✗ 不做 Conversation / 多轮对话 / conversation_id (Phase 6C 留)
- ✗ 不接真实 Anthropic native SDK (用 OpenAI-compatible 代理)
- ✗ 不做 streaming response / SSE
- ✗ 不做 function calling / Agent / MCP
- ✗ 不做 rate limiting / cost tracking
- ✗ 不接 IoT / 真实硬件 / BIM / GIS / 3D
- ✗ 不做云部署 / 支付 / 用户权限
- ✗ 不在 AI 核心计算中替代确定性工程算法
- ✗ 不修改 V1 BHI / V2 Retrofit 算法
- ✗ 不安装 openai / anthropic / langchain 等 SDK

**AI 不得声称 (强制, V3 + V3.1 + V3.2):**
- ✗ "This building is safe" / "building will collapse"
- ✗ "Automatic structural appraisal completed"
- ✗ "Official safety certification"
- ✗ "AI-designed reinforcement"
- ✗ "Professional inspection completed" (without qualified qualifier)
- ✗ "Complies with national standard" / 符合国家标准
- ✗ **"The knowledge document proves …" / 把知识文档当作本建筑的证据**
- ✗ **"Per the retrieved standard" / 把知识文档当作官方标准**
- ✗ 即使 LLM 返回自己的 disclaimer, 也会被强制覆盖为 AI_DISCLAIMER
- ✗ 即使 LLM 返回自己的 knowledge_evidence, 也会被丢弃, 只用检索器真实产出

## 技术栈

| 层 | 技术 |
|---|---|
| Frontend | React 18 + TypeScript 5 + Vite 5 + Tailwind 3 + ECharts 5 + React Router 6 |
| Backend | Python 3.9 + FastAPI 0.115 + SQLAlchemy 2.0 + Pydantic 2.9 |
| Database | SQLite (开发期单文件 `data/buildhealth.db`) |
| Data Analysis | Pandas + NumPy + SciPy (V2 trend score 中使用) |
| AI Mock | Phase 5 MockProvider (deterministic) |
| AI Real | Phase 6A OpenAI-compatible Provider (纯 httpx, 不安装 SDK) |
| Test | pytest 8.3 + FastAPI TestClient + StaticPool 内存 SQLite / Vitest + Testing Library |

## 端到端验证状态

### V1 (9 endpoints)
全部 ✓ 200

### V2 (3 endpoints)
| 端点 | 验证 |
|---|---|
| GET `/api/buildings/{id}/retrofit` | ✓ 200 |
| GET `/api/buildings/{id}/retrofit/{rec_id}` | ✓ 200 |
| GET `/api/retrofit/overview` | ✓ 200 |

### V3 (3 endpoints)
全部 ✓ 200 (Mock Mode)

### V3.1 (3 endpoints · 含 503 错误路径)
| 端点 | Mock | Misconfigured |
|---|---|---|
| GET `/api/ai/health` | 200 + status=ok | 200 + status=provider_not_configured |
| POST `/api/ai/buildings/{id}/summary` | 200 | 503 + body.detail.provider_error=config_error |
| POST `/api/ai/buildings/{id}/ask` | 200 | 503 |

**测试统计 (Phase 6B 最终验收 · 2026-09-16):**
- Backend: **371 tests passed** (V1 76 + V2 123 + V3 79 + V3.1 43 + V3.2 50)
- Frontend: **78 tests passed** (V1 30 + V2 20 + V3 10 + V3.1 5 + V3.2 13)
- Engineering Redlines: ~30 V1 + 25+ V3 + 11 V3.2 phrases 强制扫描
- Frontend build: ✓ PASS (1351 KB bundle · 441 KB gzip · 714 modules)
- TypeScript: 0 errors
- API smoke test: ✓ 全部 14 端点 200 (含 knowledge_evidence 验证)
- **No secrets committed** (verified via grep + git diff)

## License

Private / Proprietary — 仅限十八个人项目使用。
