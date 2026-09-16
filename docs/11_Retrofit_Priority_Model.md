# 11 · Retrofit Priority Model 改造优先级模型

> Prototype Retrofit Priority Parameters (RP-v1.0) 设计与公式
> V2 改造优先级评分方法 · 0-100 加权评分

**文档版本**：v0.1 · Phase 4 V2
**最后更新**：2026-09-15
**状态**：Implemented & tested

---

## 1. 公式总览

```
Priority Score (0-100) =
    Risk Severity          × 0.35
  + Trend / Deterioration  × 0.25
  + Component Importance   × 0.20
  + Intervention Urgency   × 0.10
  + Cost Efficiency        × 0.10
  ───────────────────────────────────
  = total (clamped to [0, 100], rounded 0.01)
```

权重和 = 1.0 (runtime assertion 保证).

每个维度的 contribution = dim_score × weight, frontend 可视化展示.

---

## 2. 5 维度详解

### 2.1 Risk Severity (35%)

反映建筑当前风险等级对改造紧迫性的影响.

| Risk Level | Severity Score |
|---|---|
| Normal | 15 |
| Attention | 50 |
| Abnormal | 80 |
| HighRisk | 100 |

逻辑: 风险等级越高,改造紧迫性越大,severity 子分越高.

### 2.2 Trend / Deterioration (25%)

综合 5 个 metric 的趋势恶化程度,每 metric 贡献 0-20,5 个 metric 总和上限 100.

| Metric | 评分逻辑 |
|---|---|
| crack_width | 最近 N 天均值 vs 前 N 天均值,相对上升 → 0-20 |
| tilt | 同上 |
| temperature | CV (变异系数) 越大越差 → 0-20 |
| humidity | 同上 |
| electricity | 同上 |

数据不足时返回默认 50.

### 2.3 Component Importance (20%)

按构件类型映射重要性:

| Component Type | Importance |
|---|---|
| foundation | 100 |
| column | 100 |
| beam | 80 |
| wall | 80 |
| slab | 60 |
| roof | 60 |
| (未指定) | 70 (默认) |

逻辑: 基础和柱对结构安全影响最大,因此优先级高.

### 2.4 Intervention Urgency (10%)

按 rule 输出的 urgency 等级映射:

| Urgency | Score |
|---|---|
| critical | 100 |
| high | 80 |
| medium | 50 |
| low | 20 |

### 2.5 Cost Efficiency (10%)

低成本改造视为高效率 (per dollar of benefit):

| Cost Level | Efficiency Score |
|---|---|
| low | 90 |
| medium | 60 |
| high | 30 |

**注意:** 此处 cost 是 cost level 枚举,不指具体金额.

---

## 3. 等级映射 (Priority Level)

| Score Range | Priority Level |
|---|---|
| 90-100 | Very High |
| 75-89 | High |
| 60-74 | Medium |
| 0-59 | Low |

边界 (与 BHI 风险分级保持一致): 0/60/75/90.

---

## 4. 边界值测试覆盖

`backend/tests/test_priority.py` 覆盖所有边界:

```
map_priority_level: 0, 59, 59.99, 60, 74, 74.99, 75, 89, 89.99, 90, 99, 100
```

实际 priority score 边界 (11 个):
```
0, 1, 50, 59, 60, 74, 75, 89, 90, 99, 100
```

每个边界允许 ±1 等级浮动 (因 priority 由多个子分加权,精确取到特定数值不可达).

---

## 5. 与 BHI 区别

| 维度 | BHI | Priority |
|---|---|---|
| 范围 | 0-100 | 0-100 |
| 含义 | 健康程度 (越高越健康) | 改造紧迫性 (越高越紧急) |
| 维度 | 5 个 (structural/facility/environment/energy/fire) | 5 个 (risk_severity/trend/comp_imp/urgency/cost_eff) |
| 算法 | 加权求和 | 加权求和 |
| 版本 | BHI-v1.0 | RP-v1.0 |
| 输入 | 异常 + 建筑数据 + 监测 | BHI + 风险等级 + 趋势 + 构件 + 规则输出 |
| 输出含义 | 反映"建筑是否健康" | 反映"是否需要改造" |

两者**反向**: BHI 高 → Priority 低 (好建筑不需要紧急改造).
- Normal (BHI ≥ 90) → risk_severity 子分 = 15 (低 priority)
- HighRisk (BHI < 60) → risk_severity 子分 = 100 (高 priority)

---

## 6. Disclaimer (强制)

所有 priority score 展示页面必须显示:

> "Retrofit priority is computed using Prototype Retrofit Priority Parameters (RP-v1.0). This output is engineering decision support only and does not constitute an automated structural reinforcement plan. All recommendations require qualified professional review."

代码中此 disclaimer 在 `app/analytics/config.py::RETROFIT_DISCLAIMER`,所有相关 API 端点返回该字段.

---

## 7. 版本演进

| 版本 | 说明 |
|---|---|
| RP-v1.0 | 当前版本,5 维度子分 + 加权 |
| RP-v2.0 (Phase 5+) | 计划: 加入 LLM 解释层(不修改核心计算), 增加 Cost/Benefit 真实数据 |
| RP-v3.0 (Phase 6+) | 计划: 与 IoT 实时数据集成, 动态 trend |

修改 priority 公式必须:
1. 更新 `app/analytics/config.py` 权重
2. 更新 `RETROFIT_PRIORITY_VERSION` 常量
3. 更新本文档
4. 更新 `backend/tests/test_priority.py` 边界值
5. 不破坏 V1 BHI 算法

---

**文档版本**：v0.1 · Phase 4 V2
**最后更新**：2026-09-15
**状态**：Implemented & tested
