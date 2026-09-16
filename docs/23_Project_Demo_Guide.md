# 23 · Project Demo Guide

> 面向面试 / 作品集演示的说明材料。
> 全部内容基于当前真实实现，不包含未实现的功能。

**文档版本**：v1.0
**最后更新**：2026-09-16
**适用版本**：Phase 6B（V3.2）

---

## A. 30 秒项目介绍

BuildHealth 是一个既有建筑健康监测与更新决策平台的原型。

它把监测数据（裂缝宽度、倾斜、温湿度、用电）经过三层确定性分析 ——
异常检测、BHI 健康评分、四档风险分级 —— 再叠加一个改造优先级与建议
规则引擎，最后用 AI 解释层把这些结果讲成人能读懂的话。

关键点是数据流向是单向的：所有工程数值都由后端算法算出，AI 只负责解释，
不参与计算。所有参数都是原型设计参数，不是国家或行业标准。

技术栈：FastAPI + SQLAlchemy + SQLite + React + TypeScript + ECharts。

---

## B. 1 分钟项目介绍

问题：既有建筑的数量在增长，但结构检测依赖人工，成本高、周期长。监测系统
能持续采集数据，但采集到的原始数值本身不构成决策依据 —— 中间缺一层
可解释的工程分析。

BuildHealth 实现的就是这一层：

1. 数据层：建筑 / 构件 / 传感器 / 监测记录，全部为模拟数据。
2. 异常检测层：三种方法并行 —— 绝对阈值、相邻点变化率、7 天滚动窗口
   Z-score。三种方法的检出结果按严重度合并去重。
3. 健康评估层：BHI 0-100 综合评分，由 5 个维度加权得到（结构安全 0.40、
   设施状况 0.20、环境质量 0.15、节能 0.10、消防安全 0.15）。
4. 风险分级层：4 档（Normal / Attention / Abnormal / HighRisk），按 BHI
   分档，并有一条覆盖规则 —— 只要存在 HIGH 严重度异常，最低升级为 Attention。
5. 决策层：RP-v1.0 改造优先级（5 个子分加权 0-100）与 REC-v1.0 规则引擎，
   输出改造建议、成本等级、紧急度和证据链。
6. 解释层：AI 工程助手读取上面的确定性结果，用自然语言解释，并严格区分
   「本建筑的数据证据」与「通用工程知识背景」。

工程边界是刻意的：系统不预测倒塌、不做安全鉴定、不生成加固设计、
不声称符合任何标准。

---

## C. 3 分钟完整 Demo 流程

演示环境：`backend` 起 uvicorn，`frontend` 起 vite，浏览器开 http://localhost:5173/

### 第 1 站 · Dashboard（20 秒）

打开首页。先指出顶部的 Engineering workflow 条：这是平台实现的完整分析链路，
每一步都能点进去。

然后看 KPI：建筑数、监测点、活跃告警、平均 BHI。再看 Risk Distribution
（风险分布饼图）和 Building Ranking（按 BHI 升序排的建筑列表）。
注意右下角常驻的 Simulated Data 水印。

### 第 2 站 · Building Detail（60 秒，核心页）

点排名里的 Building C · Abnormal Complex。这一页是完整工程故事：

- Building Summary：建筑基本信息
- Health Overview：BHI 总分
- Five Dimensions (Radar)：5 维度雷达图
- Dimension Scores & Weights：每个维度的分数与权重
- Monitoring Overview：裂缝宽度趋势 + 异常点标注
- Active Alerts：当前活跃异常
- Sensors：传感器清单
- Retrofit Decision：优先级 + 建议 + 工程笔记
- AI Engineering Assistant：进入解释层

演示重点：所有数字都能在页面上找到来源，没有一处是前端写死的。

### 第 3 站 · Monitoring（20 秒）

切到 Monitoring 页。展示趋势图与异常点叠加，说明数据是模拟生成的确定性
时间序列（基线 + 趋势 + 周期波动 + 噪声 + 事件）。

### 第 4 站 · Risk & Health（30 秒）

展示 BHI 分档、风险分布、告警列表。这里明确标注 Prototype Risk
Classification，不是法定的建筑安全等级。

### 第 5 站 · Retrofit Decision（30 秒）

展示跨建筑的改造优先级排序、分类分布、成本与紧急度。强调这是
decision support，不是自动加固方案。

### 第 6 站 · AI Assistant（40 秒，最值得演示）

选一个建筑，点一个 Quick Question，或点 Quick Summary。

拿到回答后，重点讲解回答面板被拆成几块：

- Answer：自然语言解释
- Key Findings：带严重度标签的要点
- Evidence：本建筑的实测与派生证据（每个都能点回到对应页面）
- Knowledge Sources（紫色区块）：从项目内部知识库检索到的通用工程概念，
  明确标注不是本建筑的数据、不是官方标准
- Recommended Actions：带紧急度的建议
- Disclaimer：固定免责声明

这就是 Phase 6B 的核心：两类证据在数据结构、prompt 和 UI 上都是分开的。

---

## D. 5 个最值得现场展示的功能

1. 证据链（Evidence Chain）与两类证据的严格区分
   同一个回答里，Evidence 是本建筑数据，Knowledge Sources 是通用知识，
   字段名不同、颜色不同、来源不同，且 AI 无法伪造 knowledge_evidence。

2. 确定性工程算法 → AI 解释的单向数据流
   BHI / 风险 / 优先级全部由后端算法算出。AI 只能读，不能改。
   可以现场说明：AI 输出的 disclaimer 会被后端强制覆盖。

3. RAG 检索完全离线且可解释
   纯标准库 TF-IDF + cosine，无向量库、无 embedding、无联网。
   5 篇项目内部知识文档 → 23 个 chunk → top-3。每次检索结果可复现。

4. 安全红线由测试强制
   43 条禁止短语扫描、语料自检（不得含标准编号）、
   prompt injection 防护、disclaimer 强制注入 —— 都有对应测试。

5. 完整的可复现验证
   一条 `bash scripts/verify.sh` 串行跑完后端测试、前端测试、类型检查、
   生产构建；另有 API smoke test。

---

## E. 10 个可能被问到的问题

1. 为什么用 BHI 加权，权重怎么定的？
2. 三种异常检测方法为什么要并行，怎么合并结果？
3. 风险分级为什么要加 HIGH 异常覆盖规则？
4. 改造优先级 RP-v1.0 是怎么算出来的？
5. AI 会不会给出错误的结构结论？怎么防？
6. RAG 为什么不用向量数据库？
7. 数据是真实的吗？
8. 这套系统能不能替代结构检测？
9. 如果阈值要改，需要动哪些地方？
10. 系统的性能瓶颈在哪？

---

## F. 对应技术解释要点

1. 权重
   BHI 5 维度权重（0.40 / 0.20 / 0.15 / 0.10 / 0.15）是原型设计参数，
   集中在 `backend/app/analytics/config.py`，前端只做显示镜像并有测试
   锁定两者一致。演示时说明：这不是国家标准的权重。

2. 三种方法并行
   绝对阈值抓突变，变化率抓持续发展，Z-score 抓偏离历史统计规律。
   单一方法各有盲区，所以三种都跑，检出后按严重度去重。
   Z-score 对噪声大的指标（用电、湿度）关闭。

3. 覆盖规则
   单纯按 BHI 分档会漏掉「分数还行但已经出现严重局部异常」的情况。
   所以只要有 HIGH 严重度异常，最低升级为 Attention。
   这是保守方向的规则 —— 宁可多提醒，不会漏报。

4. RP-v1.0
   5 个子分加权成 0-100：风险等级、趋势、构件重要性、紧急度等。
   分档为 Low / Medium / High / Very High。改造建议由 REC-v1.0 规则引擎
   按类目生成，带成本等级。全部实时计算，不落库。

5. AI 安全
   四层防护：prompt 里声明用户输入不可信；输出做 Pydantic schema 校验；
   43 条禁止短语扫描命中即抛 safety_violation；disclaimer 由后端强制覆盖，
   LLM 自己返回的会被丢弃。knowledge_evidence 同样强制取自检索结果。

6. 不用向量库
   需求是离线、确定性、可解释、零外部依赖。TF-IDF 每次排序都能用
   df/idf 数值解释，测试可以直接断言；embedding 会引入模型下载、
   非确定性浮点和外部服务。数据规模（23 个 chunk）也远不需要向量检索。

7. 数据真实性
   全部是模拟数据。seed 脚本用确定性时间序列生成器造出 3 栋建筑、
   15 个传感器、1350 条记录、187 条告警。页面上有常驻水印，
   Data/Settings 页有完整的数据来源说明。没有接任何真实硬件或社区。

8. 不能替代
   系统做的是 decision support：识别问题、解释风险、算优先级、排顺序。
   不做安全鉴定、不预测倒塌、不出加固图。所有输出都要求
   qualified professional review。

9. 改阈值
   改 `backend/app/analytics/config.py`（阈值/权重）或 `risk.py`（分档边界）。
   如果同时影响前端显示镜像，`backend/tests/test_frontend_parameter_consistency.py`
   会失败并指出是哪一项漂移。这条测试就是为此设计的。

10. 性能
    当前规模很小，瓶颈是聚合接口里的逐建筑分析调用（N+1 形态）。
    建筑数量少时无感；数量上去后需要把 per-building 分析批量化或加缓存。
    另外 AI 端点是否慢，取决于用的是 Mock provider 还是真实 LLM。

---

## G. 不能声称的内容（重要）

演示时必须明确，这个项目：

- 不是正式结构鉴定，也不构成结构鉴定结论
- 不预测建筑倒塌或结构失效
- 不做自动结构设计，不生成加固方案或施工图
- 不是官方标准评分系统，BHI / 风险分级 / 优先级都是原型参数
- 不是实际部署案例，没有真实建筑或社区在用
- 数据全部为模拟数据，未接入任何真实 IoT / 硬件
- AI 输出是工程决策支持，需要具备资质的专业人员复核

这些边界不是免责话术，而是写进代码和测试的约束：
`backend/app/ai/redlines.py` 的 43 条禁止短语、强制 disclaimer、
以及 `tests/test_rag_redlines.py` 的语料自检。
