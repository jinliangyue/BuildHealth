# BuildHealth · Roadmap

> **范围**:本文件面向**外部集成方 / 潜在使用者**,列出已完成 / 明确不做 / 候选下一步三块。
>
> **范围分工**(避免重复):
> - 项目**内部阶段路线**:见 `docs/09_Version_Roadmap.md`
> - **事实基线 + 限制清单**:见 `docs/28_Project_Fact_Sheet.md` §22
> - **本文件(ROADMAP.md)**:对外视角,讲"我们做完了什么 / 坚决不做什么 / 下一步候选(均未启动)"
>
> 当前状态:Phase 6B 完成(2026-09-17 冻结于 commit ef095b5)。
> 本文件列出已完成、明确不做、候选下一步三个区域。

---

## 已完成 · Phase 1 → Phase 6B

### V1 · 核心监测 + 异常检测 + 健康评估(Phase 1-3)

- 建筑 / 构件 / 传感器 / 监测记录四层数据模型(SQLite,8 表)
- 3 种并行异常检测:阈值 / 变化率双门限 / 7 天滚动 Z-score,按 (sensor, metric, method, severity) 去重
- 5 维度加权 BHI(0.40 / 0.20 / 0.15 / 0.10 / 0.15),权重和运行时断言为 1.0
- 4 档风险分级(Normal ≥ 90 / Attention ≥ 75 / Abnormal ≥ 60 / HighRisk < 60)+ HIGH 异常覆盖规则
- 6 个仪表盘页面 + 9 个 API 端点

### V2 · 改造决策支持(Phase 4)

- RP-v1.0 改造优先级(5 个加权子分)
- REC-v1.0 规则引擎(5 条规则)
- 证据链:每条建议可回溯到传感器与原始记录
- 3 个新 API + `/retrofit` 页面

### V3 · AI 工程助手(Phase 5)

- Mock Provider(确定性,离线,完全可测)
- EngineeringContext 类型化上下文
- AIResponse 结构化输出(answer + key_findings + evidence + disclaimer)
- 5 个 quick question + AI Assistant 页面

### V3.1 · Real LLM Provider(Phase 6A)

- OpenAI-compatible provider(纯 httpx,无 SDK)
- 失败处理:timeout / 401 / 403 / 429 / 5xx / malformed JSON
- Pydantic schema 校验 + 43 条禁词扫描
- 服务端强制 disclaimer(覆盖 LLM 自己返回的)
- _MisconfiguredProvider 显式降级

### V3.2 · 工程知识 RAG + Evidence Grounding(Phase 6B)

- 项目自有知识库(5 篇 Markdown → 23 个 chunk)
- TF-IDF + cosine 检索(top-3,标准库实现)
- 工程证据 / 知识证据三层分离(schema / prompt / UI)
- RAG 专项 11 条红线 + 知识库语料自检
- 优雅降级(retriever 缺失或异常 → RAG 关闭,AI 端点照常)

### 工程强化 · Overnight Sprint 1-3

- 22 · Sprint 1 工程质量审计
- 24 · Sprint 2 N+1 批量优化(查询数 28→7 / 22→4 / 64→6)
- 27 · Sprint 3 请求作用域复用(AI context 路径 59.0 → 31.5 ms,本地基准)
- 等价性测试 + 变异测试 + 跨语言行为探针

### 外部验证 · NAB Benchmark(2026-09-30)

- 三方法异常检测在 [NAB (Numenta Anomaly Benchmark)](https://github.com/numenta/NAB) 上验证
- 58 个公开时间序列,52 个含 ground-truth 异常窗口
- Point-level F1 0.152(Combined) > 任意单方法(最佳 0.146) > naive baseline (0.017)
- Z-score precision 0.456,所有方法中最高
- 脚本与结果在 `benchmark/external/nab/`(可独立复跑)

---

## 明确不做 · 范围边界

下列为**项目设计决策**,不是待办事项:

- ✗ 结构安全鉴定 / 倒塌预测 / 自动结构设计 / 出具施工图
- ✗ 任何"符合行业标准 / 国家标准"声称(参数都是 prototype)
- ✗ 真实建筑部署 / 真实硬件接入 / IoT 流式数据
- ✗ Vector DB / embedding / 语义检索(语料规模不需要)
- ✗ 互联网知识爬取 / 外部工程标准引用
- ✗ 任何让 AI 替代专业工程判断的路径
- ✗ BIM / GIS / 3D 数字孪生
- ✗ 用户认证 / 付费 / 多租户
- ✗ 多轮对话 / conversation_id(刻意不做)
- ✗ 流式响应 / SSE / function calling / Agent / MCP
- ✗ Anthropic native SDK(只用 OpenAI-compatible)
- ✗ 安装 openai / langchain 等 SDK

详见 `docs/28_Project_Fact_Sheet.md` §21-23。

---

## 候选下一步 · 未启动

按杠杆排序:

### 工程侧(补强 demo / 简历用)

- 跨 endpoint 共享分析结果(消除已知 N+1 形态)
- 异常检测结果持久化(避免每请求重算历史)

### 数据侧

- 用真实工程案例反向校准 BHI 权重 / 风险边界
- 接入真实监测数据格式,替换模拟数据生成器
- 支持多建筑时间轴对齐与横向对比

### AI 侧

- Provider 对比 benchmark(Mock vs Real 延迟 / 失败率 / 成本)

### 待外部条件

- 结构工程师 / 检测工程师专业评审(补"无专业验证"空白)
- 用真实结构检测结论做参数校准

### 2026-09-26 → 2026-10-13 · 已完成(后续可回收叠加,不再列入候选)

- **种子数据扩规模**:3 栋 → 30 栋 / 1,350 → 27,006 条记录。`seed_data.py`
  默认 `n_buildings=30, days=180, seed=42`。commit `c45dd32`。
- **持久化审计日志**:`AuditMiddleware` 每个 HTTP 请求一行
  (`audit_logs` 表,9 张表之一)。`GET /api/audit` + `GET /api/audit/stats`
  提供查询。自检:`grep "audit write failed" data/buildhealth.db` 不应出现。
  commit `4c215de` + Schema init 修复 commit `4167ad1`。
- **Ingestion 适配层 CSV**:`backend/scripts/import_csv.py` 命令行工具。
  commit `154558f`。
- **检索评估集**:`backend/scripts/run_retrieval_eval.py` + 50 query JSONL
  (`scripts/retrieval_eval_set.jsonl`)。当前实测 `recall@3 = 0.64,
  MRR = 0.54`。commit `c0408b2`。
- **中文检索优化**:jieba 分词 + 30 组工程同义词词典。`recall@3`
  0.46 → 0.64,`MRR` 0.3767 → 0.5400。详见 `docs/19_Engineering_RAG.md`。
  commit `3d540a2`。
- **离线 LLM 输出评估集**:30 query 离线评估 + runner + DeepEval 4.2.8
  4 工业指标(Faithfulness / AnswerRelevancy / ContextualRecall /
  ContextualPrecision)+ 1 项目专属 GEval redline safety check
  (`no_unsafe_confirmation`)。CI 默认不安装 deepeval,10 个 deepeval 测试
  中 5 个离线 + 5 个 live 全部 skip(避免污染 CI 数字)。commit `1a9de25`
  + `defe54d`。

---

## 优先级建议(对求职用)

如果目标是**秋招数字工程 / 后端 / AI 工程岗**:

1. 跨 endpoint 共享分析结果(消除已知 N+1 形态)
2. 异常检测结果持久化(避免每请求重算历史)
3. Mock provider 改造:基于检索结果生成,而非纯模板拼接

如果目标是**秋招 TIC / 工程咨询岗**:

1. 结构工程师 30 分钟咨询 + 写 docs/29

任一方向,Phase 1-3 都是 ROI 最高的杠杆点。

---

最后更新:2026-10-16(止血轮,R1 修复)· 前序版本:2026-09-20
