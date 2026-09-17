# 22 · Overnight Engineering Sprint

> 一次夜间自主工程强化。目标不是增加功能，而是把已经功能完备的
> BuildHealth 推进到工程质量、可维护性和文档完整度更成熟的状态。

**起始 commit**：`3fea1c2 test: finalize BuildHealth Phase 6B acceptance`
**起始时间**：2026-09-16 夜
**基线测试**：Backend 371 passed · Frontend 78 passed · TypeScript 0 errors · build PASS · API smoke 14/14

---

## 1. 约束（本次 Sprint 全程遵守）

- 不破坏 V1 / V2 / V3 / V3.1 / V3.2 已有功能
- 不修改或删除工程安全边界（redlines / disclaimer / professional review）
- 不进入 Phase 6C，不新增大型功能
- 不实现：Conversation / SSE / Agent / MCP / function calling / BIM / GIS /
  IoT / MQTT / vector DB / internet search / 自动结构设计 / 自动安全鉴定
- 不引入无必要的新依赖，不升级 lockfile
- 不进行大规模架构重构
- 不为通过测试而弱化断言
- 保留 Engineering Evidence 与 Knowledge Evidence 的严格区分
- 模拟数据继续明确标记 Simulated
- 所有工程评价仍是 prototype / decision-support
- 本机 8GB M2 Air：所有大型任务串行执行

---

## 2. 阶段计划

| 阶段 | 内容 | 状态 |
|---|---|---|
| Step 0 | 建立基线 + 本文件 | 完成 |
| Step 1 | 全项目工程质量审计（frontend / backend / 安全） | 进行中 |
| Step 2 | 修复最多 5 个最高价值问题 | 待办 |
| Step 3 | 演示体验强化（小范围高价值） | 待办 |
| Step 4 | README / 项目说明强化 | 待办 |
| Step 5 | 演示流程文档（已移出公开仓库） | 待办 |
| Step 6 | `scripts/verify.sh`（若成本低） | 待办 |
| Step 7 | 完整回归测试（串行） | 待办 |
| Step 8 | Git 提交（不改 f27f6f7 / 3fea1c2） | 待办 |

---

## 3. Step 1 审计结果

### 3.1 已确认健康的部分（未改动）

| 项 | 结论 |
|---|---|
| `useApi` 三态封装 | loading / error / data 统一，页面无自行 fetch |
| `api/client.ts` | 统一 baseURL + 错误拦截，无重复请求逻辑 |
| 显式 `any` | 0 处 |
| `console.*` | 仅 ErrorBoundary 1 处（有意，带注释） |
| TODO / FIXME / HACK | 0 处 |
| `print()` 调试残留 | 0 处 |
| XSS 载体 | 无 `dangerouslySetInnerHTML` / `innerHTML` / `eval` |
| 安全红线 | 43 条禁止短语完整；两个 provider 都强制 disclaimer |
| RAG 确定性 | `app/knowledge/` 内无 random / shuffle / seed |
| 样式风格 | 无 gradient / glow / neon，无装饰性动画 |
| 空状态 | Buildings / Dashboard / RetrofitDecision 均有处理 |

### 3.2 发现的问题

| # | 问题 | 级别 |
|---|---|---|
| 1 | BHI 风险档位（90/75/60）在 4 个前端文件中各写一份；检测阈值在 DataSettings 再写一份 | P1 |
| 2 | 同一风险等级在两个页面用了不同颜色（DataSettings HighRisk `#DC2626` vs 全局 `#EF4444`） | P1 |
| 3 | `frontend/src/pages/Settings.tsx` 是 Phase 0 占位残留，无任何引用 | P2 |
| 4 | RetrofitDecision 用 `<LoadingState>` 渲染空结果（语义错误，会给用户"还在加载"的错觉） | P2 |
| 5 | AI Assistant 文案写 Max 2000 chars，但 textarea 无 `maxLength`（后端确实限制 2000，前端不拦会得到 422） | P2 |
| 6 | 聚合接口逐建筑调用分析函数（N+1 形态） | 已知，不修 |
| 7 | 改造建议实时计算不落库（`retrofit_recommendations` 表为空） | 设计决定，代码内有注释 |

### 3.3 明确跳过的问题及原因

- **N+1（#6）**：修它需要把 per-building 分析批量化，属于架构改动。
  当前 3 栋建筑无实际影响，写入 README Roadmap。
- **把参数镜像改为 API 下发（#1 的彻底解法）**：`BHI_WEIGHTS` 被
  BhiRadar 图表 + 4 个页面同步使用，改成异步获取会让图表需要加载态，
  属于重构且有演示回归风险。本次改为「单一常量模块 + 跨端一致性测试」。

---

## 4. Step 2 修复记录

修复 5 项（问题 #1-#5），全部小范围、可验证：

1. **参数单一来源 + 一致性测试**
   - 在 `frontend/src/types/api.ts` 集中 `BHI_RISK_BANDS` / `DETECTION_THRESHOLDS` /
     `RETROFIT_PRIORITY_HIGH_MIN` 与 `bhiRiskBandLabel` / `formatThreshold` 两个纯函数
   - RiskHealth / Dashboard / DataSettings / RetrofitDecision 改为引用常量
   - 新增 `backend/tests/test_frontend_parameter_consistency.py`（5 tests）：
     解析前端常量，用 `classify_risk` / `map_priority_level` **行为探针**比对，
     而非重抄字面量。已用变异测试验证该守卫真的会失败
   - 新增 `frontend/tests/EngineeringParameters.test.ts`（10 tests）锁定档位
     铺满 [0,100] 无缝无叠，以及格式化输出与改造前逐字一致

2. **修复风险颜色跨页不一致**：DataSettings 的 HighRisk 由 `#DC2626`
   统一为全局 `#EF4444`

3. **删除死文件** `frontend/src/pages/Settings.tsx`

4. **RetrofitDecision 空态**改用 `EmptyState`，并给出可操作提示

5. **AI Assistant** textarea 补 `maxLength={2000}`，与后端 `AIAskRequest` 对齐

---

## 5. Step 3-6 记录

### Step 3 演示体验

审计结论：现有页面已经具备完整工程叙事，`BuildingDetail` 一页即覆盖
Summary → Health → Dimensions → Monitoring → Alerts → Sensors → Retrofit → AI。
样式干净，无 cyberpunk / 装饰性动画。SimulatedBanner 全局常驻。

唯一高价值缺口：**首次打开的人看不到分析链路**。新增
`frontend/src/components/layout/WorkflowStrip.tsx`，在 Dashboard 顶部
展示 Building → Monitoring → Anomaly → Health & Risk → Retrofit → AI Explanation，
每步可点击。组件不渲染任何工程数据（有测试断言其文本不含两位数）。
另将 Dashboard 副标题改为注明 prototype decision support。

### Step 4 README

新增：工程问题表、核心工作流图、工程分析方法（异常检测三方法 / BHI 五维度
权重表 / 风险四档 + 覆盖规则 / RP-v1.0 + REC-v1.0 + 证据链）、一键验证章节、
Roadmap（含明确不做清单）。定位开篇明确为
土木工程 × 工程数据 × AI 数字化 × 工程决策支持。

### Step 5 演示说明

新增了一份演示流程文档：30 秒 / 1 分钟 / 3 分钟三版介绍、3 分钟完整
六站 Demo 流程、5 个最值得展示的功能、10 个预期提问 + 技术解释要点、
7 条不能声称的内容。全部基于真实实现（演示数据为 3 栋建筑 / 15 传感器 /
1350 条记录 / 187 条告警）。该文档属于演示材料，已于 2026-09-17 移出
公开仓库，使公开叙事保持纯工程视角。

### Step 6 验证脚本

新增 `scripts/verify.sh`，串行执行 backend tests → frontend tests → tsc →
production build，支持 `--skip-build`。无新依赖，已被本次最终回归实际执行。

---

## 6. Step 7 最终回归

`bash scripts/verify.sh` 一次通过（串行，脚本自身也得到验证）：

| 阶段 | 结果 |
|---|---|
| Backend tests | 376 passed |
| Frontend tests | 14 files / 92 passed |
| TypeScript | 0 errors |
| Production build | ✓ 714 modules · built in 2.19s |
| **脚本退出码** | **0 · ALL CHECKS PASSED** |

API smoke test（uvicorn 实跑）：15 个端点全部 200，含 retrofit detail。
AI 端点验证 building 3：`evidence`(工程数据) 9 条、`knowledge_evidence` 3 条，
两者独立，disclaimer 强制生效。

对比基线：Backend 371 → 376（+5），Frontend 78 → 92（+14）。新增测试均
对应本次改动，无删除或弱化任何既有断言。

---

## 7. Step 8 提交

`f27f6f7` 与 `3fea1c2` 保持不变。本次改动分两个 commit：

- `feat: improve BuildHealth engineering readiness`（代码 + 一致性测试 + 验证脚本）
- `docs: improve BuildHealth project presentation`（README + 演示材料 + 本文件）

提交前已确认无 secrets / .env / API key / 临时文件 / node_modules / 构建产物。

