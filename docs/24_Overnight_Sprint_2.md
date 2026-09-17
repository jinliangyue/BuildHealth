# 24 · Overnight Sprint 2 · Engineering Optimization & Documentation

> 第二轮夜间自主工程强化。目标是在不破坏稳定版本的前提下，提升性能、
> 数据访问效率与可维护性。不进入 Phase 6C。

**起始 commit**：`340fc87 docs: improve BuildHealth project presentation`
**起始时间**：2026-09-16 夜（第二轮）
**基线测试**：Backend 376 · Frontend 92 · tsc 0 errors · build PASS · API smoke 15/15

---

## 1. 约束

- 不修改 `3fea1c2` / `f27f6f7` / `340fc87`，不回滚任何历史 commit
- 不删除测试、不弱化断言
- 不引入大型依赖 / LangChain / 向量库 / Redis / 联网搜索
- 不实现 Conversation / SSE / Agent / MCP / Function Calling / BIM / GIS / IoT / MQTT
- 不实现自动结构设计、安全认证、倒塌预测
- 保留全部 disclaimer / redlines / evidence grounding
- 所有大型 build/test 串行执行
- 需要大规模架构重构的优化：跳过并记录原因

---

## 2. 当前架构

```
SQLite (8 张表)
  → SQLAlchemy ORM
  → Analytics Engine  (anomaly · health · risk · priority · recommendation_rules)
  → Services          (assessment · retrofit_service)
  → FastAPI           (15 业务端点 + 2 health)
  → AI 层             (Mock / OpenAI-compatible provider + knowledge RAG)
  → React + TS + ECharts (8 页面)
```

---

## 3. 阶段计划与结果

| 阶段 | 内容 | 状态 |
|---|---|---|
| Step 1 | 建立基线 + 本文件 | 完成 |
| Step 2 | 性能与数据访问审计 | 进行中 |
| Step 3 | 工程参数 API 化评估 | 待办 |
| Step 4 | 低风险 N+1 优化 | 待办 |
| Step 5 | 性能基准 | 待办 |
| Step 6 | 工程数据可追溯性审计 | 待办 |
| Step 7 | AI/RAG 最终安全审计 | 待办 |
| Step 8 | `docs/25_Project_Technical_Overview.md` | 待办 |
| Step 9 | 技术问答文档（已移出公开仓库） | 待办 |
| Step 10 | 完整回归 | 待办 |
| Step 11 | Git 提交 | 待办 |

---

## 4. Step 2 性能审计结果

### 4.1 调用链

```
GET /api/dashboard/summary → services/assessment.get_dashboard_summary
GET /api/buildings/overview → services/assessment.get_buildings_overview
GET /api/retrofit/overview → services/retrofit_service.get_retrofit_overview
                                 └── 每栋建筑 → generate_recommendations
                                        ├── run_anomaly_detection   （读 sensors + 每 metric 一条序列）
                                        ├── compute_health_assessment（再读 temperature/humidity/electricity 序列）
                                        ├── get_metric_series × N     （trend score 又读一遍同样的序列）
                                        └── _get_recent_values_by_sensor（每个传感器一条查询）
```

### 4.2 实测查询次数（优化前，3 栋建筑 / 15 传感器 / 1350 条记录）

| 端点 | 查询数 | 耗时 |
|---|---|---|
| /api/dashboard/summary | 28 | 118 ms |
| /api/buildings/overview | 22 | 94 ms |
| /api/retrofit/overview | 64 | 123 ms |

### 4.3 三个具体问题

1. **同一批监测序列被读 3 次**（最严重）
   `run_anomaly_detection` 读一遍、`compute_health_assessment` 读一遍、
   trend score 再读一遍。retrofit 路径每栋建筑因此多发约 13 条序列查询。
2. **dashboard 每栋建筑把最新 HealthAssessment 查了两次**（第 4 步算平均分、
   第 5 步算风险分布），纯重复。
3. **传感器与最近值逐条查询**：`_get_recent_values_by_sensor` 每个传感器一条查询。

### 4.4 扩展到 100 / 1000 栋建筑

优化前查询数量随建筑数线性增长（dashboard ≈ 4 + 8N）：
100 栋 ≈ 804 条；1000 栋 ≈ 8004 条。retrofit overview ≈ 1 + 21N。

优化后固定：dashboard 7 条、overview 4 条，与建筑数无关。

### 4.5 判断

属于**低风险批量化**，不需要改 API contract，不需要新基础设施，
因此按 Step 4 实施（而非跳过）。

---

## 5. Step 3-7 结果

### Step 3 · 工程参数 API 化（已实施）

新增只读端点 `GET /api/engineering-parameters`：

- 返回 BHI 权重、BHI 风险档位、改造优先级档位与权重、检测阈值、
  各层 calculation_version、以及 prototype 免责声明
- 数值**直接读自** `app/analytics/config.py`，端点本身不做任何计算
- 前端 `DataSettings` 改为从该端点读取；本地常量降级为
  **纯 UI fallback**，并在页面上显式标注当前数据来源（Live / Fallback）
- 加载态、错误态、fallback 全部有 UI 表达

关键设计：**档位表用引擎行为校验**。新增的 `BHI_RISK_BANDS` 只是参数化描述，
`test_engineering_parameters_api.py` 会用 `classify_risk` /
`map_priority_level` 逐个边界验证两者一致 —— 改一边不改另一边直接失败。
这比「再抄一份常量」强得多。

未改变计算引擎：`risk.py` / `priority.py` / `health.py` 的公式一行未动。

### Step 4 · N+1 优化（已实施）

| 端点 | 优化前 | 优化后 | 倍数 |
|---|---|---|---|
| /api/dashboard/summary | 28 | **7** | 4.0× |
| /api/buildings/overview | 22 | **4** | 5.5× |
| /api/retrofit/overview | 64 | **13** | 4.9× |

实现方式：新增 3 个批量读取器（`get_latest_assessments` /
`load_sensors_by_building` / `load_series_map_by_building`），聚合接口一次读入，
再在内存里逐栋计算；`run_anomaly_detection` 与 `compute_health_assessment`
增加**可选**预加载入参（传 None 时行为与之前完全一致）。

API response shape 未做任何改变。retrofit overview 仍有每栋 4 条查询
（building/components/sensors/series），因为 `generate_recommendations`
是单建筑端点的公开函数；进一步批量需要改动其签名，本次不做，记入技术债。

### Step 5 · 性能基准（本地开发环境）

本机 8GB M2 Air · SQLite · 3 栋建筑 / 1350 条记录。优化后取 5 次中位数：

| 端点 | 查询数 | 中位数 | 最小 |
|---|---|---|---|
| /api/dashboard/summary | 7 | 83.2 ms | 81.8 ms |
| /api/buildings/overview | 4 | 82.4 ms | 80.0 ms |
| /api/retrofit/overview | 13 | 88.8 ms | 88.3 ms |

耗时拆解（dashboard）：

```
anomaly detection（3 栋）  80.0 ms   ← 92%
批量序列读取                 3.0 ms
dashboard 合计              87.0 ms
```

结论：查询次数已不再是瓶颈，**剩余耗时 92% 是异常检测的 CPU 重算**。
再优化需要「一次请求内只算一遍异常」或把告警持久化 / 加缓存 ——
本 Sprint 明确不引入缓存系统，因此记录为技术债，不再动。

> 说明：以上是本地开发环境基准，不是生产环境性能保证。
> 优化前的耗时是单次测量，优化后是 5 次中位数；查询次数是精确值。

### Step 6 · 工程数据可追溯性审计（已修复 1 项）

链路逐层检查：Building → Sensor → MonitoringRecord → Anomaly →
HealthAssessment → Risk → RetrofitRecommendation → AI Evidence → Knowledge Evidence

| 层 | id | 来源 | 版本 | 时间戳 | 可回溯原始数据 |
|---|---|---|---|---|---|
| Building/Sensor/Record | ✓ | DB | n/a | ✓ | ✓ |
| Anomaly (RiskAlert) | ✓ | `sensor_id` + `metric` | **原缺 → 已补** | ✓ | ✓（可追到传感器） |
| HealthAssessment | ✓ | building_id | BHI-v1.0 | ✓ | 经 anomalies |
| Risk classification | ✓ | building_id + n_high/medium/low | **原缺 → 已补 RISK-v1.0** | 实时 | 经 BHI + anomalies |
| RetrofitRecommendation | ✓ | building_id + 证据链 | RP-v1.0 / REC-v1.0 | 实时 | 经 sensor/anomaly/BHI |
| AI Evidence | ✓ | `reference_path` 可点击回页面 | AI-v1.0 | ✓ | ✓ |
| Knowledge Evidence | ✓ | `chunk_id` + `document` + `source` | — | — | 可回到知识库原文 |

修复的问题：**风险分级是唯一没有版本标识的层**。其他各层（BHI / RP /
REC / AI）都有 version 并随响应返回，风险分级没有，导致旧的分类结论无法
反查是按哪版参数产生的。

处理：新增 `RISK_CLASSIFICATION_VERSION = "RISK-v1.0"` 与
`ANOMALY_DETECTION_VERSION = "ANOM-v1.0"`，在参数端点统一暴露，
并在 `GET /api/buildings/{id}/risk` 响应中附带 `calculation_version`
（新增字段，向后兼容）。已补测试断言。

未做：不给 RiskAlert 加逐行版本（会牵动数据模型与历史行），
当前由 `ANOM-v1.0` 在参数端点统一声明。

### Step 7 · AI/RAG 安全审计

| 检查项 | 结论 | 依据 |
|---|---|---|
| knowledge_evidence 只能来自 retriever | ✓ | real_provider 强制取自入参，LLM 返回的被丢弃 |
| user question 视为 untrusted | ✓ | system prompt 显式声明 |
| knowledge content 视为 untrusted | ✓ | `UNTRUSTED KNOWLEDGE CONTEXT` 段落 |
| engineering data 优先于一般知识 | ✓ | prompt 中 `absolute priority` |
| disclaimer 强制 | ✓ | 两个 provider 都强制覆盖为 AI_DISCLAIMER |
| redlines 完整 | ✓ | 43 条（含 11 条 RAG 专项），scanner 已接入 provider |
| 能否生成确定性安全结论 | ✗ 不能 | 禁词扫描 + schema 校验 + 语料自检 |
| 知识库文本被误认为官方标准 | ✗ 不会 | 禁词覆盖该类表述 + 语料禁标准编号 |
| Mock 与 Real provider 行为一致 | **原不一致 → 已修复** | 见下 |

修复的问题：**Real provider 有运行时红线闸门，Mock provider 没有**。
Mock 输出仅由测试保证合规，运行时不做扫描。虽然 Mock 用模板生成文本，
但它会插入数据库里的值（建筑名、指标名、风险等级）。若这些值里出现禁词，
Mock 会原样输出，而 Real provider 会抛 `safety_violation` —— 两个 provider
在安全行为上不一致。

处理：给 Mock provider 加上同样的运行时闸门
（`_guard_safety`，复用 `scan_response_for_redlines`，命中即抛
`safety_violation`）。已补两个测试：带禁词的数据必须被拦、正常数据不受影响。

安全相关测试合计 109 + 2 = 111 条。

---

## 6. Step 8-9 文档

### Step 8 · `docs/25_Project_Technical_Overview.md`

英文项目技术总览，面向国际工程咨询 / TIC / 工程数字化方向。含项目标题、
一句话描述、工程问题、架构、核心工作流、工程分析（异常检测 / BHI /
风险分级 / 改造决策）、证据链、AI 助手、知识 RAG、技术栈、测试、
安全与范围边界、模拟数据限制、Roadmap。

定位明确为数字化工程决策支持系统，而不是「AI developer」。
全部内容基于真实实现，无虚构。

### Step 9 · 技术问答文档（已移出公开仓库）

17 个技术问题，每条四段：当前实现 / 技术理由 / 局限 / 后续改进。
覆盖工程问题定义、为什么不是看板、异常检测、可解释性、BHI、原型参数、
风险分级、改造优先级、两类证据分离、RAG 选型、为什么不让 LLM 算、
prompt injection 防护、确定性检索、如何扩展、N+1 在哪、
如何接真实数据、生产化要改什么。

不虚构生产经验：生产化那题明确写「当前是单机开发形态」并列出缺口。
该文档属于问答准备材料，已于 2026-09-17 移出公开仓库。

### README 更新

- 端点说明更正为 16 业务 + 2 health + 1 只读参数端点
- 新增参数端点说明
- 新增 docs 22-26 索引
- 测试统计更新为 Sprint 2 后的数字

---

## 7. Step 10 回归与 Step 11 提交

### 回归（串行，`bash scripts/verify.sh` 一次通过）

| 阶段 | 结果 |
|---|---|
| Backend tests | **401 passed** |
| Frontend tests | **15 files / 97 passed** |
| TypeScript | 0 errors |
| Production build | ✓ 714 modules · 2.26s |
| 脚本退出码 | **0 · ALL CHECKS PASSED** |

API smoke test：uvicorn 实跑，**19/19 端点全部 200**，
并验证 `GET /api/engineering-parameters` 返回 6 个版本标识、
`GET /api/buildings/{id}/risk` 携带 `RISK-v1.0`、
AI 端点 `evidence` 与 `knowledge_evidence` 仍然分离且 disclaimer 强制生效。

对比起始基线：Backend 376 → 401（+25），Frontend 92 → 97（+5）。
无删除测试、无弱化断言。

### 环境问题（非代码）

本轮开始时发现 `node_modules/@types/` 下有 9 个空目录，名字带 ` 2` 后缀
（`react 2`、`react-dom 2` 等），导致 tsc 报 9 个 `TS2688` 错误。
经逐一确认**全部为空目录**后删除，tsc 恢复 0 errors。
属于 macOS 文件冲突副本，与项目代码无关。

### 提交

`3fea1c2` / `f27f6f7` / `340fc87` 保持不变。本轮分两个 commit：

- `80f1c6c` — 工程性能优化（N+1 批量化 + 参数端点）
- `03114a4` — 文档整理（参数 API 化与性能审计记录）

提交标题可在 `git log` 中查看；此处只记 commit hash 与内容摘要。

