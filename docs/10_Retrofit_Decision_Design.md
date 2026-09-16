# 10 · Retrofit Decision Design 改造决策设计

> Retrofit Decision 决策支持系统设计 · Existing Building Retrofit Decision Support
> V2 设计文档 · 与 V1 BHI/Risk 形成完整闭环

**文档版本**：v0.1 · Phase 4 V2
**最后更新**：2026-09-15
**状态**：Implemented & tested

---

## 1. 背景

V1 (Phase 1-3) 已完成"监测 → BHI → 风险"的完整链路,但是仅作为 Dashboard 提供问题视图,不输出"改不改、怎么改、优先级如何"的工程决策支持。

V2 (Phase 4) 的目标是在 V1 的数据基础上,新增:

```
Monitoring → Assessment → Risk → Retrofit Decision
                              ↑
                        本阶段新增
```

完整决策支持链路,而非仅"看到问题"。

---

## 2. V2 定位

**BuildHealth 不是:**
- 智能家居
- IoT dashboard
- AI 聊天机器人
- 自动结构设计软件
- 自动加固设计软件
- 建筑安全认证系统

**BuildHealth 是:**
- 既有建筑健康监测与智能更新决策平台 (Existing Building Health Monitoring & Intelligent Retrofit Decision Support Platform)

**V2 的角色:** Decision Support,不是 Automatic Engineering Design.

### 系统可以:
- 识别问题
- 解释风险
- 计算改造优先级
- 推荐可能的改造方向
- 给出成本等级 (低/中/高,无精确数字)
- 给出建议下一步行动

### 系统不能:
- 自动判断建筑一定安全/不安全
- 自动出结构施工图
- 自动生成钢筋设计
- 自动替代结构工程师
- 声称符合某个国家规范并可以直接用于工程施工

---

## 3. 数据模型

V2 在 V1 6 张表基础上新增 2 张表:

### RetrofitRecommendation

| Col | Type | Notes |
|---|---|---|
| `id` | Integer PK | |
| `building_id` | Integer FK buildings | cascade delete |
| `component_id` | Integer FK components | set null |
| `category` | String(32) | Structural/Envelope/MEP/Environment/Energy/FireSafety |
| `issue_type` | String(64) | crack_growth/tilt_trend/moisture_control/energy_efficiency/comprehensive_assessment |
| `title` | String(128) | 短标题 |
| `recommendation` | Text | 详细建议 |
| `rationale` | Text | 工程理由 |
| `next_action` | Text | 下一步行动 |
| `urgency` | String(16) | low/medium/high/critical |
| `estimated_cost_level` | String(16) | low/medium/high (3 档,无具体数字) |
| `expected_benefit` | String(16) | low/medium/high |
| `source` | String(64) | "rule:crack_growth" (显式来源) |
| `evidence_json` | Text | 完整证据链 (sensors + anomalies + bhi/risk context) |
| `priority_score` | Float | 0-100 (RP-v1.0 加权) |
| `calculation_version` | String(32) | REC-v1.0 |
| `created_at` | DateTime | utcnow |

Index: `(building_id, urgency)`, `(building_id, category)`.

### EngineeringNote

| Col | Type | Notes |
|---|---|---|
| `id` | Integer PK | |
| `building_id` | Integer FK buildings | cascade delete |
| `component_id` | Integer FK components | set null |
| `text` | Text | 现场笔记 |
| `source` | String(32) | field_note/site_inspection |
| `created_at` | DateTime | |

Index: `(building_id, created_at)`.

---

## 4. 服务架构

新增 2 个 analytics 模块 + 1 个 service:

```
app/analytics/priority.py              # RP-v1.0 加权 + breakdown
app/analytics/recommendation_rules.py  # 5 条 rule 函数
app/services/retrofit_service.py       # 编排 (调用 assessment + analytics)
app/api/retrofit.py                    # 3 个新端点
```

依赖关系:

```
retrofit_service
    ├── assessment_service  (复用 V1)
    ├── analytics.priority  (RP-v1.0)
    └── analytics.recommendation_rules  (REC-v1.0)
```

---

## 5. API 端点

| Method | Path | 描述 |
|---|---|---|
| GET | `/api/buildings/{id}/retrofit` | 单建筑完整 retrofit decision |
| GET | `/api/buildings/{id}/retrofit/{rec_id}` | 单条 recommendation 详情 |
| GET | `/api/retrofit/overview` | 跨建筑概览 |

### RetrofitDecisionRead schema

```python
{
  "building_id": int,
  "building": BuildingRead,
  "overall_priority": float,        # 0-100
  "overall_priority_level": "Low"|"Medium"|"High"|"Very High",
  "calculation_version": "RP-v1.0",
  "recommendations": [RetrofitRecommendationDetailRead, ...],  # 按 priority 降序
  "engineering_notes": [EngineeringNoteRead, ...],
  "disclaimer": "Retrofit priority is computed using Prototype..."  # 强制
}
```

---

## 6. Evidence Chain 证据链

每个 recommendation 的 `evidence` 字段完整追溯到原始监测数据:

```
Sensors (id, name, metric, recent_values, anomaly_count)
    ↓
Anomalies (timestamp, method, severity, explanation)
    ↓
BHI Context (score, weakest_dimension)
    ↓
Risk Context (risk_level, explanation)
    ↓
Recommendation (priority_score + breakdown)
```

Example response shape:

```json
{
  "sensors": [
    {
      "sensor_id": 3,
      "name": "crack_width_sensor_3",
      "metric": "crack_width",
      "unit": "mm",
      "recent_values": [
        {"timestamp": "2026-09-13", "value": 0.22},
        {"timestamp": "2026-09-14", "value": 0.58}
      ],
      "anomaly_count_by_severity": {"high": 4, "medium": 1, "low": 0}
    }
  ],
  "anomalies": [{"timestamp": "...", "severity": "high", ...}],
  "bhi_context": {"score": 54.27, "weakest_dimension": "structural_safety"},
  "risk_context": {"risk_level": "HighRisk", "explanation": "..."}
}
```

---

## 7. 已知限制

- **不**接 IoT / 真实硬件
- **不**做 BIM / GIS / 3D
- **不**做云部署 / 支付 / 用户权限
- **不**做自动结构设计 / 钢筋设计
- **不**做真实建筑安全认证
- **不**在核心计算中引入 LLM (Phase 5 计划加入)
- **不**伪造精确造价或 ROI 数字
- **不**修改 V1 现有 BHI / Risk 算法
- 优先级计算是 prototype parameters,非国家标准

---

## 8. 与 V1 关系

| 组件 | V1 | V2 |
|---|---|---|
| Monitoring | ✓ | 复用 |
| Anomaly Detection | ✓ | 复用 |
| BHI | ✓ | 复用 |
| Risk Classification | ✓ | 复用 |
| Recommendation | — | **新增** |
| Priority Score | — | **新增** |
| Evidence Chain | — | **新增** |
| Engineering Notes | — | **新增** |

V2 是 V1 之上的纯增量,**不**修改任何 V1 业务逻辑.

---

**文档版本**：v0.1 · Phase 4 V2
**最后更新**：2026-09-15
**状态**：Implemented & tested
