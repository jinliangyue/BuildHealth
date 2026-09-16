# 27 · Overnight Sprint 3 · Final Engineering Optimization

> 最后一轮低风险工程性能优化，然后把 BuildHealth 封板到稳定、可展示状态。
> 不扩大项目范围，不引入新基础设施，不进入 Phase 6C。

**起始 commit**：`03114a4 docs: expand BuildHealth technical portfolio materials`
**起始时间**：2026-09-17
**基线**：Backend 401 · Frontend 97 · tsc 0 errors · build PASS · API smoke 19/19 · verify.sh PASS

---

## 1. 本轮目标

1. request-scoped anomaly detection reuse —— 同一请求内同一栋建筑的异常检测只算一次
2. 清掉 retrofit overview 剩余的逐建筑 N+1
3. 行为等价必须可证明
4. 完成后封板

约束：不引入 Redis / 缓存 / Celery / 消息队列 / 新依赖；不改数据库 schema；
不改 API response contract；不做大规模重构。

---

## 2. 审计：重复到底发生在哪

先测量再动手。给 `run_anomaly_detection` 加计数器，逐个请求路径数调用次数：

| 请求路径 | 优化前 anomaly 调用 | 说明 |
|---|---|---|
| `build_engineering_context(1)`（AI 链路） | **2** | 同一栋建筑算两遍 |
| `get_dashboard_summary` | 3 | 3 栋建筑各一次，无重复 |
| `get_buildings_overview` | 3 | 同上 |
| `get_retrofit_overview` | 3 | 同上 |
| `generate_recommendations(1)` | 1 | 无重复 |

结论和预期不同：**聚合接口本来就没有重复计算**（Sprint 2 已经清理过）。
真正重复的是 AI 链路：

```
build_engineering_context()
  ├── run_anomaly_detection()          ← 第 1 次
  ├── compute_health_assessment()
  └── get_retrofit_decision()
        └── generate_recommendations()
              └── run_anomaly_detection()  ← 第 2 次（结果被丢掉）
              └── compute_health_assessment()  ← 也算了两遍
```

同时 `build_engineering_context` 还有两处逐条查询：每个传感器一条监测记录查询，
以及 retrofit overview 里每栋建筑一条 recent-values 查询。

---

## 3. request-scoped reuse 的设计

新增请求作用域容器（`app/services/assessment.py`）：

```python
@dataclass
class BuildingAnalysis:
    building: m.Building
    components: List[m.Component]
    sensors: List[m.Sensor]
    series_map: Dict[str, List[Tuple[datetime, float]]]
    anomalies: List[Dict]
    health: Dict
    risk: Dict
```

两个构造入口：

- `analyze_building(session, building_id)` —— 单建筑，4 条查询
- `analyze_buildings(session, building_ids)` —— 多建筑，**固定 4 条查询**
  （buildings / components / sensors / series），异常检测与 BHI 在内存里逐栋算

然后沿调用栈向下传递：`generate_recommendations(..., analysis=None)` →
`get_retrofit_decision(..., analysis=None)` → `build_engineering_context` 内部使用。

设计要点：

- **这不是缓存**。它是随调用栈传递的普通对象，请求结束即释放。
  没有全局状态、没有 key 失效逻辑、没有第二个数据副本。
- **可选项，不破坏现有调用**。所有新参数默认 `None`，传 None 时
  行为与之前逐字节一致。单建筑端点、测试、脚本都不用改。
- **没有引入新的抽象层**。容器只是把原本散在三个函数里的中间结果放到一起。

同时修掉两处逐条查询：
- 新增 `load_records_by_sensor()`，context builder 一次读入本建筑所有传感器记录
- `_get_recent_values_by_sensor()` 在 retrofit overview 里跨全部建筑调用一次，
  再按建筑切分传入

---

## 4. Before / After

基准环境：本机 8GB M2 Air · SQLite · 3 栋建筑 / 15 传感器 / 1350 条记录 ·
取 5 次中位数。**这是本地开发基准，不是生产环境性能保证。**

| 请求路径 | 查询数 | anomaly 计算次数 | 中位耗时 |
|---|---|---|---|
| AI context build（building 1） | 16 → **7** | 2 → **1** | 59.0 → **31.5 ms** |
| GET /api/dashboard/summary | 7 → 7 | 3 → 3 | 82.1 → 81.0 ms |
| GET /api/buildings/overview | 4 → 4 | 3 → 3 | 81.9 → 82.2 ms |
| GET /api/retrofit/overview | 13 → **6** | 3 → 3 | 88.7 → 87.9 ms |
| GET /api/buildings/1/retrofit | 6 → 6 | 1 → 1 | 29.5 → 29.5 ms |

解读：

- **AI 链路是最大受益者**：查询数 -56%，异常检测 -50%，耗时 -47%。
  这正是原先重复计算的地方。
- **retrofit overview 查询数 -54%**，且现在与建筑数量无关（由测试锁定）。
- 三个聚合端点的 anomaly 调用维持 3 次（= 建筑数），这已是理论最小值：
  每栋建筑的异常检出结果不同，不能跨建筑复用。
- dashboard / overview 耗时基本不变，因为它本来就只算一次；
  它们的耗时由异常检测 CPU 主导（Sprint 2 已测：约 92%）。

---

## 5. 等价性验证

新增 `backend/tests/test_request_scoped_reuse.py`（11 tests）：

| 测试 | 断言 |
|---|---|
| `test_analysis_matches_individual_calls` | `analyze_building` 的 anomalies / health / risk 与逐函数调用完全相等 |
| `test_recommendations_with_analysis_equal_without` | 传/不传 analysis 的改造建议完全相同 |
| `test_retrofit_decision_with_analysis_equals_without` | 单建筑 decision 完全相同 |
| `test_retrofit_overview_equals_per_building_generation` | 聚合结果与逐建筑重算一致 |
| `test_context_builder_matches_manual_chain` | AI context 的 BHI / 异常总数与手工重算一致 |
| `test_retrofit_overview_unchanged_shape` | response shape 未变 |
| `test_ai_path_runs_anomaly_detection_once_per_building` | AI 链路异常检测恰好 1 次 |
| `test_aggregates_run_anomaly_detection_once_per_building` | 3 个聚合各恰好 N 次（N=建筑数） |
| `test_single_building_endpoint_runs_anomaly_detection_once` | 单建筑端点 1 次 |
| `test_retrofit_overview_query_count_does_not_grow` | 1 栋 vs 3 栋查询数相同 |
| `test_context_builder_query_count_does_not_grow` | 记录读取不随传感器数增长 |

唯一允许的差异是 `created_at`（`datetime.utcnow()` 生成的墙钟时间），
测试对此做了显式剥离并注明原因；其余字段必须逐字节相等。

**守卫有效性已用变异测试验证**：把 `context_builder` 里传下去的 analysis 去掉后，
`test_ai_path_runs_anomaly_detection_once_per_building` 立刻失败并报出
`anomaly detection ran 2 times`。这条测试不是摆设。

---

## 6. 新增测试数量

- Backend：401 → **412**（+11）
- Frontend：97 → 97（本轮未改前端）
- 新增基准脚本：`backend/scripts/benchmark_computations.py`

无删除测试、无弱化断言。

---

## 7. 为什么没有引入 Redis / 缓存 / Phase 6C

- **没有引入缓存**：本轮所有复用都是请求作用域的对象传递。Redis 或进程级缓存
  会引入失效策略、一致性风险和第二份状态，而当前瓶颈是单次请求内的重复计算，
  不是跨请求的重复计算 —— 用缓存解决是过度设计。
- **没有引入队列 / Celery**：分析是同步的、毫秒级的，没有异步化需求。
- **没有进入 Phase 6C**：多轮对话、SSE、Agent、MCP、function calling 都不是
  这个项目的短板。BuildHealth 的说服力来自工程深度和边界克制，不是功能数量。
- **没有改数据库 schema**：本轮只优化读取方式与计算复用，不动数据模型。

---

## 8. 技术债状态

本轮清掉：

- AI 链路重复异常检测（原 2 次 → 1 次）
- context builder 逐传感器记录查询
- retrofit overview 逐建筑 recent-values 查询（查询数不再随建筑数增长）

仍然保留（记录，不在本轮范围）：

1. dashboard 与 overview 各自独立重算异常检测 —— 不同 endpoint，无法在
   无缓存前提下共享
2. 改造建议实时计算不落库，无法做历史比对
3. 前端仍保留参数常量作为离线 fallback（正常路径已走 API）
4. 中文检索按单字切分，无词干化与同义词扩展
5. 单机形态：无认证、无限流、无审计日志
6. `RetrofitRecommendation` 表存在但未使用

---

## 9. 封板建议

建议封板。理由：

- 全部可执行验证通过（backend / frontend / tsc / build / API smoke / verify.sh）
- 本轮性能优化有真实测量数据支撑，且行为等价性有测试证明
- 剩余技术债都已被明确记录，且都不影响当前展示与演示
- 继续优化的收益递减：聚合端点已达每栋建筑一次计算、固定次数查询；
  再往下走要么引入缓存（违反本轮约束），要么改动数据模型

**封板状态**：稳定、可复现、可展示、可面试深挖。
