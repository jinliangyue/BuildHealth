# 02 · 工程需求（Engineering Requirements）

## 1. 范围声明

本文档定义 BuildHealth V1 的工程需求边界。

它是**项目内强制规则**，覆盖：

- 数据真实性
- 评分体系归属
- 算法可解释性
- 数据可追溯性
- 风险结论免责

## 2. 工程真实性红线（10 条）

### 2.1 数据真实性

| 编号 | 规则 | 触发场景 |
|---|---|---|
| ER-01 | 不得伪造真实建筑监测数据 | 模拟数据生成器必须带 `is_simulated=True` 标记 |
| ER-02 | 不得声称系统部署在真实小区 | 所有页面必须显示 "Simulated Data" 水印 |
| ER-03 | 不得使用真实小区名称、地址、坐标 | Building.name / address 必须是虚构命名 |

### 2.2 评分体系归属

| 编号 | 规则 | 触发场景 |
|---|---|---|
| ER-04 | 自定义评分体系不得声称是国家标准 | BHI 公式必须标注 "Prototype Design Parameters" |
| ER-05 | BHI 权重必须可修改、可版本化 | 计算时必须读取 `bhi_version` 字段 |
| ER-06 | 风险等级不得声称是法定建筑安全等级 | 风险结果页必须显示免责提示 |

### 2.3 算法可解释性

| 编号 | 规则 | 触发场景 |
|---|---|---|
| ER-07 | 每个异常必须给出可解释字段 | `sensor_id / metric / time_range / current / baseline / delta / method / severity / reason` |
| ER-08 | 不得使用无法解释的黑盒模型 | V1 不允许引入深度学习异常检测 |

### 2.4 数据可追溯性

| 编号 | 规则 | 触发场景 |
|---|---|---|
| ER-09 | 前端显示的所有数值必须能追溯到后端 | Dashboard / Building Detail / Monitoring / Risk & Health 全部走 API |
| ER-10 | 禁止 React 页面硬编码 BHI / 风险等级 / 异常数量 / 监测趋势 / 建筑数量 | 任何硬编码数值 = 违反 ER-09 |

## 3. 功能需求（V1 16 项）

### 3.1 数据管理（FR-DM）

- **FR-DM-01** Building CRUD：增删改查 + 列表分页 + 筛选（按城市/类型/年龄）
- **FR-DM-02** Component CRUD：构件管理，与 Building 多对一
- **FR-DM-03** Sensor CRUD：监测点管理，与 Component 多对一
- **FR-DM-04** MonitoringRecord 批量插入与查询：按 sensor + 时间窗口
- **FR-DM-05** HealthAssessment 写入：每次评分生成一条记录，含 `bhi_version`
- **FR-DM-06** RiskAlert 写入：每次风险判定生成一条记录

### 3.2 分析引擎（FR-AE）

- **FR-AE-01** 趋势分析：移动平均 + 同比/环比
- **FR-AE-02** 异常检测：阈值检测 + 变化率检测 + 统计异常（Z-score）
- **FR-AE-03** 健康评分：BHI 0-100，5 维度加权
- **FR-AE-04** 风险分级：4 档（Normal / Attention / Abnormal / High Risk）

### 3.3 前端页面（FR-UI）

- **FR-UI-01** Dashboard：全平台总览 + 趋势图 + Top 风险
- **FR-UI-02** Buildings：建筑列表 + 筛选 + 卡片视图
- **FR-UI-03** Building Detail：单建筑档案 + 评分 + 监测趋势
- **FR-UI-04** Monitoring：监测数据查询 + 时序图
- **FR-UI-05** Risk & Health：风险列表 + 健康评分雷达图
- **FR-UI-06** Data / Settings：基础数据维护 + 参数配置

### 3.4 基础设施（FR-INF）

- **FR-INF-01** 模拟数据生成器：3 种建筑 × 5 类指标 × 90 天
- **FR-INF-02** 测试用例：核心计算逻辑 + API + 前端组件
- **FR-INF-03** 数据库迁移：SQLAlchemy 自动建表
- **FR-INF-04** API 文档：FastAPI 自动生成 OpenAPI

## 4. 非功能需求（NFR）

| 编号 | 类别 | 要求 |
|---|---|---|
| NFR-01 | 可维护性 | 单一职责模块化，BHI 权重配置化 |
| NFR-02 | 可测试性 | 核心计算逻辑必须有 unit test |
| NFR-03 | 可追溯性 | 所有数据可追溯到数据库行 |
| NFR-04 | 性能 | 单建筑趋势查询 P95 < 500ms（SQLite + 10K 行内） |
| NFR-05 | 可移植性 | 纯 Python + 纯 JS，无云依赖，跨平台可运行 |
| NFR-06 | 文档完整性 | 每个模块有 README + 关键函数有 docstring |

## 5. 验收清单（V1 Done Definition）

- [ ] 后端 16 项 API 全部可调通
- [ ] 前端 6 个页面全部可访问、可渲染
- [ ] 模拟数据生成器可一键产出完整数据集
- [ ] 异常检测至少触发 3 次（在 Abnormal Building 上）
- [ ] BHI 计算结果与手工核算一致
- [ ] 风险等级与 BHI 分档一致
- [ ] 每个 API 响应都能在数据库查到对应行
- [ ] 至少 10 个 unit test 通过
- [ ] 前端没有任何硬编码数值（除静态文案外）
- [ ] README + 9 份 docs 文档齐全

## 6. 当前状态

**Phase 0** — 设计阶段

- ✅ 需求清单与红线已编写
- ⏳ V1 业务代码未实现
- ⏳ 测试用例未编写
- ⏳ 验收清单未跑通

---

**文档版本**：v0.1 · Phase 0 起草
**最后更新**：2026-09-15
**状态**：Designed but not implemented
