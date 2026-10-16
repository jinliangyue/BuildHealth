"""
BuildHealth FastAPI Application
Phase 1 V1 + Phase 4 V2 retrofit + Phase 5 V3 AI Engineering Assistant
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: bring the on-disk schema up to date on startup.

    Init DB *here* (not at module-import time) for two reasons:

    1. Idempotent ``CREATE TABLE IF NOT EXISTS`` so models added after
       the last ``seed_data.py`` run (e.g. AuditLog in commit 4c215de)
       appear without wiping data. See ``app.db.session.init_db`` for
       the full rationale.
    2. Tests bypass this entirely: ``tests/conftest.py`` builds the
       TestClient with ``yield TestClient(app)`` (no ``with`` context),
       so lifespan never fires during the test suite. Test fixtures
       own their own schema via the ``test_engine`` fixture. This
       keeps the existing in-memory SQLite tests unaffected.
    """
    from app.db.session import init_db
    init_db()
    yield


app = FastAPI(
    title="BuildHealth API",
    description="既有建筑健康监测与智能更新决策平台 · Phase 5 V3",
    version="0.3.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Audit middleware (Phase 7): writes one row per HTTP request to
# `audit_logs`. Registered *after* CORS so that preflight OPTIONS
# requests don't generate audit rows (CORS handles them before
# reaching user code). Exempt paths (/api/health, /docs, /redoc,
# /openapi.json) are listed inside AuditMiddleware.
from app.audit.middleware import AuditMiddleware  # noqa: E402
app.add_middleware(AuditMiddleware)


@app.get("/")
def root():
    return {
        "project": "BuildHealth",
        "full_name": "Existing Building Health Monitoring & Intelligent Retrofit Decision Platform",
        "phase": "Phase 5 - V3 AI Engineering Assistant",
        "version": "0.3.0",
        "notice": (
            "All data is simulated (Simulated Data). "
            "BHI uses Prototype Design Parameters (v1.0), not a national or industry standard. "
            "Risk classification is Prototype Risk Classification, "
            "not a legally binding building safety grade. "
            "Retrofit priority uses Prototype Retrofit Priority Parameters (RP-v1.0) "
            "and is engineering decision support only. "
            "AI Engineering Assistant is an explanation layer (Mock provider by default); "
            "it does not perform engineering calculation or replace qualified professionals."
        ),
    }


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "phase": "Phase 5 - V3",
        "components": {
            "api": "ok",
            "database": "ok",
            "analytics": "ok",
            "retrofit_decision": "ok",
            "ai_assistant": "ok (mock provider)",
        },
    }


# Phase 1: 挂载完整路由
from app.api import buildings, sensors, monitoring, health, risk, dashboard
from app.api import retrofit as retrofit_api
from app.api import ai as ai_api
from app.api import parameters as parameters_api
from app.audit import router as audit_router

app.include_router(buildings.router, prefix="/api")
app.include_router(sensors.router, prefix="/api")
app.include_router(monitoring.router, prefix="/api")
app.include_router(health.router, prefix="/api")
app.include_router(risk.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(retrofit_api.router, prefix="/api")
app.include_router(ai_api.router, prefix="/api")
app.include_router(parameters_api.router, prefix="/api")
app.include_router(audit_router.router)  # already prefixed with /api/audit


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
