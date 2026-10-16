# BuildHealth · data/

运行时数据目录(由应用自动维护,**不**通过 git 跟踪;`data/*.db`
在 `.gitignore` 中)。

## 当前内容

| 路径 | 大小 | 说明 |
|---|---|---|
| `buildhealth.db` | ~6.6 MB | SQLite 数据库。**9 张表**:buildings / components / sensors / monitoring_records / health_assessments / risk_alerts / retrofit_recommendations / engineering_notes / audit_logs。当前默认 seed = **30 栋建筑 / 27,006 条 monitoring_records**。 |

## 不存在(预期)

原 README 列出过 `raw/` 与 `exports/` 子目录 — 全仓库确认不存在,
**也未在 `.gitignore` 中**。如有工程化需求,后续按 `import_csv.py`
(commit 154558f)的 CSV 适配层扩展,不必预先创建空目录。

## 重建方式

```bash
cd backend
venv/bin/python -m scripts.seed_data   # 清库 + 重建(seed=42, 30 栋, 180 天)
# 或者 仅运行应用,会触发 init_db() 补全缺表(不自增 seed)
venv/bin/uvicorn app.main:app --reload
```

注意:`seed_data.py` 的 `wipe_database()` 会丢掉所有非 seed 写入
的数据(例如 audit_logs),不要在生产路径上调用。
