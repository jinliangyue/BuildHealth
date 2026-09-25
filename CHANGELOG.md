# BuildHealth · Changelog

> 项目冻结于 commit `ef095b5`(2026-09-17)。
> 本文件记录决策依据与冻结原因,不是迭代日志。

---

## 2026-09-17 · 冻结公开仓库(commit ef095b5)

**决策**:把仓库变成"公开叙事版本",移出所有个人求职准备材料。

**做了什么**:
- 创建 `BuildHealth-prep-notes/` 桌面文件夹(仓库外,个人材料)
- 仓库 commit 历史保留全部旧 commit(包括含 prep-notes 的旧版本),不重写
- README 改写为英文版(工程叙事优先,中文版保留在 prep-notes `33_README_Chinese.md`)

**为什么冻结**:
- 项目达到求职用展示态:V1 + V2 + V3 + V3.1 + V3.2 全部完成,两轮工程强化
- 不希望继续叠加未审阅的功能到公开仓库
- 求职准备材料(19 份文档 + 5 大类问题清单)与工程代码分离,各自独立维护

**冻结不等于废弃**:
- 候选改进方向见 `ROADMAP.md` 候选下一步
- 任何后续改进单独走"v1.1 release"流程,不直接改 main

---

## 2026-09-13 → 2026-09-17 · Sprint 3 最终优化(commit 19e2125)

**做了**:
- 请求作用域 `BuildingAnalysis` 对象,消除 AI context 路径的重复异常检测
- 等价性测试 11 条覆盖新旧路径
- 变异测试验证守卫本身能失败
- 跨语言参数一致性测试(用 classify_risk / map_priority_level 行为探针)

**数字**(本地基准,M2 Air 8GB / SQLite / 3 栋 / 1350 条记录,5 次中位):
- AI context build:queries 16 → 7,anomaly calls 2 → 1,median 59.0 → 31.5 ms(约 47%)
- retrofit overview:queries 64 → 6
- dashboard summary:queries 28 → 7
- buildings overview:queries 22 → 4

**没改**:
- 算法逻辑(BHI 权重 / 风险边界 / 阈值)
- API 契约
- 数据库 schema

---

## 2026-09-08 → 2026-09-13 · Sprint 2 N+1 优化(commit 80f1c6c, 03114a4)

**做了**:
- SQLAlchemy `before_cursor_execute` 监听器量化查询数
- 批量读取消除 N+1(监测序列被读 3 次、最新评估被查 2 次、传感器逐个查)
- 聚合等价性测试 12 条
- `docs/24` Sprint 2 记录文档

**数字**(同基准):
- retrofit overview:64 → 13 queries
- 跨 endpoint 共享分析(Sprint 3 才落地)

---

## 2026-08-29 → 2026-09-08 · Sprint 1 工程质量审计(commit 5d679a0)

**做了**:
- 类型 / API 错误处理 / 文档完备性审计
- 测试缺口定位 + 补齐
- `docs/22` Sprint 1 记录文档

**没做**:
- 性能优化(留给 Sprint 2 / 3)
- AI 路径改进(留给 Phase 6A / 6B)

---

## 2026-09-07 → 2026-09-08 · Phase 6B Knowledge RAG(commit f27f6f7)

**做了**:
- 5 篇工程知识 Markdown(`backend/knowledge/`)
- `KnowledgeRetriever`:TF-IDF + cosine,纯标准库
- `AIResponse.knowledge_evidence` 与 `evidence` 字段分离
- prompt 两个独立 key(engineering / knowledge)
- 前端 Knowledge Sources 分区(配色与 Evidence 不同)
- 11 条 RAG 专项红线 + 语料自检(无标准编号)

**没做**:
- Conversation(留给 Phase 6C)
- Vector DB / embedding(不在路线内)
- 真实工程标准知识(语料只是项目自身概念)

---

## 2026-08-23 → 2026-09-07 · Phase 6A Real LLM Provider(commit 068dcba)

**做了**:
- OpenAICompatibleProvider(纯 httpx,无 SDK)
- 失败处理:timeout / 401 / 403 / 429 / 5xx / malformed JSON
- Pydantic schema 校验 + 43 条禁词扫描
- 服务端强制 disclaimer(覆盖 LLM 自己返回的)
- _MisconfiguredProvider 显式降级(503 + structured body)
- ProviderBadge(Mock Mode / Live AI / Not Configured)

**风险控制**:
- 默认仍是 Mock provider(整个测试套件跑在 Mock 上)
- 真实 LLM 仅作为可选,需环境变量显式开启

---

## 2026-08-15 → 2026-08-23 · Phase 5 AI Assistant(commit e1ac5f7)

**做了**:
- MockProvider V3(确定性 / 离线 / 5 个 quick question)
- EngineeringContext 类型化上下文
- AIResponse 结构化输出
- `/ai-assistant` 页面

**关键约束**:
- AI 不能算 / 改 / 下结论(单向数据流)
- 43 条禁词扫描两端(Mock + Real)走同一闸门

---

## 2026-08-08 → 2026-08-15 · Phase 4 Retrofit Decision(commit 76a1526)

**做了**:
- RP-v1.0 改造优先级(5 个加权子分)
- REC-v1.0 规则引擎(5 条规则)
- 证据链:每条建议可回溯
- `/retrofit` 页面 + 3 个新 API

**没做**:
- 建议持久化(`retrofit_recommendations` 表保留但未使用)
- 真实造价数据

---

## 2026-08-01 → 2026-08-08 · Phase 1-3 V1 核心(commit 84b781a, b481088, 4b87faf)

**做了**:
- 监测数据模型 + 异常检测 + BHI + 风险分级
- 6 个仪表盘页面 + 9 个 API
- 412 个后端测试 / 97 个前端测试

**没做**:
- 改造决策
- AI 解释

---

## 2026-07-XX · Phase 0 初始化(commit 0bd52d1)

**做了**:
- 项目定位 + 架构设计
- 工程真实性 10 条红线(`docs/02`)
- 数据模型初稿

---

## 决策记录(非时间序)

- **AI 不参与工程计算**:从 Phase 5 开始,所有工程数值由确定性算法产出,AI 只读不写。原因:可复现 / 可审计 / 责任边界。
- **参数版本化**:BHI-v1.0 / RP-v1.0 / REC-v1.0 / RISK-v1.0 / ANOM-v1.0 / AI-v1.0 各自带版本号,响应里可见。
- **参数明确标注为 Prototype**:从 docs/02 开始,所有展示处都说明"非国家标准 / 行业标准"。
- **Mock provider 是默认**:测试可重现 + 离线运行 + 无外部依赖。
- **不用 LangChain / Anthropic SDK**:安全路径必须能逐行推理,框架会遮蔽。
- **不接向量库**:语料 23 chunk,TF-IDF 即可,向量检索不会提升质量。
- **不接真实工程标准**:知识库只描述项目自身概念,避免"标准权威"误用。

---

## 2026-09-26 · v1.1 release prep(5 个 commit,基于 ef095b5)

**目标**:把仓库演化为"对外可发布"形态,同时保持工程叙事的纯度。

### Commit 列表

- `ef82070` — `docs: add CHANGELOG.md`
- `a9adcf6` — `docs: add engineering review Q&A + sync 28 baseline to ef095b5`
- `c642e8a` — `docs: add ROADMAP.md for external integrators`
- `c0408b2` — `eval: add RAG retrieval evaluation set + runner + docs/19 §11`
- `84f1563` — `feat(ai): mock provider answer cites knowledge evidence`
- 待 commit — `data: scale seed 3 → 30 buildings + sync all docs`

### 做了什么

#### 文档类
- 新增根目录 `CHANGELOG.md`(本文件,记录决策依据而非迭代日志)
- 新增 `docs/29_Engineering_Review_QA.md`(结构/检测工程师咨询问题清单,伦理底线明示)
- 新增根目录 `ROADMAP.md`(对外发布视角,与 `docs/09_Version_Roadmap.md` 内部演进路线分工)
- `docs/28_Project_Fact_Sheet.md` §1 baseline 字段 62d21e4 → ef095b5,version v1.0 → v1.1
- `docs/19_Engineering_RAG.md` 末尾新增 §11 检索评估集章节

#### 评估/脚本类
- 新增 `backend/scripts/retrieval_eval_set.jsonl`(50 条 query 覆盖 5 篇知识文档)
- 新增 `backend/scripts/run_retrieval_eval.py`(计算 recall@3 + MRR + median latency)
- **baseline 数字**:M2 Air 8GB / TF-IDF top_k=3 / **recall@3 = 0.46 / MRR = 0.3767 / 23 of 50 hits / 0.025 ms 中位延迟**

#### 代码类
- `backend/app/ai/mock_provider.py` 新增 `_format_knowledge_citation()` helper,把检索到的 knowledge_evidence 编织进 answer 文本(此前只在响应字段里)
- 引用前缀固定 `"Per the platform's documented engineering notes..."`,避免被读成"本建筑情况"
- 4 个 explain path(summary / risk / retrofit / anomaly)全部接入
- 自检:如果 citation 自身触发禁词扫描,降级为空字符串(避免 _guard_safety 抛 safety_violation)
- 新增 4 个测试(全部通过):有 knowledge 时引用 / 无 knowledge 时无引用 / 4 路径全部接入 / 自检降级

#### 数据规模
- `backend/scripts/seed_data.py` 把种子数据从 **3 栋 / 15 传感器 / 1350 记录**扩到 **30 栋 / 150 传感器 / 27000 记录**(×10 / ×30)
- 保留 `random.seed(42)` / `quality_flag="simulated"` / `wipe_database`
- 3 种 profile(healthy / attention / abnormal)1:1:1 比例大致保持
- 不动 `generate_timeseries` 函数体
- 新基准:`docs/27_Overnight_Sprint_3_Final.md` §附 + `docs/28_Project_Fact_Sheet.md` §17
- **关键观察**:10× 建筑 + 20× 记录下,所有 queries / anomaly_calls 数字均不变 — "查询数不随建筑数增长"承诺被直接验证

### 没做

- 不创建 GitHub remote / 不 push(仓库保持本地)
- 不重写 git 历史(ef095b5 之前所有 commit 保留)
- 不动 docs/01-27 现有内容(29 cp 进 29 之后序号连续)
- 不启动 39 工程师访谈(等用户后续安排咨询对象)
- 不引入新依赖(38 Mock 重构只用现有 imports)

### 测试

- **416 backend tests passed**(412 baseline + 4 new knowledge-citation tests)
- **97 frontend tests passed**(无变化)
- TypeScript 0 errors
- verify.sh ALL CHECKS PASSED

### Release tag

(待用户确认后)`v1.1.0` tag 打在本 commit 上。
