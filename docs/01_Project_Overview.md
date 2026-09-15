# 01 · 项目概述（Project Overview）

## 1. 项目名称

**BuildHealth**
既有建筑健康监测与智能更新决策平台
Existing Building Health Monitoring & Intelligent Retrofit Decision Platform

## 2. 项目定位

BuildHealth 是一个面向既有建筑的**数字化工程决策支持原型平台**。

它不替代专业结构工程师、不替代检测鉴定机构、不输出"建筑即将倒塌"这类结论。

它将传统的建筑状态管理过程**数字化、流程化、可追溯化**：

```
建筑档案
  → 监测数据
  → 数据分析
  → 异常检测
  → 建筑健康评价
  → 风险分级
  → 后续更新改造决策（V2+）
```

## 3. 当前阶段

**V1 MVP（Minimum Viable Prototype）**

只解决一件事：把建筑 → 监测 → 分析 → 评分 → 风险的链路跑通。

未来才考虑：

- 改造建议
- 改造优先级
- 成本估算
- IoT 设备接入（ESP32 / MQTT）
- BIM / GIS 三维可视化
- RAG / AI Agent
- 自动结构设计 / 自动加固设计
- 云部署 / 权限系统 / 支付

## 4. V1 必须实现（16 项）

1. Building 建筑管理
2. Component 构件管理
3. Sensor 监测点管理
4. MonitoringRecord 监测数据管理
5. Monitoring Trend 趋势分析
6. Anomaly Detection 异常检测
7. Building Health Index 建筑健康评分
8. Risk Classification 风险分级
9. Dashboard
10. Buildings
11. Building Detail
12. Monitoring
13. Risk & Health
14. 基础数据管理
15. 模拟工程数据生成
16. 基础测试

## 5. V1 禁止实现

- ESP32 / MQTT / IoT 接入
- BIM / GIS / 3D 建筑模型
- RAG / AI Agent
- 自动结构设计 / 自动加固设计
- 云部署 / 支付
- 用户权限系统 / 社交功能
- 任何形式的真实建筑数据接入

## 6. 工程真实性原则（硬性规则 · 不可违反）

1. 不伪造真实建筑监测数据
2. 不声称系统已部署在真实小区
3. 不把自定义评分体系说成国家标准
4. 不让 AI 或算法替代专业工程判断
5. 不输出"建筑即将倒塌"等未经专业依据的结论
6. 所有模拟数据必须明确标记为 **Simulated Data**
7. 所有评分必须可解释（可追溯到维度 + 子项 + 输入）
8. 所有关键数据必须可追溯（数据库 → API → 前端）
9. 所有计算逻辑必须可以测试
10. 工程逻辑优先于 UI

## 7. 技术栈

| 层 | 技术 |
|---|---|
| Frontend | React 18 + TypeScript + Vite + Tailwind CSS + ECharts |
| Backend | Python 3.9 + FastAPI + SQLAlchemy + Pydantic |
| Database | SQLite |
| Data Analysis | Pandas + NumPy + SciPy + scikit-learn（仅确有必要时） |

## 8. 数据范围

**V1 全部为 Simulated Data。**

至少三种建筑原型：

- Healthy Building（健康）
- Attention Building（关注）
- Abnormal Building（异常）

重点监测指标：

- crack_width（裂缝宽度 · mm）
- tilt（倾斜 · ‰）
- temperature（温度 · ℃）
- humidity（湿度 · %）
- electricity（用电 · kWh）

---

**文档版本**：v0.1 · Phase 0 起草
**最后更新**：2026-09-15
**状态**：Designed but not implemented（设计已完成，业务代码未实现）
