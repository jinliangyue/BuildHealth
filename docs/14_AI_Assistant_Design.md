# 14 · AI Engineering Assistant Design  AI 助手设计

> AI Engineering Assistant / Engineering Knowledge Assistant 设计文档
> Phase 5 V3 最后一层 · 解释层 / 知识助手

**文档版本**：v0.1 · Phase 5 V3
**最后更新**：2026-09-15
**状态**：Implemented & tested

---

## 1. 背景

V1 + V2 已形成完整数据链路:

```
Monitoring → Anomaly Detection → BHI → Risk → Retrofit Recommendation → Priority
```

但所有输出都是结构化数字 + 简短 explanation. 工程人员仍然需要解释层来理解:

- 这栋建筑目前健康状况如何?
- 为什么被判定为 High Risk?
- 为什么推荐这个改造建议?
- 工程师下一步该看什么?

V3 引入 AI Engineering Assistant, 专门解决"解释"需求.

---

## 2. 定位

### BuildHealth AI 不是:

- 自动结构设计软件
- 自动安全鉴定系统
- AI 加固设计生成器
- 工程师替代品
- 自动修改工程数据
- 给出最终安全结论的工具

### BuildHealth AI 是:

- **Engineering Decision Support** (工程决策支持)
- **Engineering Knowledge Assistant** (工程知识助手)
- 解释层 / 说明层 / 知识查询助手

### AI 可以:

- 总结已有数据
- 解释 BHI / Risk / Priority 来源
- 解释为什么推荐某个改造
- 整理 next action 摘要
- 引用 evidence chain

### AI 不能:

- 重新计算 BHI / Risk / Priority
- 编造不存在的传感器 / 异常
- 声称完成专业工程鉴定
- 声称符合国家或行业标准
- 自动设计加固方案
- 替代结构工程师
- 修改任何工程数据

---

## 3. 架构

```
┌─────────────────────────────────────────────┐
│  Frontend (/ai-assistant)                    │
│  - QuickQuestions · Free-form · Evidence     │
└──────────────────┬──────────────────────────┘
                   │ POST /api/ai/buildings/{id}/{summary|ask}
                   │ GET  /api/ai/health
                   ▼
┌─────────────────────────────────────────────┐
│  FastAPI Router (app/api/ai.py)              │
└──────────────────┬──────────────────────────┘
                   ▼
┌─────────────────────────────────────────────┐
│  AI Service (app/ai/service.py)              │
│  - 编排: Provider + Context Builder          │
└──────────┬───────────────────┬──────────────┘
           ▼                   ▼
┌──────────────────┐  ┌─────────────────────────┐
│ Context Builder  │  │ AI Provider              │
│ (context_builder │  │ (provider.py · Protocol)│
│  .py)            │  │                          │
│                  │  │  - MockProvider (default)│
│ 读取 V1/V2 service│  │  - (future) OpenAI       │
│ 不重算任何指标    │  │  - (future) Anthropic    │
└──────────────────┘  └─────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────┐
│  V1 / V2 已有 services (零修改)               │
│  - assessment.run_anomaly_detection           │
│  - assessment.compute_health_assessment       │
│  - assessment.classify_risk_for_building      │
│  - retrofit_service.get_retrofit_decision     │
└──────────────────────────────────────────────┘
```

---

## 4. Provider 抽象

```python
class AIProvider(Protocol):
    name: str
    model: str

    def health_check(self) -> AIHealthStatus
    def generate_summary(self, context: EngineeringContext) -> AIResponse
    def generate_answer(
        self, context: EngineeringContext, question: str
    ) -> AIResponse
```

### Mock Provider (默认)

- 完全确定性
- 不调用任何真实 LLM API
- 基于 context 直接生成结构化响应
- 5 个问题模式 (关键词路由): 总结/风险/改造/异常/default
- 所有数字从 context 读, 不编造
- answer / disclaimer 强制受控 (避免越界)

### 真实 LLM Provider (Phase 6+ 计划)

预留 protocol, 不实现. Phase 6+ 可加:

- `OpenAIProvider(AIProvider)` — 通过 httpx 调用 OpenAI Chat Completions
- `AnthropicProvider(AIProvider)` — 通过 httpx 调用 Anthropic Messages API
- 通过 `AI_PROVIDER` 环境变量选择

### Provider 切换

```python
def get_ai_provider() -> AIProvider:
    global _provider_instance
    if _provider_instance is None:
        if AI_PROVIDER == "mock":
            _provider_instance = MockProvider()
        else:
            # 真实 provider 未实现 → 降级到 mock
            _provider_instance = MockProvider()
    return _provider_instance
```

---

## 5. AI Response 结构

```python
class AIResponse(BaseModel):
    answer: str                              # 3-5 段文字回答
    key_findings: List[AIKeyFinding]         # 结构化要点
    evidence: List[AIEvidenceRef]            # 证据链 (可点击)
    recommended_actions: List[...Action]     # 建议下一步
    disclaimer: str                          # 强制
    provider: str                            # "mock" 显式标识
    model: str
    calculation_version: str                 # "AI-v1.0"
    created_at: datetime
```

### Evidence Chain

每条 evidence 含:

- `source_type`: building | sensor | anomaly | health | risk | retrofit_recommendation | engineering_note
- `source_id`: 整数 ID (可点击跳转)
- `metric`: 关联 metric
- `description`: 简短描述
- `reference_path`: `/api/buildings/1/health` 等可点击 URL

前端 EvidenceList 自动把 `/api/buildings/{id}/...` 转为内部路由 `/buildings/{id}/...`.

---

## 6. 已知限制

- **不接真实 LLM** — 当前仅 Mock, 适合本地开发/演示/GitHub 展示
- **不持久化 chat history** — 每次 ask 独立
- **不支持流式响应** — 一次性返回完整 AIResponse
- **不支持多轮对话** — 每个 question 独立处理
- **不支持 i18n** — 当前仅英文/中文混排
- **不接 RAG / Vector DB** — 仅基于当前 context
- **不修改任何 V1/V2 数据** — 完全只读

---

## 7. 与 V1/V2 关系

| 组件 | V1 | V2 | V3 |
|---|---|---|---|
| Monitoring | ✓ | 复用 | 复用 |
| Anomaly Detection | ✓ | 复用 | 复用 |
| BHI | ✓ | 复用 | 复用 |
| Risk Classification | ✓ | 复用 | 复用 |
| Recommendation | — | ✓ | 复用 |
| Priority Score | — | ✓ | 复用 |
| AI Explanation | — | — | **NEW** |
| Engineering Notes | — | ✓ | 复用 |

V3 是 V1/V2 之上的纯增量, **不**修改任何 V1/V2 业务逻辑.

---

## 8. 未来扩展路径 (Phase 6+)

Phase 5 仅实现 provider 抽象 + Mock. 未来可加:

- `OpenAIProvider` (gpt-4o / gpt-4-turbo)
- `AnthropicProvider` (claude-3.5-sonnet)
- Gemini / Cohere 等
- 本地模型 (Ollama)
- 流式响应 (SSE)
- 多轮对话 (chat session)
- RAG 接入工程文档
- Function calling (查询具体 API)

接入方式 (Phase 6+):
1. 在 `app/ai/` 加 `openai_provider.py` 等
2. 实现 `AIProvider` protocol
3. 在 `get_ai_provider()` 添加分支
4. 通过环境变量 `AI_PROVIDER=openai` + `AI_API_KEY=...` 启用
5. .env.example 文档化

---

**文档版本**：v0.1 · Phase 5 V3
**最后更新**：2026-09-15
**状态**：Implemented & tested
