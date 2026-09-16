# 16 · AI Safety Redlines  AI 安全红线

> Phase 5 V3 · 禁止 AI 行为清单与强制 disclaimer
> Engineering Realism Redlines 扩展

**文档版本**：v0.1 · Phase 5 V3
**最后更新**：2026-09-15
**状态**：Implemented & tested

---

## 1. 禁止 AI 行为清单

### 1.1 不得声称安全 / 倒塌

- "This building is safe" / "This building is unsafe"
- "Building will collapse" / "Structure will fail"
- "Structural failure is certain"
- "AI predicts structural failure"
- "Guaranteed safe" / "Definitely safe" / "Absolutely safe"
- "Guaranteed to fail"

### 1.2 不得声称完成工程鉴定

- "Automatic structural appraisal completed"
- "Official safety certification"
- "Safety certification issued"
- "Real-world deployment occurred"
- "Deployed in production"

### 1.3 不得自动设计

- "Automatic reinforcement design"
- "AI-designed reinforcement"
- "Auto-generated structural design"
- "AI designed the reinforcement"

### 1.4 不得假冒专业检查

- "Professional inspection completed" (without "qualified" qualifier)
- "Engineer has approved" / "Engineer approved"

### 1.5 不得声称符合标准

- "Complies with national standard" / "符合国家标准"
- "符合行业标准" / "符合国标"
- 任何正向声明符合国家 / 行业 / 国际标准

### 1.6 不得编造绝对结论

- "This is a real building" / "This is a real monitoring"
- 任何把模拟数据描述为真实数据的措辞

---

## 2. 强制 Disclaimer

### AI_DISCLAIMER (固定字符串)

```
AI Engineering Assistant output is engineering decision support only, 
based on Prototype BHI / Risk / Priority parameters. It does not 
constitute professional engineering appraisal, automatic structural 
design, or a building safety certification. All outputs require 
qualified professional review.
```

### 必含关键词 (测试强制)

- "Prototype"
- "decision support"
- "professional review"
- "qualified"

### 必出现位置

- 每次 AIResponse 的 `disclaimer` 字段
- AIAssistant 页面 Provider banner
- AI Response 卡片底部

---

## 3. Mock Provider 受控字符串

Mock Provider 的 answer 模板从 context 直接读数字, 绝不硬编或编造.

### 模板示例 (summary)

```python
f"Building '{b.name}' (id={b.building_id}) is a {b.building_type} "
f"with {b.floors} floors, structure type '{b.structure_type}', "
f"currently {b.current_age} years old (design life {b.design_life})."
```

所有 `{...}` 都从 context 读, 不会注入额外信息.

### 模板示例 (risk explanation)

```python
f"Prototype Risk Classification for '{b.name}' is {r.risk_level or 'N/A'}. "
f"Inputs: BHI={bhi_str} (calculation_version={h.calculation_version}); "
f"anomalies high={r.n_high}, medium={r.n_medium}, low={r.n_low}. "
f"This is a Prototype Risk Classification, not a legally "
f"binding building safety grade. Qualified professional review "
f"is required for any safety-relevant conclusion."
```

明确标注 "Prototype" / "Qualified professional review" / "not a legally binding grade".

---

## 4. 测试覆盖

`backend/tests/test_ai_redlines.py` 强制:

### 4.1 Forbidden phrase 扫描 (parametrize)

对 3 个建筑 profile (Healthy / Attention / Abnormal) × 5 个 question 路由 (summarize / risk / retrofit / anomaly / default) 扫描:

- `answer + disclaimer` 联合扫描
- `key_findings` 每项扫描
- `recommended_actions` 每项扫描

每个禁词出现 → test fail.

### 4.2 强制 disclaimer 关键词

```python
@pytest.mark.parametrize("keyword", ["Prototype", "decision support", "professional review", "qualified"])
def test_disclaimer_required_keyword(keyword):
    assert keyword in AI_DISCLAIMER
```

### 4.3 Schema 完整性

- evidence 必含 source_type
- key_findings severity ∈ {info, low, medium, high}
- response provider 必为 "mock"
- response model 必含 "mock" (不伪装为真实 LLM)

---

## 5. 与 V1 红线的关系

| Redline | V1 (Engine) | V2 (Retrofit) | V3 (AI) |
|---|---|---|---|
| 不得声称符合国家标准 | ✓ | ✓ | ✓ (强化) |
| 不得声称自动结构设计 | ✓ | ✓ | ✓ (强化) |
| 不得危言耸听 | ✓ | ✓ | ✓ (新增: 不得 collapse / fail) |
| 不得假冒专业检查 | — | — | ✓ NEW |
| 不得编造数据 | ✓ | ✓ | ✓ (新增: sensor ID 验证) |
| 必含 disclaimer | ✓ | ✓ | ✓ (新增: 4 关键词强制) |

V3 的红线比 V1/V2 更严, 因为 AI 有"流利"风险, 必须额外约束.

---

## 6. 真实 LLM 接入时的 Redline 强制 (Phase 6+)

未来真实 provider 必须:
1. 使用 `prompts.SYSTEM_PROMPT` 作为 system prompt
2. 解析 LLM 输出为结构化 AIResponse (失败 → 降级 mock)
3. 再次扫描禁词, 发现 → 拒绝输出 + 降级 mock
4. disclaimer 强制注入 (LLM 不可省略)
5. evidence 数量 >= 1 (若 LLM 返回 0 → 用 context 默认 evidence)

这些强制逻辑在 `get_ai_provider()` 工厂中实现.

---

**文档版本**：v0.1 · Phase 5 V3
**最后更新**：2026-09-15
**状态**：Implemented & tested
