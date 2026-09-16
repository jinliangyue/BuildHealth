"""
Local computation benchmark (development only)
==============================================

Measures, per request path:
  * number of SQL statements issued
  * number of run_anomaly_detection invocations
  * elapsed wall time (median of N runs)

Run against the local SQLite development database:

    python -m scripts.benchmark_computations

This is a LOCAL DEVELOPMENT BENCHMARK on simulated data. It is not a
production performance guarantee, and the timings are noisy on a shared
8 GB machine — the query and invocation counts are the stable signal.
"""
import statistics
import sys
import time
from pathlib import Path
from typing import Callable, Dict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import event  # noqa: E402

from app.ai.context_builder import build_engineering_context  # noqa: E402
from app.db import models as m  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.services import assessment as A  # noqa: E402
from app.services import retrofit_service as R  # noqa: E402

_queries = {"n": 0}
_calls = {"n": 0}

event.listen(
    engine,
    "before_cursor_execute",
    lambda *a, **kw: _queries.__setitem__("n", _queries["n"] + 1),
)

_original_run_anomaly_detection = A.run_anomaly_detection


def _counting_run_anomaly_detection(*args, **kwargs):
    _calls["n"] += 1
    return _original_run_anomaly_detection(*args, **kwargs)


A.run_anomaly_detection = _counting_run_anomaly_detection
R.assessment_svc.run_anomaly_detection = _counting_run_anomaly_detection


def bench(label: str, fn: Callable[[], object], reps: int = 5) -> Dict:
    times = []
    for _ in range(reps):
        _queries["n"] = 0
        _calls["n"] = 0
        t0 = time.perf_counter()
        fn()
        times.append((time.perf_counter() - t0) * 1000)
    result = {
        "label": label,
        "queries": _queries["n"],
        "anomaly_calls": _calls["n"],
        "median_ms": round(statistics.median(times), 1),
        "min_ms": round(min(times), 1),
    }
    print(
        f"{label:42s} queries={result['queries']:3d}  "
        f"anomaly_calls={result['anomaly_calls']}  "
        f"median={result['median_ms']:7.1f} ms  min={result['min_ms']:7.1f} ms"
    )
    return result


def main() -> None:
    session = SessionLocal()
    try:
        n_buildings = session.query(m.Building).count()
        print(f"=== Local benchmark · {n_buildings} buildings ===")
        bench("AI context build (building 1)", lambda: build_engineering_context(session, 1))
        bench("GET /api/dashboard/summary", lambda: A.get_dashboard_summary(session))
        bench("GET /api/buildings/overview", lambda: A.get_buildings_overview(session))
        bench("GET /api/retrofit/overview", lambda: R.get_retrofit_overview(session))
        bench("GET /api/buildings/1/retrofit", lambda: R.get_retrofit_decision(session, 1))
    finally:
        session.close()


if __name__ == "__main__":
    main()
