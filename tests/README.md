# BuildHealth · tests/

项目根的 `tests/` 目录**仅保留 README 占位**;实际测试在两个
独立位置:

- **`backend/tests/`** — pytest,Python。33 个 `test_*.py` + conftest.py
  + `__init__.py`;`408` 个 `def test_` 函数。收集数取决于可选的 deepeval
  装没装:CI 里没装 → 收集 **474**(473 passed + 1 skipped,
  `test_deepeval_integration.py` 整模块 `importorskip` 只计 1 个 skip);
  本地装了 → 收集 **483**(478 passed + 5 skipped,其中 5 个 live 用例
  需 `OPENAI_API_KEY`)。
- **`frontend/tests/`** — vitest + Testing Library,TypeScript/TSX。
  15 个测试文件 / 97 个 `it(...)` 用例。

## 不再依赖仓库根 tests/

本目录是 Phase 0 早期占位的产物。Phase 1 后**所有测试都迁到了
靠近源码的位置**,以避免 test 跨模块相互 import。本目录保留
README 是为了避免 git 历史丢失,可与 `BuildHealth-prep-notes/` 中
旧决策材料交叉引用时定位原文。

## 与 verify.sh 的配合

`scripts/verify.sh` 串行运行:
1. `cd backend && venv/bin/python -m pytest tests -q`
2. `cd frontend && npx vitest run`
3. `cd frontend && npx tsc --noEmit`(自 2026-10-16 起覆盖 tests/)
4. `cd frontend && npm run lint`(自 2026-10-16 起)
5. `cd frontend && npm run build`

任何一步失败 → verify.sh 退出非 0。
