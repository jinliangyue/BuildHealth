# BuildHealth · scripts/

项目根目录的"开发期工具脚本"。**Phase 6B**起已完整实装,
不再是 Phase 0 占位。

## 实装内容

| 脚本 | 用途 |
|---|---|
| `verify.sh` | 一键串行验证(后端 pytest + 前端 vitest + tsc + eslint + 生产构建)。本地与 CI 都调用此脚本。 |
| `verify_benchmarks.sh` | 重跑 9 项性能 benchmark(参考 docs/28 §17),输出数字与 docs/27 对比。 |

## 与 backend/scripts/ 的区别

`backend/scripts/` 是 Python 工程脚本(数据生成 + 评估跑分),需要
`backend/venv/bin/python` 解释器;本目录是 shell 脚本入口,不依赖
Python 解释器。两边职责清晰:

- `backend/scripts/seed_data.py` — 生成模拟数据(默认 30 栋 / 180 天 /
  27,000 记录)
- `backend/scripts/import_csv.py` — CSV → DB 适配层
- `backend/scripts/run_retrieval_eval.py` — 50 query 检索评估
- `backend/scripts/run_llm_eval.py` — 30 query LLM 输出评估 + DeepEval
  4 工业指标(可选 deepeval)

历史说明:`recompute_health.py` 与 `verify_invariants.py` 曾列入
Phase 1 计划脚本,**全仓库已确认不存在**(BHI 重算通过 API endpoint
触发;禁词扫描在 CI 通过 `npm run lint` + 后端测试覆盖)。
