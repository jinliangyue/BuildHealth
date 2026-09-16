# BuildHealth

> 既有建筑健康监测与智能更新决策平台
> Existing Building Health Monitoring & Intelligent Retrofit Decision Platform

**土木工程 × 工程数据 × AI 数字化 × 工程决策支持**

BuildHealth 不是聊天机器人，也不是智能家居项目。它解决的是一个具体的
工程问题：结构检测依赖人工、成本高、周期长；监测系统能持续采集数据，
但原始数值本身不构成决策依据。中间缺一层**可解释、可复现、边界清晰的
工程分析层**。这个项目实现的就是这一层。

## 工程问题

| 现状 | 缺口 |
|---|---|
| 既有建筑存量持续增长 | 人工检测成本高、频次低 |
| 监测系统能持续采集数据 | 原始数值直接给人看，不构成决策依据 |
| 工程判断依赖资深工程师 | 经验难沉淀、难规模化 |
| AI 能生成自然语言 | 但不能让它参与工程计算，也不能让它下结论 |

BuildHealth 的答案是：**确定性工程算法负责算，AI 负责解释**，两者严格分层，
且 AI 层被红线约束住。

## 核心工作流

```
监测数据 (裂缝宽度 / 倾斜 / 温湿度 / 用电)
        ↓
异常检测 (阈值 · 变化率 · Z-score 三方法并行 → 按严重度去重)
        ↓
BHI 健康评分 (0-100 · 5 维度加权)
        ↓
风险分级 (4 档 · HIGH 异常覆盖规则)
        ↓
改造决策 (RP-v1.0 优先级 + REC-v1.0 建议规则 → 证据链)
        ↓
AI 解释层 (只读上述结果 + 检索项目内部知识库 → 自然语言解释)
```

关键约束：**数据单向流动**。工程数值全部由后端算法产出，AI 不能修改、
不能编造、不能下最终结论。AI 输出的免责声明会被后端强制覆盖。

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
FastAPI (16 个业务端点 + 2 health + 1 只读参数端点)
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

## 工程分析方法

全部参数集中在 `backend/app/analytics/config.py`，版本化并在文档中引用。
这些是 **Prototype Design Parameters**，不是国家或行业标准。

只读端点 `GET /api/engineering-parameters` 公开这组参数
（各层 calculation_version、BHI 权重、风险档位、改造优先级档位与权重、
异常检测阈值）与 prototype 声明。前端参数页从该端点读取，本地常量仅作
离线 fallback。档位表由引擎行为测试锁定，改一边不改另一边会直接失败。

### 异常检测（3 种方法并行）

| 方法 | 作用 | 参数 |
|---|---|---|
| Threshold | 抓绝对值突变 | crack_width 0.20/0.30 mm · tilt 3.0/4.0 ‰ · temperature 40 ℃ · humidity 85 % |
| Rate of Change | 抓持续发展 | 各指标独立的绝对变化量与相对百分比阈值 |
| Z-score | 抓偏离历史统计规律 | 7 天滚动窗口 · \|z\| > 4 异常 · \|z\| > 6 为 HIGH · 对用电/湿度关闭 |

三种检出按 `(sensor, metric, method, severity)` 去重后合并，避免同一事件重复告警。

### BHI 健康评分（BHI-v1.0）

`BHI = Σ (维度分 × 权重)`，范围 [0, 100]：

| 维度 | 权重 | 输入来源 |
|---|---|---|
| Structural Safety | 0.40 | 结构类异常（裂缝、倾斜） |
| Facility Condition | 0.20 | 设备与构件状态 |
| Environmental Quality | 0.15 | 温湿度稳定性 |
| Energy Performance | 0.10 | 用电变异系数 |
| Fire Safety | 0.15 | 消防安全维度 |

维度分超出 [0, 100] 会直接报错，不会被静默截断。

### 风险分级（4 档）

`BHI ≥ 90` Normal · `≥ 75` Attention · `≥ 60` Abnormal · `< 60` HighRisk。

覆盖规则：只要存在 HIGH 严重度异常，最低升级为 Attention。
这是保守方向的设计 —— 宁可多提醒，不会漏报。

### 改造决策（V2）

- **RP-v1.0**：5 个子分加权成 0-100 优先级，分档 Low / Medium / High / Very High
- **REC-v1.0**：规则引擎按类目生成改造建议，带成本等级与紧急度
- **证据链**：每条建议可回溯到触发它的传感器、异常与 BHI 维度
- 建议为**实时计算**，不落库（`retrofit_recommendations` 表保留但当前未使用）

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

### 工程强化 (Overnight Sprint)
- `22_Overnight_Engineering_Sprint.md` · 工程质量审计与修复记录
- `23_Project_Demo_Guide.md` · **演示脚本 · 30 秒 / 1 分钟 / 3 分钟版本 + 面试问答要点**

### 性能与作品集（Sprint 2）
- `24_Overnight_Sprint_2.md` · 性能/数据访问审计 + N+1 批量优化 + 追溯性与安全审计记录
- `25_Portfolio_English.md` · **英文作品集材料（国际工程咨询 / TIC / 工程数字化方向）**
- `26_Interview_Technical_Deep_Dive.md` · **18 个技术面试问答：实现 · 理由 · 局限 · 改进**

### 最终优化（Sprint 3）
- `27_Overnight_Sprint_3_Final.md` · 请求作用域计算复用 + 剩余 N+1 清理 + 等价性验证记录

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

**测试统计 (Sprint 3 封板 · 2026-09-17):**
- Backend: **412 tests passed** (V1/V2/V3/V3.1/V3.2 + 聚合等价性 12 + 参数端点 11 + mock 闸门 2 + 请求作用域复用 11)
- Frontend: **97 tests passed** (15 files)
- Engineering Redlines: 43 条禁词（含 11 条 RAG 专项）强制扫描，两个 provider 都走运行时闸门
- 跨端参数一致性: 后端测试用 `classify_risk` / `map_priority_level` 行为探针对比前端镜像
- 查询数不随建筑数增长: dashboard 7 · overview 4 · retrofit overview 6（均有测试锁定）
- 请求作用域复用: AI 链路异常检测由 2 次降为 1 次，等价性有测试证明
- Frontend build: ✓ PASS (1351 KB bundle · 441 KB gzip · 714 modules)
- TypeScript: 0 errors
- API smoke test: ✓ 全部 19 端点 200
- **No secrets committed** (verified via grep + git diff)

### 一键验证

```bash
bash scripts/verify.sh              # backend tests → frontend tests → tsc → build
bash scripts/verify.sh --skip-build # 跳过生产构建
```

四个阶段**串行**执行（8GB 机器上并行会因内存压力假死）。API smoke test
需要先起服务，步骤见上方「启动」章节。

## Roadmap

已完成 V1 → V2 → V3 → V3.1 → V3.2。以下是候选方向，均**未开始**：

**工程侧**
- 把前端显示镜像的参数改为从 API 读取（消除最后一处参数重复）
- 聚合接口的逐建筑分析批量化（当前为 N+1 形态，规模小无感）
- 改造建议持久化（当前实时计算，未落库）

**数据侧**
- 接入真实监测数据格式（CSV / 标准时序协议），替换模拟数据生成器
- 支持多建筑时间轴对齐与横向对比

**AI 侧**
- 多轮对话与上下文管理（Phase 6C 范畴，当前刻意不做）
- 检索质量提升（领域词表 / 同义词扩展）

**明确不做**
- 结构安全鉴定、倒塌预测、自动结构设计、官方标准评分
- 任何把原型参数包装成正式工程标准的表述

## License

Private / Proprietary — 仅限十八个人项目使用。
