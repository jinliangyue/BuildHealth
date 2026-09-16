# 15 · AI Context & Grounding  上下文与证据落地

> Engineering Context Builder 设计 · 证据落地 (Evidence Grounding) 原则
> Phase 5 V3 · 关键: AI = 解释层, 不是计算层

**文档版本**：v0.1 · Phase 5 V3
**最后更新**：2026-09-15
**状态**：Implemented & tested

---

## 1. Context Builder 设计

`backend/app/ai/context_builder.py` 的 `build_engineering_context()` 是 V3 的关键入口.

### 设计原则

> **不重新计算任何工程指标.**

Context Builder 只能:
- 读数据库
- 调用已有 V1/V2 services
- 组装结构化 EngineeringContext

Context Builder 绝不能:
- ❌ 自己计算 BHI
- ❌ 自己判断风险
- ❌ 自己判定异常
- ❌ 自己生成改造建议
- ❌ 自己计算 priority score

这样保证:
> AI = 解释已有数据
> 而不是 AI = 重新计算

---

## 2. 复用 V1 / V2 services 清单

```python
def build_engineering_context(session, building_id) -> EngineeringContext:
    # 1. 加载基础元数据 (V1 models)
    building = session.get(m.Building, building_id)
    components = session.query(m.Component).filter(...).all()
    sensors = session.query(m.Sensor).filter(...).all()

    # 2. 复用 V1 assessment service
    anomalies = assessment_svc.run_anomaly_detection(session, building_id)
    health = assessment_svc.compute_health_assessment(session, building, anomalies)
    risk = assessment_svc.classify_risk_for_building(health["score"], anomalies, building_id)

    # 3. 复用 V2 retrofit service
    retrofit_decision = retrofit_svc.get_retrofit_decision(session, building_id)

    # 4. 统计 monitoring 数据 (V1 models 直接读)
    for s in sensors:
        records = session.query(m.MonitoringRecord).filter(sensor_id=s.id).all()
        ...

    # 5. 组装 context
    return EngineeringContext(...)
```

Context Builder 调用的 service 全部是 V1 / V2 已有函数. 任何对算法的修改必须先在 V1/V2 service 完成, 不能在 Context Builder 私自修改.

---

## 3. EngineeringContext Schema

```python
class EngineeringContext(BaseModel):
    building_id: int
    building: ContextBuildingInfo
    components: List[ContextComponentInfo]
    sensors: List[ContextSensorInfo]
    monitoring_summary: ContextMonitoringSummary
    health: ContextHealthInfo
    risk: ContextRiskInfo
    retrofit: ContextRetrofitInfo
    evidence_chain: List[AIEvidenceRef]
    disclaimer: str
    generated_at: datetime
    context_version: str = "CTX-v1.0"
```

### 字段填充来源

| 字段 | 来源 |
|---|---|
| `building` | m.Building 表 |
| `components` | m.Component 表 |
| `sensors` | m.Sensor 表 |
| `monitoring_summary.total_records` | m.MonitoringRecord count |
| `monitoring_summary.by_metric` | 按 sensor_type 分组 |
| `monitoring_summary.anomaly_total` | run_anomaly_detection() 返回列表长度 |
| `health.bhi` | compute_health_assessment()["score"] |
| `health.dimensions` | compute_health_assessment() 5 维度 |
| `health.weakest_dimension` | 计算 (取 dim 最小值) |
| `risk.risk_level` | classify_risk_for_building()["risk_level"] |
| `risk.n_high/medium/low` | 异常计数 |
| `retrofit.overall_priority` | get_retrofit_decision()["overall_priority"] |
| `retrofit.recommendations` | 完整 recommendation 列表 |
| `evidence_chain` | 自动从 retrofit_decision / alerts 抽取 |

---

## 4. Evidence Grounding 原则

每条 AI 回答的重要判断都必须能追溯到 EngineeringContext 中已有数据.

### 强约束

1. **不编造 sensor ID** — sensor_id 必须在 ctx.sensors 列表中
2. **不编造 BHI 数字** — 必须读 ctx.health.bhi
3. **不编造 risk level** — 必须读 ctx.risk.risk_level
4. **不编造 priority score** — 必须读 ctx.retrofit.overall_priority
5. **不编造 recommendation** — 必须读 ctx.retrofit.recommendations

### 测试覆盖

`backend/tests/test_ai_mock_provider.py::test_summary_numbers_match_context` 强制验证:
- answer 字符串中包含 `f"{ctx.health.bhi:.2f}"`
- answer 包含 `ctx.risk.risk_level`

`backend/tests/test_ai_redlines.py` 强制:
- Mock 输出不含 25+ 禁词
- 所有 evidence 必含 source_type + description
- 所有 key_findings 必含 severity

---

## 5. Mock Provider 确定性

Mock Provider 是确定性的:
- 同一 context → 同一 output
- 不调外部 API
- 数字直接读 context
- answer 字符串从 context 模板生成

### 5 个问题路由

```python
def generate_answer(self, context, question):
    q_lower = question.lower()
    if any(kw in q_lower for kw in ("总结", "summarize", "health")):
        return self.generate_summary(context)
    if any(kw in q_lower for kw in ("风险", "risk")):
        return self._explain_risk(context)
    if any(kw in q_lower for kw in ("改造", "retrofit", "优先级")):
        return self._explain_retrofit(context)
    if any(kw in q_lower for kw in ("异常", "anomaly", "裂缝")):
        return self._explain_anomaly(context)
    return self.generate_summary(context)  # default
```

未来真实 LLM provider 可用更智能的分类, 但 Mock 保持简单可预测.

---

## 6. 证据链路可视化

`Context.evidence_chain` 字段 (List[AIEvidenceRef]) 自动生成:

1. **building** — 必有
2. **health** — 若 ctx.health.bhi 不为空
3. **risk** — 若 ctx.risk.risk_level 不为空
4. **retrofit_recommendation** (top 3) — 若有 rec
5. **anomaly** (top 3 HIGH severity) — 若有 HIGH

每条 evidence 必含可点击 URL. 前端 `EvidenceList` 组件把 `/api/buildings/{id}/...` 转为内部路由.

---

## 7. 不写库

Context Builder 是纯读操作:

```python
def test_does_not_modify_db(test_session, sample_full_building):
    rec_before = test_session.query(m.MonitoringRecord).count()
    alert_before = test_session.query(m.RiskAlert).count()
    assess_before = test_session.query(m.HealthAssessment).count()
    build_engineering_context(test_session, building_id)
    assert rec_before == rec_after
    assert alert_before == alert_after
    assert assess_before == assess_after
```

---

**文档版本**：v0.1 · Phase 5 V3
**最后更新**：2026-09-15
**状态**：Implemented & tested
