# 12 · Retrofit Recommendation Rules 改造建议规则

> REC-v1.0 规则引擎 · 5 条 rule 函数 · 纯函数 / 无 LLM / 可解释
> Phase 4 V2 推荐规则定义

**文档版本**：v0.1 · Phase 4 V2
**最后更新**：2026-09-15
**状态**：Implemented & tested

---

## 1. 设计原则

1. **Explainable** — 每条建议都必须可解释, 给出 evidence 链
2. **Deterministic** — 同一输入 → 同一输出
3. **Versioned** — 规则版本 REC-v1.0, 每次修改升级
4. **No LLM** — Phase 4 不引入 LLM, Phase 5+ 才考虑 (作为解释层,非核心)
5. **No Black Box** — 不使用 ML anomaly detection 或 reinforcement learning

---

## 2. 5 条规则总表

| # | Issue Type | Category | Trigger | Recommendation |
|---|---|---|---|---|
| 1 | crack_growth | Structural | crack_width 异常 OR zscore > 2 | Detailed inspection of affected structural components |
| 2 | tilt_trend | Structural | tilt 异常 OR zscore > 2 | Inspect potential differential deformation |
| 3 | moisture_control | Environment | humidity 异常 OR env_score < 80 | Review ventilation, moisture control, envelope |
| 4 | energy_efficiency | Energy | electricity 异常 OR energy_perf < 80 | Review electrical equipment and energy efficiency |
| 5 | comprehensive_assessment | Structural | risk_level in (Abnormal, HighRisk) | Conduct comprehensive engineering assessment |

---

## 3. 详细规则

### Rule 1: Crack Growth (裂缝生长)

**Trigger (满足任一):**
- 至少 1 个 crack_width anomaly (来自 RiskAlert)
- crack_width 序列 zscore abs > 2 in last 30 days

**Urgency 判定:**
- 存在 HIGH severity anomaly → `high`
- 否则 → `medium`

**Cost / Benefit 默认:**
- estimated_cost_level: `medium`
- expected_benefit: `high`

**Recommended Action:**
> "Review by qualified engineering personnel and perform detailed inspection including crack mapping and material assessment."

### Rule 2: Tilt Trend (倾斜趋势)

**Trigger (满足任一):**
- 至少 1 个 tilt anomaly
- tilt 序列 zscore abs > 2 in last 30 days

**Urgency:** 同上 (HIGH → high, else medium)
**Cost / Benefit:** medium / high
**Action:** "Engage qualified surveyor to assess deformation pattern, foundation settlement indicators, and reference network."

### Rule 3: Moisture Control (湿度 / 围护)

**Trigger (满足任一):**
- 至少 1 个 humidity anomaly
- environmental_quality < 80

**Urgency:**
- env_score < 60 → `high`
- 否则 → `medium`

**Cost / Benefit:** low / medium
**Action:** "Inspect building envelope for moisture sources, review HVAC operation, and consider ventilation upgrade or moisture barrier installation."

### Rule 4: Energy Efficiency (能耗)

**Trigger (满足任一):**
- 至少 1 个 electricity anomaly
- energy_performance < 80

**Urgency:**
- ener_score < 60 → `medium`
- 否则 → `low`

**Cost / Benefit:** low / medium
**Action:** "Audit major electrical loads, review equipment schedules, and identify efficiency opportunities including retrofit to higher-efficiency equipment."

### Rule 5: Comprehensive Assessment (综合评估)

**Trigger:**
- risk_level in (`Abnormal`, `HighRisk`)

**Urgency:**
- HighRisk → `high`
- Abnormal → `medium`

**Cost / Benefit:** high / high
**Action:** "Commission a comprehensive engineering assessment by qualified professionals covering structural, MEP, and envelope systems."

---

## 4. Evidence 字段填充

每条 matched rule 返回的 RuleResult.evidence 包含:

```python
{
  "sensors": [
    {
      "sensor_id": int,
      "metric": str,           # crack_width/tilt/...
      "name": str,
      "unit": str,
      "location": str,
      "recent_values": [       # 最近 10 条
        {"timestamp": "iso", "value": float}
      ],
      "anomaly_count_by_severity": {"high": int, "medium": int, "low": int}
    }
  ],
  "anomalies": [
    {
      "sensor_id": int, "metric": str, "timestamp": str,
      "current_value": float, "detection_method": str,
      "severity": str, "explanation": str
    }
    # 最多 10 条
  ],
  "bhi_context": {"score": float, "weakest_dimension": str} | None,
  "risk_context": {"risk_level": str, "explanation": str} | None,
  "anomaly_summary": {"total": int, "high": int, "medium": int} | None  # 仅 Rule 5
}
```

---

## 5. 优先级字段映射

Rule output → Priority Score 输入:

```
RuleResult.urgency          → priority.urgency_score
RuleResult.estimated_cost   → priority.cost_efficiency
RuleResult.component_id     → priority.component_importance (查 COMPONENT_IMPORTANCE 表)
```

优先级计算见 `docs/11_Retrofit_Priority_Model.md`.

---

## 6. 输入参数 (RuleContext)

```python
@dataclass
class RuleContext:
    building: Building
    health: dict          # 来自 health assessment 服务
    risk: dict            # 含 risk_level
    anomalies: List[dict]  # 已 dedup 的 anomaly dict
    sensors_by_metric: Dict[str, List[Sensor]]
    components: List[Component]
```

5 条 rule 函数签名统一为:
```python
def rule_xxx(ctx: RuleContext, recent_values_by_sensor: Dict[int, List]) -> List[RuleResult]
```

`recent_values_by_sensor` 由 service 层注入,key 是 sensor_id,value 是最近 30 天内最近 10 条记录.

---

## 7. 版本演进

| 版本 | 说明 |
|---|---|
| REC-v1.0 | 5 条基础规则 (Phase 4 V2 当前) |
| REC-v1.1 (Phase 5+) | 计划: 加入 MEP / Fire Safety 规则 |
| REC-v2.0 (Phase 5+) | 计划: LLM 解释层 (在 rule 之上, 不替换 rule) |
| REC-v3.0 (Phase 6+) | 计划: 多建筑联合规则 (e.g. 邻近影响) |

修改规则必须:
1. 更新 `app/analytics/recommendation_rules.py`
2. 更新 `RECOMMENDATION_RULES_VERSION` 常量
3. 更新本文档
4. 更新 `backend/tests/test_recommendation_rules.py` 测试
5. 不破坏 V1 BHI/Risk 算法

---

## 8. 测试覆盖

`backend/tests/test_recommendation_rules.py` 21 个测试,覆盖:
- 每条 rule 的 trigger / no-trigger case
- Urgency 判定 (HIGH → high, env<60 → high, etc.)
- Cost / Benefit 默认值
- Evidence 字段完整性 (sensors / anomalies / bhi/risk context)
- 5 条 rule 同时触发
- Calculation version = REC-v1.0

---

**文档版本**：v0.1 · Phase 4 V2
**最后更新**：2026-09-15
**状态**：Implemented & tested
