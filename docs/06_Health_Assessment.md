# 06 · 健康评估（Health Assessment）

## 1. 评估目标

对单栋建筑输出 0–100 分的 **Building Health Index（BHI）**，用于：

- Dashboard 总览
- Building Detail 单建筑评分
- Risk & Health 页面雷达图
- Risk Classification 引擎的输入

## 2. BHI 公式（Prototype Design Parameters v0.1）

```
BHI = Structural Safety      × 0.40
    + Facility Condition     × 0.20
    + Environmental Quality  × 0.15
    + Energy Performance     × 0.10
    + Fire Safety            × 0.15
```

**约束**：

- 五项权重之和必须为 1.0（运行时断言）
- 每个维度输入值范围 [0, 100]
- 输出 BHI 范围 [0, 100]

## 3. 维度定义（V1 · Phase 1 已实现）

实际代码位于 `backend/app/analytics/health.py`。

### 3.1 Structural Safety（结构安全）· 40%

**实际算法**（`score_structural_from_anomalies`）：

- 基础分 100
- 按异常严重度对数扣分：`100 - log1p(n_high)*18 - log1p(n_medium)*6 - log1p(n_low)*2`
- 优势：异常数量越多边际扣分越小，避免一次事件拖垮整栋

### 3.2 Facility Condition（设施状况）· 20%

**实际算法**（`score_facility_from_age`）：

- 基础分 95（新建）
- 设计年限内线性下降到 75：`score = 95 - 20 * (current_age / design_life)`
- 超出设计年限加速下降：`score = max(30, 75 - (over * 100))`

### 3.3 Environmental Quality（环境质量）· 15%

**实际算法**（`score_environment_from_series`）：

- 温度得分：`max(0, 100 - (stdev - 3) * 8)`（stdev<3 ℃ 满分）
- 湿度得分：`max(0, 100 - (stdev - 5) * 5)`（stdev<5 % 满分）
- 取两者平均

### 3.4 Energy Performance（能耗表现）· 10%

**实际算法**（`score_energy_from_series`）：

- 用电变异系数 CV = stdev / mean
- CV < 0.15 满分；CV > 0.6 零分：`max(0, 100 - (CV - 0.15) * 220)`

### 3.5 Fire Safety（消防安全）· 15%

**实际算法**（`score_fire_placeholder` · V1 占位）：

- 基础分 90
- 楼层 ≥20 扣 8；≥10 扣 4
- 年龄 >30 扣 5；>15 扣 2

## 4. 版本化机制

```python
# core/config.py
BHI_VERSIONS = {
    "v0.1": {
        "weights": {
            "structural_safety": 0.40,
            "facility_condition": 0.20,
            "environmental_quality": 0.15,
            "energy_performance": 0.10,
            "fire_safety": 0.15,
        },
        "released_at": "2026-09-15",
        "note": "Phase 0 初始版本",
    },
}

CURRENT_BHI_VERSION = "v0.1"
```

**写入数据库**：

- HealthAssessment.bhi_version = "v0.1"
- 查询时按版本号过滤（不混算）

**未来版本切换**：

- 引入 v0.2 → 写入新记录时使用新权重
- 历史记录保留原 bhi_version，可对比

## 5. 计算时机

V1 设计：

- **手动触发**：API `/api/health/recompute/{building_id}`
- **自动触发**（未来）：cron 每日凌晨跑一次

## 6. 强制声明

每个 BHI 显示位置（Dashboard / Building Detail / Risk & Health）都必须显示：

> "BHI 为 Prototype Design Parameters（v0.1），非国家标准或真实工程鉴定标准。"

## 7. 当前状态

**Phase 1 — 完成**

- ✅ 5 维度评分逻辑已实现并通过 16 个 unit test
- ✅ 权重版本化（calculation_version=BHI-v1.0）已生效
- ✅ 范围校验（非 0-100 输入抛 HealthInputError）
- ✅ 强制声明：每次 explanation 含 "prototype assessment suggests further professional inspection is recommended"

**实际运行结果（模拟数据）**：

| Building | BHI | structural | facility | environment | energy | fire |
|---|---|---|---|---|---|---|
| A Healthy | 96.02 | 100.0 | 91.6 | 100.0 | 100.0 | 90.0 |
| B Attention | 87.44 | 82.6 | 82.6 | 100.0 | 100.0 | 88.0 |
| C Abnormal | 54.27 | 0.0 | 82.6 | 100.0 | 100.0 | 85.0 |

---

**文档版本**：v0.2 · Phase 1 实施
**最后更新**：2026-09-15
**状态**：Implemented & tested
