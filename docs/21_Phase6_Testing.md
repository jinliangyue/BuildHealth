# 21 · Phase 6 Testing  Phase 6A + 6B 测试策略

> Phase 6A · Real LLM Provider 测试覆盖
> Phase 6B · Engineering Knowledge RAG + Grounding 测试覆盖

**文档版本**：v1.0 · Phase 6A + 6B
**最后更新**：2026-09-16
**状态**：Implemented & tested

---

## 1. 测试目标

- **V1+V2+V3 回归**: 278 个 backend tests + 60 个 frontend tests 必须全部继续通过
- **V6A 新增**: 至少 40 个 backend tests + 5 个 frontend tests
- **V6B 新增**: RAG loader / chunker / retriever / service + grounding 安全测试
- **Real Provider mock 友好**: 不真实调用外部 API, 用 `unittest.mock` 模拟 httpx
- **Mock Mode 不退化**: 所有 V1+V2+V3 测试零修改全保留

### 1.1 Phase 6B 新增测试总览 (backend 50 · frontend 13)

| 文件 | 测试数 | 主题 |
|---|---|---|
| `test_knowledge_loader.py` | 9 | frontmatter / title / section / fallback / 空目录 / 不存在目录 / skip list |
| `test_knowledge_chunker.py` | 5 | `##` 切分 / 无 `##` fallback / chunk_id / word_count |
| `test_knowledge_retriever.py` | 13 | 文档数 / chunk 数 / top-k / 排序 / 确定性 / CJK / 空 query / README 排除 |
| `test_knowledge_service.py` | 6 | AIService 注入 / summary + ask 带 evidence / 优雅降级 / 无 retriever |
| `test_rag_redlines.py` | 17 | RAG 禁词 / 语料自检 / 标准编号扫描 / evidence 强制来自输入 |
| **backend 小计** | **50** | |
| `KnowledgeEvidenceList.test.tsx` | 7 | 空态 / 渲染 / 百分比 / 边界分数 / 安全提示语 |
| `AIResponsePanel.test.tsx` (扩展) | +6 | Knowledge Sources 分区 / 与 Evidence 分离 / 旧后端兼容 |
| **frontend 小计** | **13** | |

---

## 2. Backend 测试 (371 total)

### V1+V2+V3 保留 (278 tests)

零修改. Phase 6A / 6B 的改动都隔离在 `app/ai/` · `app/knowledge/` 和
`app/api/ai.py` 范围.

### V6A 新增 (43 tests · 3 文件)

| 文件 | 测试数 | 主题 |
|---|---|---|
| test_real_provider.py | ~30 | OpenAICompatibleProvider 全部方法 (mock httpx) |
| test_ai_provider_factory.py | 10 | env-based 4 路径 + singleton + config |
| test_ai_api.py (扩展) | 3 | misconfigured 503 + health 200 显式 provider_not_configured |

### V6B 新增 (50 tests · 5 文件)

见 §1.1 总览, 详细策略见 §9.

**Backend 总计: 371 tests**

---

## 3. Frontend 测试 (78 total)

### V1+V2+V3 保留 (60 tests)

零修改. Phase 6A 的改动只新增 ProviderBadge 子组件, 不影响现有页面渲染.

### V6A 新增 (5 tests · 1 文件)

| 文件 | 测试数 | 主题 |
|---|---|---|
| AIProviderStatus.test.tsx | 5 | Mock Mode / Live AI / Not Configured 3 mode + precedence + 未来 provider |

### V6B 新增 (13 tests · 1 新文件 + 1 扩展)

| 文件 | 测试数 | 主题 |
|---|---|---|
| KnowledgeEvidenceList.test.tsx | 7 | 空态 / 渲染 / relevance 百分比 / 越界 clamp / 非权威提示语 / 多 chunk |
| AIResponsePanel.test.tsx (扩展) | +6 | Knowledge Sources 分区 / 与 Evidence 分离 / 空态 / 旧后端缺字段兼容 |

**Frontend 总计: 78 tests** (60 V1+V2+V3 + 5 V6A + 13 V6B)

---

## 4. Real Provider 测试策略

**核心原则**: 不真实调用任何 LLM. 全部用 `unittest.mock` 模拟 httpx.

### 4.1 构造校验 (3 tests)
- 缺 api_key → ValueError
- 缺 base_url → ValueError
- 末尾 `/` 去除

### 4.2 health_check (5 tests)
- 200 → "ok"
- 401 → "provider_error" + 401 in message
- 403 → "provider_error" + 403
- httpx.TimeoutException → "provider_error" + "timeout"
- httpx.ConnectError → "provider_error"

### 4.3 _call_chat (9 tests)
- 200 正常 → 返回 content
- 401 → AIProviderError("auth_error")
- 429 → AIProviderError("rate_limit")
- 500 → AIProviderError("provider_error")
- 400 → AIProviderError("client_error")
- httpx.TimeoutException → AIProviderError("timeout")
- httpx.HTTPError → AIProviderError("network_error")
- 非 JSON 响应 → AIProviderError("malformed_response")
- 缺 choices → AIProviderError("malformed_response")

### 4.4 _parse_response (~10 tests)
- 正常 JSON → AIResponse (provider="openai-compatible", disclaimer=AI_DISCLAIMER)
- 非 JSON → AIProviderError
- 非 dict → AIProviderError
- 含 ```json``` 围栏 → 正确解析
- 缺 key_findings / actions / evidence → 空 list
- 缺 evidence → 回退到 context.evidence_chain[:5] (grounding)
- severity 不合法 → "info"
- urgency 不合法 → "low"
- answer 含禁词 → AIProviderError("safety_violation")
- key_finding 含禁词 → AIProviderError("safety_violation")
- LLM 的 disclaimer 被强制覆盖

### 4.5 End-to-end (2 tests)
- generate_summary (mock httpx) → 完整 AIResponse
- generate_answer (mock httpx) → 完整 AIResponse
- 验证 response_format={"type": "json_object"} 传给 LLM

---

## 5. Provider Factory 测试

### 5.1 Env 路径 (4 tests)
- `AI_PROVIDER=mock` → MockProvider
- `AI_PROVIDER=openai-compatible` + 完整 config → OpenAICompatibleProvider
- `AI_PROVIDER=openai-compatible` + 缺 AI_API_KEY → _MisconfiguredProvider
- `AI_PROVIDER=openai-compatible` + 缺 AI_BASE_URL → _MisconfiguredProvider
- `AI_PROVIDER=unknown` → MockProvider (降级)

### 5.2 Singleton (2 tests)
- 同一 env → 同一 instance
- `reset_ai_provider()` 清理 singleton

### 5.3 Misconfigured 行为 (1 test)
- `_MisconfiguredProvider.generate_summary()` → AIProviderError("config_error")

### 5.4 Config 传递 (1 test)
- `AI_REQUEST_TIMEOUT=45` / `AI_MAX_TOKENS=2000` / `AI_TEMPERATURE=0.5` → provider 字段正确

### 5.5 关键设计: `get_ai_provider()` 每次调用读 env

`monkeypatch.setenv` 必须生效. 通过在 `provider_factory.py` 中用 `os.getenv()` 而非 import from `config` 实现.

---

## 6. API Misconfigured 测试

### 6.1 503 端点 (2 tests)
- `POST /api/ai/buildings/{id}/summary` 在 `AI_PROVIDER=openai-compatible` + 缺 key → 503 + body detail.provider_error="config_error"
- `POST /api/ai/buildings/{id}/ask` → 同样 503

### 6.2 health 端点 (1 test)
- `GET /api/ai/health` → 200 + body status="provider_not_configured" (HTTP 200 是故意的, health 端点总是 200)

---

## 7. Frontend ProviderBadge 测试

5 个测试覆盖:
- mock + status=ok → "Mock Mode" (data-mode="mock")
- openai-compatible + status=ok → "Live AI · openai-compatible" (data-mode="live")
- openai-compatible + status=provider_not_configured → "Not Configured" (data-mode="misconfigured")
- provider_not_configured 优先级最高
- 未知 provider → 仍 "live" + 显示 provider 名

---

## 8. 回归保护

- V1 76 tests 不能动
- V2 123 tests 不能动
- V3 79 tests 不能动
- `AI_FORBIDDEN_PHRASES` 列表 (redlines.py) 与 V3 test_ai_redlines.py 完全一致 (V1 test_engineering_redlines.py 排除 redlines.py 文件本身)

---

## 9. Phase 6B 测试策略

### 9.1 核心原则

- **全部离线**: 不联网, 不调外部 API, 不下载模型
- **全部确定性**: TF-IDF 无随机性, 同一 query 必得同一结果
- **临时语料**: loader / chunker / retriever 测试用 `tmp_path` 构造小语料,
  不依赖 `backend/knowledge/` 的真实内容 (真实内容另有专门测试)
- **真实语料单独验证**: `test_get_default_retriever_loads_project_kb` 断言
  实际 5 篇文档被加载

### 9.2 Loader (9 tests)

| 测试 | 断言 |
|---|---|
| frontmatter 解析 | `<!-- key: value -->` 被剥离, source 被读取 |
| title 提取 | 首个 `#` 作为 title |
| section 提取 | `##` 存入 full_text, 供 chunker 使用 |
| 无 `#` fallback | 用 filename 转 title (`no_frontmatter_no_h1` → `No Frontmatter No H1`) |
| 空目录 | 返回 `[]` |
| 不存在目录 | 返回 `[]`, 不抛异常 |
| **README 不索引** | `README.md` 被跳过, 其他 `.md` 正常加载 |

### 9.3 Chunker (5 tests)

`##` 边界切分 · 无 `##` → 单个 `Full Document` chunk · `chunk_id` 格式
(`{doc}::{idx}` / `{doc}::full`) · `word_count` · 空 section 跳过.

### 9.4 Retriever (13 tests)

| 测试 | 断言 |
|---|---|
| 文档 / chunk 计数 | 3 docs → 5 chunks (sections 求和) |
| top-k | 最多返回 `top_k` 条 |
| 排序 | `relevance_score` 降序 |
| 相关性 | "crack width threshold" 命中 `anomaly.md :: Threshold` |
| 无关语料 | 得分 0 的 chunk 不返回 |
| score 范围 | `0 <= relevance_score <= 1` |
| 确定性 | 同一 query 多次结果完全一致 |
| **CJK** | 中文 query 能命中中文 chunk (单字 token 保留) |
| 空 query / 全停用词 | 返回 `[]` |
| 空语料 | `_index = None`, `retrieve()` → `[]` |
| **README 排除** | 真实语料检索不命中 `README.md` |
| 真实语料 | 5 篇文档全部加载, chunk 数 > 0 |

### 9.5 Service 集成 (6 tests)

| 测试 | 断言 |
|---|---|
| `build_retrieval_query` | 含用户问题 + metric + risk + category + weakest |
| Normal risk | 不注入 risk 关键词 |
| summary 注入 | `get_ai_service().knowledge_retriever is not None` |
| summary 字段 | `response.knowledge_evidence` 是 list |
| ask 字段 | 同上 |
| **优雅降级** | retriever 抛 `RuntimeError` → `knowledge_evidence == []`, service 不崩 |
| **无 retriever** | `knowledge_retriever = None` → `knowledge_evidence == []` |

### 9.6 RAG 安全 (17 tests) · `test_rag_redlines.py`

这是 Phase 6B 最关键的一组测试。

| 测试 | 断言 |
|---|---|
| `test_rag_forbidden_in_phrase_list` | 11 条 RAG 禁词全部在 `AI_FORBIDDEN_PHRASES` 中 (parametrized) |
| `test_scan_response_catches_knowledge_proves` | "the knowledge document proves …" 被抓 |
| `test_scan_response_catches_knowledge_certifies` | "building is certified based on knowledge" 被抓 |
| `test_scan_response_no_false_positive_on_benign_use` | 正常提及 knowledge 不误报 |
| **`test_knowledge_documents_contain_no_self_referential_violations`** | **语料不得含任一禁词 (无例外)** |
| **`test_knowledge_documents_no_national_standard_numbers`** | **不得含 GB/T · JGJ · ISO · ACI 318 · Eurocode** |
| `test_knowledge_documents_have_prototype_disclaimer` | 每篇必须含 `Prototype` |
| `test_knowledge_documents_have_source_label` | 每篇必须含 `BuildHealth Internal` |
| **`test_ai_response_evidence_and_knowledge_evidence_are_distinct_fields`** | **两个 evidence 字段永不合并** |
| **`test_real_provider_knowledge_evidence_forced_from_input`** | **LLM 伪造的 knowledge_evidence 被丢弃, 只用检索输入** |

> 语料扫描**不设例外**: 连 `engineering_redlines.md`(描述红线的文档)
> 也不得字面包含禁词, 用描述性措辞代替直接引用.
> 这样语料永远不能成为禁词的载体.

### 9.7 前端 (13 tests)

| 文件 | 测试 | 断言 |
|---|---|---|
| `KnowledgeEvidenceList.test.tsx` | 7 | 空态 / document + section + content 渲染 / source 标签 / 百分比 (42%) / 越界分数 clamp (100% · 0%) / 非权威提示语 / 多 chunk |
| `AIResponsePanel.test.tsx` | +6 | Knowledge Sources 与 Evidence 同时存在且为独立分区 / 百分比 / 非本建筑提示 / 空时不渲染分区 / Evidence 仍可见 / `knowledge_evidence` 缺失时旧后端兼容不崩 |

### 9.8 Phase 6B 发现并修复的缺陷

| 缺陷 | 影响 | 修复 |
|---|---|---|
| `_tokenize` 统一 `len(t) >= 2` 过滤 | 单个汉字被丢弃 → **中文检索恒返回空** | CJK 单字保留, 长度过滤只作用于 ASCII |
| `README.md` 被索引 | Document Map 表格抢占 retrieval 位次 (实测 BHI query 中被 README 排第一) | `SKIP_FILENAMES` 排除 |
| `full_building` fixture 定义在 `test_ai_service.py` | 跨模块不可见 → `test_knowledge_service.py` 4 个测试 error | 上移到 `conftest.py` |
| `engineering_redlines.md` 字面含 4 条禁词 | 语料自检失败 | 改为描述性措辞 |
| `test_rag_redlines.py` 缺 `datetime` import | 2 个测试 NameError | 补 import |

---

## 10. Phase 6B 最终验收结果 (2026-09-16)

| 项目 | 命令 | 结果 |
|---|---|---|
| Backend 全量 | `python -m pytest tests/ -q` | 371 passed |
| Frontend 全量 | `npm test -- --run` | 12 files / 78 passed |
| TypeScript | `tsc` (经 `npm run build`) | 0 errors |
| Production build | `npm run build` | ✓ 714 modules · 1350.86 kB / 441.46 kB gzip · 2.33s |
| API smoke test | uvicorn + curl | 全部 14 端点 200 |

Phase 6B 新增测试合计: backend 50 + frontend 13 = 63.

### 10.1 验收过程中修复的环境问题

首次执行前端测试时 jsdom 无法加载 (`Class extends value undefined`，伴随
circular dependency 警告，每次报错文件不同)。排查结论: `node_modules`
安装不完整/不一致，与 Phase 6B 代码无关。

修复方式: `npm ci` (严格按 `package-lock.json` 重建，未升级依赖、未修改
锁文件)。重建后 jsdom 正常加载，前端 78 tests 全绿。

同时确认该状态下 build 耗时从 5m58s 恢复到 2.33s，产物 hash 前后一致
(`index-0qCZOQxZ.js`)，说明先前在资源紧张时产出的 build 结果同样有效。

---

**文档版本**：v1.1 · Phase 6A + 6B
**最后更新**：2026-09-16
**状态**：Implemented & tested · 验收通过
