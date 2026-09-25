# 19 · Engineering RAG  工程知识检索

> Phase 6B · Engineering Knowledge Base + RAG + Evidence Grounding
> Project-internal knowledge only. No vector DB, no embedding service, no internet.

**文档版本**：v1.0 · Phase 6B (implemented)
**最后更新**：2026-09-16
**状态**：Implemented & tested

---

## 1. 为什么需要这一层

V3 / V3.1 的 AI Assistant 只能解释**本建筑的数据**（BHI / risk / retrofit /
anomaly 都由确定性算法算出）。当用户问「为什么异常会被这样判定」这类
**概念性问题**时，Mock Provider 只能复述数值，Real LLM 只能靠模型自身
的通用知识作答 —— 两者都没有项目内部可引用的依据。

Phase 6B 增加一个**项目自有的工程知识库**，让 AI 的解释可以引用项目内部
写定、经过评审的概念说明。

关键约束：知识库是**背景**，不是**证据**。本建筑的实测数据永远是第一位的。

---

## 2. 范围（严格）

**做：**
- `knowledge/` 目录 + Markdown 知识文档（手写，不发散）
- 确定性 document loading + chunking
- 轻量 lexical retrieval（TF-IDF + cosine，纯 Python 标准库）
- `KnowledgeEvidence` schema
- `AIResponse.knowledge_evidence` 字段
- Engineering Data Context 与 Knowledge Context 分离
- Mock Provider 支持 knowledge evidence
- Real LLM Provider 支持 knowledge context
- Frontend Knowledge Sources 展示
- Prompt injection / security tests
- docs + README + 回归测试

**不做（Phase 6C 及以后）：**
- ✗ Vector DB / embedding service / 语义检索
- ✗ 互联网爬取 / 外部标准引入
- ✗ Conversation / history / multi-turn
- ✗ SSE / streaming
- ✗ Agent / MCP / function calling
- ✗ BIM / GIS / IoT / MQTT
- ✗ 云部署 / 自动结构设计

---

## 3. 知识库内容

位置：`backend/knowledge/`。5 份工程知识文档 + 1 份目录说明。

| 文档 | 主题 | 典型提问 |
|---|---|---|
| `anomaly_detection.md` | Threshold / rate-of-change / z-score 三方法 | "Why was this anomaly flagged?" |
| `health_assessment.md` | BHI 0-100 + 5 维度 + 权重 | "How is BHI computed?" |
| `risk_classification.md` | 4 档分级 + HIGH override 规则 | "Why is this building HighRisk?" |
| `retrofit_decision.md` | RP-v1.0 优先级 + REC-v1.0 规则 | "Why is this retrofit recommended?" |
| `engineering_redlines.md` | 10 条红线 + 强制 disclaimer | "Why does the system refuse to say X?" |
| `README.md` | **目录导航（不索引）** | — |

**不索引 README**：它是知识库自身的说明文档（含 Document Map 表格），
不是工程知识。若索引，短 query 会命中导航表格而非真正的工程内容，
污染 grounding。实现见 `loader.py::SKIP_FILENAMES`。

知识文档自身的纪律（由 `tests/test_rag_redlines.py` 强制扫描）：
- 不含任何国家 / 行业标准编号（GB / JGJ / ISO / ACI / Eurocode）
- 不含具体结构安全限值（如「裂缝 > 0.3 mm 必须立即加固」）
- 不含 AI 输出红线中的禁用短语
- 每份必须含 `Prototype` 字样与 `BuildHealth Internal` 来源声明

知识库**只写概念**，所有数值（BHI 权重、risk 边界、top-k）都留在
`backend/app/analytics/config.py` 与 `retriever.py`，避免文档与代码漂移。

---

## 4. 数据流

```
backend/knowledge/*.md
    │
    ▼  loader.py :: load_knowledge_base()
    │   解析 frontmatter + 首个 # 作为 title + ## sections
    │   跳过隐藏文件 / 非 .md / README.md
    ▼
List[KnowledgeDocument]
    │
    ▼  chunker.py :: chunk_documents()
    │   每个 ## section = 1 chunk; 无 ## 则整篇 = "Full Document"
    ▼
List[KnowledgeChunk]        ← 当前语料: 5 docs → 23 chunks
    │
    ▼  retriever.py :: _TfidfIndex
    │   建 index (df / tf / 每 chunk L2 范数)
    ▼
KnowledgeRetriever.retrieve(query) → top-3 List[KnowledgeEvidence]
    │
    ▼  query_builder.py :: build_retrieval_query(question, ctx)
    │   query = 用户问题 + context 关键词(metric / risk / category / weakest)
    ▼
AIService → provider.generate_summary / generate_answer(knowledge_evidence=...)
    │
    ▼
AIResponse.knowledge_evidence
```

模块：`backend/app/knowledge/`
`__init__.py` · `schemas.py` · `loader.py` · `chunker.py` · `query_builder.py` · `retriever.py`

---

## 5. Chunking 规则（确定性）

`chunker.py` 以 `##` 二级标题切分，**不做语义切分**：

- 每个 `##` section → 一个 `KnowledgeChunk`
- `###` 三级标题视为 section 内容，不再切分
- 文档无 `##` → 整篇作为单个 chunk，`section = "Full Document"`
- 空 section 跳过
- `chunk_id` = `{document_id}::{index}`，或 `{document_id}::full`
- `word_count` = `len(content.split())`

同一份文档每次切分结果完全一致，无随机性，便于测试与 review。

---

## 6. 检索算法（TF-IDF + cosine）

纯 Python 标准库，无 sklearn / numpy / 任何外部依赖。

```
1. tokenize(query) / tokenize(chunk)
2. df(t)  = 含 t 的 chunk 数
3. idf(t) = log((N + 1) / (df(t) + 1)) + 1        # smoothed
4. w(t,d) = tf(t,d) * idf(t)                       # 原始 tf
5. score(q,d) = cosine(w(q), w(d))                 # 各自 L2 归一化
6. 按 score 降序取 top-k, 过滤 score <= 0
```

**Tokenizer**（`retriever.py::_tokenize`）：
- 小写化
- ASCII 词：`[a-z0-9]+`，长度 >= 2（单字母是噪声）
- CJK：**单个汉字即一个有效 token**（长度过滤只作用于 ASCII）
- 两者都过一遍中英停用词表

> CJK 单字保留是 Phase 6B 修复的一个真实缺陷：早期实现统一用
> `len(t) >= 2` 过滤，导致所有单个汉字被丢弃、中文检索恒返回空。

**参数**：`top_k = 3` · `relevance_score` 四舍五入到 4 位并 clamp 到 `[0, 1]`
· 单条 `content` 截断到 300 字符（控制 prompt 体积）。

**为什么不用 embedding**：项目要求离线、确定性、可解释、无外部依赖。
TF-IDF 的每次排序都能用 df/idf 数值解释，便于测试断言；
embedding 会引入模型下载、非确定性浮点与外部服务依赖。

### 6.1 查询增强

`build_retrieval_query(user_question, context)` 在用户问题后追加
EngineeringContext 里的关键词，提升召回：

- sensor 的 metric 名（`crack_width` → `crack width`）
- `risk {level}`（仅当 risk != Normal）
- 前 3 条 retrofit recommendation 的 `category` 与 `issue_type`
- `health.weakest_dimension`

**不修改用户问题的语义**，只做追加。实测效果：

```
Q : "Summarize this building's current engineering status."
EQ: "... status. crack width tilt temperature humidity electricity fire safety"
    → 0.2822 health_assessment.md :: Five Dimensions
      0.1432 retrofit_decision.md :: Recommendation Rules
      0.1334 anomaly_detection.md :: Three Methods Overview
```

---

## 7. KnowledgeEvidence Schema

```python
class KnowledgeEvidence(BaseModel):
    document: str          # "risk_classification.md"
    section: str           # "Four Tiers"
    content: str           # 截断到 300 字符
    relevance_score: float # 0.0-1.0, TF-IDF cosine
    source: str            # "BuildHealth Internal Engineering Notes"
    chunk_id: str          # "risk_classification.md::0"
```

`AIResponse.knowledge_evidence: List[dict]` 承载同一结构。
在 `app/ai/schemas.py` 用宽松 `dict` 而非直接 import
`app.knowledge.schemas`，是为了避免 `app.ai` 对 `app.knowledge`
产生硬依赖（`app.knowledge` 可选加载，缺失时 RAG 优雅降级）。

---

## 8. 优雅降级

RAG **永远不能**让 AI 端点失败：

| 场景 | 行为 |
|---|---|
| `knowledge/` 目录不存在 | `get_default_retriever()` → `None` |
| `knowledge/` 无 `.md` 文件 | `get_default_retriever()` → `None` |
| chunk 列表为空 | `_TfidfIndex = None`，`retrieve()` → `[]` |
| retriever 抛异常 | `AIService._retrieve_knowledge_safe` 吞掉 → `[]` |
| query 全为停用词 | 返回 `[]` |
| 全部 chunk 得分 0 | 返回 `[]` |

`get_ai_service()` 用 try/except 包住 retriever 构造，
任何失败都退化为 `knowledge_retriever=None`，AI 端点照常工作。

---

## 9. 测试

| 文件 | 覆盖 |
|---|---|
| `test_knowledge_loader.py` | frontmatter / title / sections / fallback / 空目录 / 不存在目录 / skip list |
| `test_knowledge_chunker.py` | ## 切分 / 无 ## fallback / chunk_id / word_count |
| `test_knowledge_retriever.py` | 文档数 / chunk 数 / top-k / 排序 / 确定性 / CJK / 空 query / README 排除 |
| `test_knowledge_service.py` | AIService 注入 / summary + ask 带 evidence / 优雅降级 / 无 retriever |
| `test_rag_redlines.py` | RAG 禁词 / 知识文档自检 / standard 编号扫描 / evidence 强制来自输入 |

详见 `21_Phase6_Testing.md`。

---

## 10. 边界声明

- 知识库是 **BuildHealth Internal Engineering Notes**，**不是**任何
  国家 / 行业标准，**不构成**工程鉴定或安全认证。
- 知识文档描述的是 **BuildHealth 原型做了什么**，不是外部权威要求什么。
- 检索结果是**背景解释**，不是本建筑的实测证据。
- 本建筑的数据证据（sensor / anomaly / BHI / risk / retrofit）永远优先。
- AI 不得声称知识文档「证明了」「确认了」本建筑的状况。
- 任何可执行决策都需要**具备资质的专业复核**。

---

## 11. 检索评估集(v1.1 release prep · 2026-09-26)

### 设计

50 条 query,覆盖全部 5 篇知识文档;字面匹配 + 同义改写各 50%;query 长度从 4 字到 30 字;中英文混合。每条 query 都有明确的"期望命中文档" + "期望章节" + "期望关键词"。

- 文件:`backend/scripts/retrieval_eval_set.jsonl`(50 条)
- 评估脚本:`backend/scripts/run_retrieval_eval.py`
- 评估指标:`recall@3` + `MRR` + `median_latency_ms`

### Baseline(M2 Air 8GB,本地运行,TF-IDF 默认 top_k=3)

| Metric | Value |
|---|---|
| n_queries | 50 |
| n_hits | 23 / 50 |
| **recall@3** | **0.46** |
| **MRR** | **0.3767** |
| median_latency_ms | 0.025 |

### 解读

- 46% 命中率符合"小语料 + 简单 TF-IDF + CJK 单字切分"的预期,不是 bug
- 27 条 miss 主要集中在三类:
  1. 中文短查询(如"4 档风险分级" → "四档风险分级"同义改写)
  2. 概念性查询(如"BHI 是什么"、"系统不做什么")
  3. 含禁词的查询触发回避路径
- 后续优化方向(若启动,见 ROADMAP "AI 侧"候选):
  - jieba 二元组切分(中文字段粒度提升)
  - 同义词扩展(领域词表)
  - query expansion(把"BHI 是什么"扩成"Building Health Index 是什么 评分")

### 复跑命令

```bash
cd backend
./venv/bin/python -m scripts.run_retrieval_eval
# 或加 --top-k 5 / --eval-set <其他 jsonl>
```

### 与新阶段的衔接

若 Phase 4 优化检索质量(分词 / 同义词 / query expansion),用同一份 `retrieval_eval_set.jsonl` 重跑;新数字追加到本节末尾,前后对比可证明优化方向是否有效。

设计参考:`BuildHealth-prep-notes/34_Retrieval_Eval_Set_Draft.md`。
