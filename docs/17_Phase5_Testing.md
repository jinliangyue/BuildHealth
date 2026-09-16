# 17 · Phase 5 Testing  Phase 5 测试策略

> Phase 5 V3 AI Engineering Assistant 测试覆盖矩阵
> Backend 5 文件 + Frontend 2 文件 · 红线扫描 + 边界值 + 回归

**文档版本**：v0.1 · Phase 5 V3
**最后更新**：2026-09-15
**状态**：Implemented & tested

---

## 1. 测试目标

- **V1+V2 回归**: 199 个 backend 测试 + 50 个 frontend 测试必须全部继续通过
- **V3 新增**: 至少 70 个新测试 (backend) + 10 个新测试 (frontend)
- **Redlines**: 至少 25 个禁词强制扫描 + 强制 disclaimer 关键词
- **Provider 抽象**: Mock 与 future 真实 provider 接口一致

---

## 2. Backend 测试

### V1+V2 保留 (199 tests · 0 改动)

| 文件 | 测试数 |
|---|---|
| test_skeleton | 3 |
| test_database | 8 |
| test_anomaly | 14 |
| test_health | 17 |
| test_risk | 13 |
| test_api | 13 |
| test_buildings_overview | 8 |
| test_priority | 45 |
| test_recommendation_rules | 21 |
| test_retrofit_service | 17 |
| test_retrofit_api | 12 |
| test_engineering_redlines | ~30 |

### V3 新增 (~79 tests · 5 文件)

| 文件 | 测试数 | 主题 |
|---|---|---|
| test_ai_context_builder.py | 12 | context building, 复用 V1/V2 service, 不写库 |
| test_ai_mock_provider.py | 10 | Mock 输出, 数字一致, 5 个问题路由 |
| test_ai_service.py | 8 | 编排, singleton, 不写库 |
| test_ai_api.py | 10 | 3 端点 + OpenAPI + health |
| test_ai_redlines.py | ~15 | 25+ 禁词 parametrize + 4 disclaimer 关键词 + schema |

**Backend 总计: 278 tests**

---

## 3. Frontend 测试

### V1+V2 保留 (50 tests · 0 改动)

### V3 新增 (10 tests · 2 文件)

| 文件 | 测试数 | 主题 |
|---|---|---|
| AIResponsePanel.test.tsx | 5 | 渲染 answer / key_findings / evidence / actions / disclaimer + provider tag + 空数组容错 |
| QuickQuestions.test.tsx | 5 | 5 按钮渲染 + 点击 onSelect + disabled 状态 |

**Frontend 总计: 60 tests**

---

## 4. 边界值与覆盖矩阵

### Context Builder (12 tests)

- building 不存在 → None
- Healthy 建筑 → context 完整
- Attention 建筑 → 1 retrofit rec
- Abnormal 建筑 → 3+ retrofit recs
- context_version = "CTX-v1.0"
- evidence_chain 含 building + health + risk
- 复用 V1 assessment (BHI 一致)
- 复用 V2 retrofit (count 一致)
- 不写库 (rec/alert/assess 计数前后相等)
- sensors record_count >= 0
- monitoring_summary 异常 severity 计数
- generated_at 在 5 秒内

### Mock Provider (10 tests)

- health_check → "ok" / "mock" / "mock-deterministic-v1"
- summary 返回 AIResponse
- disclaimer 必含 "Prototype" + "qualified"
- key_findings 至少 1 条, severity 必 ∈ {info, low, medium, high}
- evidence 至少 1 条
- recommended_actions 至少 1 条
- numbers (BHI / risk_level) 与 context 一致
- 不编造 sensor (sensor_id 必须在 ctx.sensors)
- 4 个问题路由 + default
- 空白 question trim

### AI Service (8 tests)

- get_ai_provider 返回 MockProvider
- provider singleton
- AIService 构造
- summarize_building 正常
- summarize_building 不存在 → None
- summarize_building 不写库
- ask_about_building 正常
- ask_about_building 不存在 → None
- ask trim 空白

### AI API (10 tests)

- GET /api/ai/health → 200 + status=ok
- POST /api/ai/buildings/{id}/summary → 200 + 完整 schema
- POST /api/ai/buildings/{id}/summary 404 (不存在)
- POST /api/ai/buildings/{id}/ask → 200
- ask 缺 question → 422
- ask 空 question → 422
- ask 2001 字符 → 422
- ask 404 (不存在 building)
- OpenAPI 包含 3 个新端点
- /api/health 含 ai_assistant 组件

### AI Redlines (~15 tests)

- AI_DISCLAIMER 含 4 个必含关键词 (parametrize)
- 3 building profile × 4 question = 12 parametrize test, 每个测禁词
- 3 profile 测 key_findings 禁词
- 3 profile 测 recommended_actions 禁词
- evidence 必含 source_type
- key_findings severity 必合法
- response.disclaimer == AI_DISCLAIMER
- response.provider == "mock"
- response.model 含 "mock" (不伪装)

---

## 5. Engineering Realism Redlines (V1+V2 保留)

V1 红线测试 (test_engineering_redlines.py) 继续生效, 扫描所有 backend .py 源文件. V3 新增 `app/ai/*.py` 也被扫描.

---

## 6. 回归保护

### 严格保护

- V1 76 tests 不能动
- V2 123 tests 不能动
- V1 BHI / Risk 算法不能改
- V2 Retrofit Priority / Rule Engine 不能改
- Context Builder 必须复用 V1/V2 service, 不能复制实现

### 任何 V3 改动若导致 V1/V2 测试 fail → 立即修复

---

## 7. CI 集成

`.github/workflows/ci.yml` 扩展:

```yaml
backend job:
  - pytest tests/ -v
  - 期望 278 passed
frontend job:
  - npx tsc --noEmit
  - npm run test:run
  - npm run build
  - 期望 60 tests passed
```

---

**文档版本**：v0.1 · Phase 5 V3
**最后更新**：2026-09-15
**状态**：Implemented & tested
