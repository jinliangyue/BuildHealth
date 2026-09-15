# 05 · 分析引擎设计（Analytics Design）

## 1. 模块定位

Analytics Engine 是 BuildHealth 的**计算层**，由 4 个子引擎组成：

| 引擎 | 职责 | 输入 | 输出 |
|---|---|---|---|
| Trend Engine | 时序趋势分析 | MonitoringRecord 序列 | DataFrame + 摘要 dict |
| Anomaly Engine | 异常检测 | MonitoringRecord 序列 | List[Anomaly] |
| Health Assessment Engine | 5 维度评分 | 聚合统计 | HealthAssessment dict |
| Risk Classification Engine | 风险分级 | BHI + 异常列表 | RiskAlert dict |

**约束**：

- 纯函数式设计（输入 → 输出，无副作用）
- 不依赖 FastAPI / SQLAlchemy
- 100% 可独立单元测试
- 输入输出全部为标准 Python 类型（dict / list / float）

## 2. Trend Engine（趋势分析）

### 2.1 功能

- 移动平均（window=24h / 7d）
- 同比 / 环比（与上一窗口对比）
- 趋势方向判定（up / down / stable）

### 2.2 算法（设计稿）

```python
# analytics/trend.py
import pandas as pd
import numpy as np

def moving_average(records: list[dict], window: int = 24) -> pd.DataFrame:
    """
    records: [{"ts": datetime, "value": float}, ...]
    window: 移动窗口大小（小时）
    return: DataFrame(ts, value, ma_24)
    """
    df = pd.DataFrame(records).sort_values("ts")
    df["ma"] = df["value"].rolling(window=window, min_periods=1).mean()
    return df

def period_over_period(records: list[dict], period_hours: int = 24) -> dict:
    """
    计算与上一周期对比的变化率
    return: {"current_avg": float, "prev_avg": float, "delta_pct": float, "direction": "up"|"down"|"stable"}
    """
    df = pd.DataFrame(records).sort_values("ts")
    if df.empty:
        return {"current_avg": 0, "prev_avg": 0, "delta_pct": 0, "direction": "stable"}

    cutoff = df["ts"].max() - pd.Timedelta(hours=period_hours)
    current = df[df["ts"] >= cutoff]["value"].mean()
    prev = df[(df["ts"] < cutoff) & (df["ts"] >= cutoff - pd.Timedelta(hours=period_hours))]["value"].mean()

    if prev == 0 or pd.isna(prev):
        delta_pct = 0
    else:
        delta_pct = (current - prev) / prev * 100

    if abs(delta_pct) < 1.0:
        direction = "stable"
    elif delta_pct > 0:
        direction = "up"
    else:
        direction = "down"

    return {
        "current_avg": round(float(current), 4),
        "prev_avg": round(float(prev), 4),
        "delta_pct": round(float(delta_pct), 2),
        "direction": direction,
    }
```

## 3. Anomaly Engine（异常检测）

### 3.1 方法优先级（V1）

1. **Threshold Detection**（阈值检测）
   - 每个 metric 都有硬阈值（如 crack_width > 0.3mm 视为异常）
   - 阈值表存储在 `core/config.py`，可版本化
2. **Rate of Change**（变化率检测）
   - 相邻两点变化率 > 50% 视为异常
3. **Z-score**（统计异常）
   - 7 天滚动窗口内偏离均值 > 3σ 视为异常

**禁止使用**：

- Isolation Forest（V1 不引入）
- 深度学习异常检测
- 任何黑盒模型

### 3.2 异常结果结构（强制 · 满足 ER-07）

```python
# analytics/anomaly.py
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

@dataclass
class Anomaly:
    sensor_id: int
    metric: str
    time_range_start: datetime
    time_range_end: datetime
    current_value: float
    baseline_value: float
    delta: float
    method: str              # "threshold" | "rate_of_change" | "zscore"
    severity: Severity
    reason: str              # 人话描述（如"裂缝宽度超过阈值 0.30mm"）
```

### 3.3 阈值表（设计稿）

| metric | 阈值 | 严重程度 |
|---|---|---|
| crack_width | > 0.30 mm | HIGH |
| crack_width | > 0.20 mm | MEDIUM |
| tilt | > 4.0 ‰ | HIGH |
| tilt | > 3.0 ‰ | MEDIUM |
| temperature | > 40 ℃ | MEDIUM |
| humidity | > 80 % | LOW |

### 3.4 算法伪代码

```python
def detect_anomalies(records: list[dict], sensor_meta: dict) -> list[Anomaly]:
    anomalies = []

    # 1. Threshold detection
    threshold = THRESHOLDS.get(sensor_meta["metric"])
    if threshold:
        for r in records:
            if abs(r["value"]) > threshold["value"]:
                anomalies.append(Anomaly(
                    sensor_id=sensor_meta["id"],
                    metric=sensor_meta["metric"],
                    time_range_start=r["ts"],
                    time_range_end=r["ts"],
                    current_value=r["value"],
                    baseline_value=threshold["baseline"],
                    delta=r["value"] - threshold["baseline"],
                    method="threshold",
                    severity=Severity(threshold["severity"]),
                    reason=f"{sensor_meta['metric']} 超过阈值 {threshold['value']}{sensor_meta['unit']}",
                ))

    # 2. Rate of change
    df = pd.DataFrame(records).sort_values("ts")
    for i in range(1, len(df)):
        prev = df.iloc[i-1]["value"]
        curr = df.iloc[i]["value"]
        if prev == 0:
            continue
        change_pct = abs((curr - prev) / prev * 100)
        if change_pct > 50:
            anomalies.append(Anomaly(
                ...,
                method="rate_of_change",
                reason=f"环比变化 {change_pct:.1f}%（>50%）",
            ))

    # 3. Z-score
    window = df["value"].rolling(window=168, min_periods=24)  # 7 天 × 24 小时
    for i in range(len(df)):
        if pd.isna(window.std().iloc[i]) or window.std().iloc[i] == 0:
            continue
        z = (df.iloc[i]["value"] - window.mean().iloc[i]) / window.std().iloc[i]
        if abs(z) > 3:
            anomalies.append(Anomaly(
                ...,
                method="zscore",
                reason=f"Z-score = {z:.2f}（>3σ）",
            ))

    return anomalies
```

## 4. Health Assessment Engine（健康评分）

### 4.1 BHI 公式

```
BHI = Structural×0.40 + Facility×0.20 + Environment×0.15 + Energy×0.10 + Fire×0.15
```

### 4.2 权重配置（可版本化）

```python
# core/config.py
BHI_WEIGHTS_V0_1 = {
    "structural_safety": 0.40,
    "facility_condition": 0.20,
    "environmental_quality": 0.15,
    "energy_performance": 0.10,
    "fire_safety": 0.15,
}
BHI_VERSION = "v0.1"
```

### 4.3 维度评分来源（设计）

| 维度 | 来源（设计） |
|---|---|
| Structural Safety | 从 crack_width / tilt 异常 + 历史健康度推断 |
| Facility Condition | 构件年龄 + 维护记录（V1 简化为基于 built_year 推算） |
| Environmental Quality | temperature / humidity 历史均值稳定性 |
| Energy Performance | electricity 用电模式稳定性 |
| Fire Safety | 暂用静态评分（V1 未接入真实消防监测） |

### 4.4 算法

```python
def compute_bhi(dimensions: dict, weights: dict, version: str) -> dict:
    """
    dimensions: {"structural_safety": 85, "facility_condition": 90, ...}
    weights: {"structural_safety": 0.40, ...}
    return: {"bhi": 87.5, "bhi_version": "v0.1", "breakdown": {...}}
    """
    assert abs(sum(weights.values()) - 1.0) < 1e-6, "权重之和必须为 1"
    assert version, "版本号必填"

    bhi = sum(dimensions[k] * weights[k] for k in weights)
    return {
        "bhi": round(bhi, 2),
        "bhi_version": version,
        "breakdown": {k: round(dimensions[k], 2) for k in dimensions},
    }
```

## 5. Risk Classification Engine（风险分级）

### 5.1 分档规则

```
90–100 → Normal
75–89  → Attention
60–74  → Abnormal
0–59   → High Risk
```

### 5.2 算法

```python
def classify_risk(bhi: float, anomaly_count_high: int) -> dict:
    """
    return: {"risk_level": "Abnormal", "top_reason": "..."}
    """
    if bhi >= 90:
        level = "Normal"
    elif bhi >= 75:
        level = "Attention"
    elif bhi >= 60:
        level = "Abnormal"
    else:
        level = "HighRisk"

    # 原因简述
    if anomaly_count_high > 0:
        reason = f"存在 {anomaly_count_high} 条 HIGH 级别异常"
    elif bhi < 60:
        reason = f"BHI 仅 {bhi}，综合健康度严重偏低"
    elif bhi < 75:
        reason = f"BHI {bhi}，多项指标低于正常"
    else:
        reason = "监测数据基本正常"

    return {"risk_level": level, "top_reason": reason}
```

## 6. 测试要求

每个引擎至少 5 个 unit test：

- Trend Engine：稳态 / 上升趋势 / 下降趋势 / 空数据 / 边界值
- Anomaly Engine：阈值触发 / 变化率触发 / Z-score 触发 / 无异常 / 多异常
- Health Engine：满分 100 / 零分 0 / 边界 75 / 权重异常（断言失败） / 版本号缺失
- Risk Engine：4 个分档全覆盖 + 异常计数影响

## 7. 当前状态

**Phase 0** — 设计完成

- ✅ 4 个引擎职责与边界已设计
- ✅ 关键算法伪代码已编写
- ✅ 异常结果结构已强制
- ⏳ 实际代码未实现（analytics/ 目录为空）

---

**文档版本**：v0.1 · Phase 0 起草
**最后更新**：2026-09-15
**状态**：Designed but not implemented
