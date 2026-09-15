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

## 3. 维度定义（V1）

### 3.1 Structural Safety（结构安全）· 40%

**V1 输入来源**（设计）：

- crack_width 监测数据 + 阈值异常
- tilt 监测数据 + 阈值异常
- 历史 HealthAssessment 趋势（最近 3 次）

**评分逻辑**（设计稿）：

```python
def score_structural(records: list[dict], anomalies: list[Anomaly]) -> float:
    base = 100.0
    for a in anomalies:
        if a.method == "threshold" and a.severity == Severity.HIGH:
            base -= 15
        elif a.method == "threshold" and a.severity == Severity.MEDIUM:
            base -= 8
        elif a.method == "rate_of_change" and a.severity == Severity.HIGH:
            base -= 10
    return max(0.0, min(100.0, base))
```

### 3.2 Facility Condition（设施状况）· 20%

**V1 简化逻辑**：基于建筑年龄 + 维护假设

```python
def score_facility(building: Building) -> float:
    age = 2026 - building.built_year
    # 假设：50 年以上 60 分，30 年 80 分，新建 95 分
    score = 95 - (age * 0.7)
    return max(0.0, min(100.0, score))
```

### 3.3 Environmental Quality（环境质量）· 15%

**V1 输入**：temperature / humidity 稳定性

```python
def score_environment(temp_records: list, hum_records: list) -> float:
    temp_std = pd.Series([r["value"] for r in temp_records]).std()
    hum_std = pd.Series([r["value"] for r in hum_records]).std()

    # 温度标准差 < 5 ℃ 满分；> 15 ℃ 零分
    temp_score = max(0, 100 - temp_std * 6.7)
    # 湿度标准差 < 10 % 满分；> 30 % 零分
    hum_score = max(0, 100 - hum_std * 3.3)

    return (temp_score + hum_score) / 2
```

### 3.4 Energy Performance（能耗表现）· 10%

**V1 输入**：electricity 用电模式稳定性（峰谷差）

```python
def score_energy(elec_records: list) -> float:
    values = pd.Series([r["value"] for r in elec_records])
    cv = values.std() / values.mean() if values.mean() != 0 else 0  # 变异系数

    # CV < 0.2 满分；> 0.8 零分
    score = max(0, 100 - (cv - 0.2) * 166.67)
    return score
```

### 3.5 Fire Safety（消防安全）· 15%

**V1 占位逻辑**：静态评分

```python
def score_fire(building: Building) -> float:
    # V1 未接入真实消防监测，使用建筑年龄 + 楼层数粗估
    base = 85.0
    if building.total_floors > 20:
        base -= 5
    if (2026 - building.built_year) > 30:
        base -= 5
    return max(0.0, min(100.0, base))
```

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

**Phase 0** — 设计完成

- ✅ 5 维度评分逻辑已设计
- ✅ 权重版本化机制已规划
- ✅ 强制声明位置已明确
- ⏳ 实际代码未实现

---

**文档版本**：v0.1 · Phase 0 起草
**最后更新**：2026-09-15
**状态**：Designed but not implemented
