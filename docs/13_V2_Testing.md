# 13 · V2 Testing V2 测试策略

> Phase 4 V2 测试覆盖矩阵与边界值
> Retrofit Decision Support 测试设计

**文档版本**：v0.1 · Phase 4 V2
**最后更新**：2026-09-15
**状态**：Implemented & tested

---

## 1. 测试目标

- **V1 回归**: 76 个 V1 backend 测试 + 30 个 V1 frontend 测试必须全部通过
- **V2 新增**: 至少 100 个 V2 新测试
- **Engineering Realism Redlines**: 至少 30 个红线扫描测试
- **覆盖率**: 边界值 (0/59/60/74/75/89/90/100) 全部覆盖

---

## 2. Backend 测试

### V1 保留 (76 tests · 0 改动)

| 文件 | 测试数 | 主题 |
|---|---|---|
| test_skeleton.py | 3 | FastAPI 启动 |
| test_database.py | 8 | ORM + FK + cascade |
| test_anomaly.py | 14 | 3 种异常检测方法 |
| test_health.py | 17 | BHI + 5 维度 |
| test_risk.py | 13 | 风险分级边界 |
| test_api.py | 13 | 9 个 V1 端点 |
| test_buildings_overview.py | 8 | 跨建筑聚合 |

### V2 新增 (~120 tests · 5 文件)

| 文件 | 测试数 | 主题 |
|---|---|---|
| test_priority.py | 45 | RP-v1.0 加权 + 边界 + trend + validation |
| test_recommendation_rules.py | 21 | 5 条 rule + evidence |
| test_retrofit_service.py | 17 | service 编排 + ranking + disclaimer |
| test_retrofit_api.py | 12 | 3 个 V2 端点 |
| test_engineering_redlines.py | 30+ | 红线扫描 (parametrized forbidden phrases) |

**Backend 总计: 199 tests**

---

## 3. Frontend 测试

### V1 保留 (30 tests · 0 改动)

| 文件 | 测试数 | 主题 |
|---|---|---|
| RiskLevel.test.ts | 7 | 风险分级 |
| StateViews.test.tsx | 10 | UI 状态组件 |
| Charts.test.tsx | 7 | ECharts 组件 |
| ErrorBoundary.test.tsx | 2 | 错误边界 |
| useApi.test.tsx | 4 | useApi hook |

### V2 新增 (20 tests · 3 文件)

| 文件 | 测试数 | 主题 |
|---|---|---|
| PriorityScoreCard.test.tsx | 6 | Score + level + Prototype disclaimer |
| PriorityRankingList.test.tsx | 7 | 排序 + 选中 + 空状态 |
| RecommendationDetail.test.tsx | 7 | 5 维度 + evidence + disclaimer |

**Frontend 总计: 50 tests**

---

## 4. 边界值覆盖矩阵

### Priority Score 边界 (11 个)

| Score | Expected Level | 测试位置 |
|---|---|---|
| 0 | Low | test_priority_score_boundaries[0] |
| 1 | Low | test_priority_score_boundaries[1] |
| 50 | Low | test_priority_score_boundaries[50] |
| 59 | Low | test_priority_score_boundaries[59] |
| 60 | Medium | test_priority_score_boundaries[60] |
| 74 | Medium | test_priority_score_boundaries[74] |
| 75 | High | test_priority_score_boundaries[75] |
| 89 | High | test_priority_score_boundaries[89] |
| 90 | Very High | test_priority_score_boundaries[90] |
| 99 | Very High | test_priority_score_boundaries[99] |
| 100 | Very High | test_priority_score_boundaries[100] |

### map_priority_level 边界 (8 个)

| Score | Expected |
|---|---|
| 0 | Low |
| 59.99 | Low |
| 60 | Medium |
| 74.99 | Medium |
| 75 | High |
| 89.99 | High |
| 90 | Very High |
| 100 | Very High |

### Input Validation (10 个)

- invalid risk_level → raise
- trend_score < 0 → raise
- trend_score > 100 → raise
- component_importance > 100 → raise
- invalid urgency → raise
- invalid cost_level → raise
- map_priority_level out of range → raise
- ... etc

---

## 5. 回归保护

### V1 76/30 tests

- 每次 PR 必须全部通过
- 任何 V1 测试失败视为 Phase 4 实现错误
- 修改 V1 行为必须有 explicit reason 注释

### BHI / Risk 算法稳定性

- BHI_CALCULATION_VERSION 保持 "BHI-v1.0"
- RISK 边界值 0/60/75/90 保持不变
- test_risk.py 11 个 boundary 测试不可删除

---

## 6. Engineering Realism Redlines (新)

`backend/tests/test_engineering_redlines.py` 强制执行:

### 扫描禁止词 (~25 个 parametrize)

```
"符合国家标准"
"符合行业标准"
"complies with national standard"
"complies with industry standard"
"GB/T 50292"
"JGJ 125"
"legally binding safety grade"
"法定建筑安全等级"
"法定建筑等级"
"real building safety grade"
"auto structural design"
"automatic reinforcement design"
"automated structural design"
"自动结构设计"
"自动钢筋设计"
"building will collapse"
"structure will fail"
"建筑即将倒塌"
"结构即将失稳"
"AI predicts structural failure"
... (+ 5 more)
```

任何 backend .py 源文件出现这些词 → 整个测试套件失败.

### Disclaimer 强制

- `RETROFIT_DISCLAIMER` 必须含 "Prototype", "RP-v1.0", "engineering decision support", "professional review", "structural reinforcement plan"
- Disclaimer 自身不得含 "legal" / "statutory" / "certified" / "compliant"

### Model Field 强制

- RetrofitRecommendation 必须含 calculation_version 列
- EngineeringNote 必须含 text + source 列

### Version 常量强制

- BHI_CALCULATION_VERSION == "BHI-v1.0"
- RETROFIT_PRIORITY_VERSION == "RP-v1.0"
- RECOMMENDATION_RULES_VERSION == "REC-v1.0"

---

## 7. 不测的内容 (Out of Scope)

- LLM 集成 (Phase 5+ 计划)
- IoT 硬件 (Phase 5+ 计划)
- BIM / GIS / 3D (不做)
- 真实造价数据库 (Phase 5+)
- 用户权限 / 多用户 (Phase 5+)
- 云部署 / 支付 (不做)
- 移动端原生 UI (Web 响应式)
- WebSocket 推送 (V1 用 30s 轮询)
- 国际化和多语言

---

## 8. CI 集成

`.github/workflows/ci.yml`:

```yaml
backend job:
  - pytest tests/ -v
frontend job:
  - npx tsc --noEmit
  - npm run test:run
  - npm run build
```

V2 起,CI 必须 199 backend + 50 frontend tests 全绿.

---

**文档版本**：v0.1 · Phase 4 V2
**最后更新**：2026-09-15
**状态**：Implemented & tested
