# 09 · 版本路线图（Version Roadmap）

> ⚠️ **本文件已于 2026-10-16 标记为 SUPERSEDED(止血轮 R1)。**
> 原内容仍可读,但不再代表项目当前状态。本文档主要错位:
>
> 1. 顶部状态栏仍自称"Phase 0 — 当前",但项目实际已完成 Phase 6B
>    (`v1.1.0` release tag `32af4ad` 2026-09-26);
> 2. 最后更新日期 2026-09-15 与仓库真实时间线相差一个月以上;
> 3. §5"未来探索方向"中 BIM/GIS / AI Agent / 自动结构设计 /
>    多用户权限 / 云部署+支付 / IoT-MQTT 已被 `ROADMAP.md` 明确
>    排除在候选之外。
>
> **请改用 [../../ROADMAP.md](../../ROADMAP.md) 作为本项目的当前
> 版本规划来源。** 本文件保留用于:(a) 历史考古回溯;(b) 与
> `BuildHealth-prep-notes/` 中旧决策材料交叉引用时定位原文。
>
> 本节以下内容系历史快照,可能与代码 / 最新文档不一致,需以
> `ROADMAP.md` + `28_Project_Fact_Sheet.md` 为准。

---

## 1. 阶段总览

```
Phase 0          Phase 1          Phase 2          Phase 3+
Project Init  →  V1 MVP       →  V1 Polish    →  V2+
2026-09-15       2026-09-22      2026-10-15      2026-12+
(当前)            (目标)          (目标)
```

## 2. Phase 0 — Project Initialization ✅ 当前

**目标**：项目骨架 + 文档设计 + 工具链就位

**已完成**：

- ✅ 项目目录结构（frontend / backend / docs / tests / data / scripts）
- ✅ Git 仓库初始化
- ✅ 9 份设计文档
- ✅ 技术栈确定
- ✅ 数据库 ER 设计
- ✅ API 架构设计
- ✅ Analytics 引擎架构
- ✅ 模拟数据生成器架构
- ✅ 前端骨架（Vite scaffold）

**未做**（符合 Phase 0 边界）：

- ❌ 业务代码（CRUD、计算引擎实现）
- ❌ Dashboard 完整页面
- ❌ 异常检测算法实现
- ❌ 真实数据接入

## 3. Phase 1 — V1 MVP 实现

**目标**：跑通完整数据链路

**预计工作量**：约 5-7 个工作日

### 3.1 后端任务（优先级降序）

1. **数据库模型 + 迁移**
   - SQLAlchemy 6 张表模型
   - Alembic 初始化迁移
   - 自动建表（开发期）

2. **模拟数据生成器**
   - 3 种建筑 × 5 类指标 × 90 天
   - 工程趋势逻辑（不纯随机）
   - 一键脚本：`python scripts/seed_data.py`

3. **Analytics Engine 实现**
   - trend.py / anomaly.py / health.py / risk.py / sim_data.py
   - 100% unit test 覆盖

4. **API 实现（16 项）**
   - Buildings CRUD
   - Components CRUD
   - Sensors CRUD
   - MonitoringRecords 查询 + 批量插入
   - HealthAssessment 查询 + 触发重算
   - RiskAlert 查询
   - Dashboard 聚合接口
   - Analytics 接口（趋势 / 异常列表）

5. **基础测试**
   - pytest + FastAPI TestClient
   - 至少 20 个 unit + integration 测试

### 3.2 前端任务（优先级降序）

1. **Layout + 路由**
   - Sidebar + TopBar + React Router
   - 6 个页面占位

2. **API Client**
   - axios instance + 错误处理
   - TypeScript 类型与后端 Pydantic 对应

3. **6 个页面骨架**
   - Dashboard（KPI 卡片 + Top 风险 + 总览图）
   - Buildings（卡片网格 + 筛选）
   - Building Detail（Header + 评分 + 趋势图）
   - Monitoring（时序图 + 表格）
   - Risk & Health（风险列表 + 雷达图）
   - Settings（参数配置）

4. **图表组件**
   - TrendChart（ECharts 时序图）
   - BhiRadar（ECharts 雷达图）
   - DistributionPie（ECharts 饼图）

5. **免责水印**
   - 全局右下角 "Simulated Data" 标识
   - BHI 显示处强制 Prototype 声明

### 3.3 测试 & 文档

- 20+ 测试用例通过
- README 更新（启动命令 + 截图占位）
- API 文档自动生成（FastAPI OpenAPI）

### 3.4 Phase 1 Done Definition

- [ ] 后端 16 项 API 全部可调通
- [ ] 前端 6 个页面全部可访问、可渲染
- [ ] 模拟数据生成器可一键产出完整数据集
- [ ] 异常检测至少触发 3 次（Abnormal Building）
- [ ] BHI 计算结果与手工核算一致
- [ ] 风险等级与 BHI 分档一致
- [ ] 每个 API 响应都能在数据库查到对应行
- [ ] 至少 20 个测试通过
- [ ] 前端无任何硬编码数值
- [ ] README + 9 份 docs 文档齐全

## 4. Phase 2 — V1 Polish

**目标**：补完 V1 短板 + 体验优化

- 图表交互（缩放 / 联动 / Tooltip）
- 批量操作（多建筑对比）
- 导出（CSV / PDF 报告）
- 错误处理 + Loading 状态 + 空状态
- 响应式适配（平板可用）

## 5. Phase 3+ — V2 及未来

**保留方向**（不承诺时间）：

- 改造建议生成（基于 BHI + 异常模式）
- 改造优先级排序
- 成本估算（参考市场价）
- IoT 设备接入（ESP32 + MQTT）
- BIM / GIS 三维可视化
- RAG 知识库（接入规范文档）
- AI Agent（自动巡检建议）
- 自动结构设计 / 自动加固设计
- 多用户权限系统
- 云部署 + 支付

## 6. 长期原则

无论到哪个阶段，**工程真实性原则不可违反**：

1. 不伪造真实数据
2. 不声称国家标准
3. 不输出未经专业依据的结论
4. 所有计算可解释
5. 所有数据可追溯

## 7. 当前状态

**Phase 0 — 进行中（已完成文档设计）**

下一步：等待用户决策是否进入 Phase 1。

---

**文档版本**：v0.1 · Phase 0 起草
**最后更新**：2026-09-15
**状态**：Phase 0 in progress
