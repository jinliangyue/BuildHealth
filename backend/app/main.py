"""
BuildHealth FastAPI Application
Phase 1 实现 · 9 个业务端点 + health check
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="BuildHealth API",
    description="既有建筑健康监测与智能更新决策平台 · Phase 1",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
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


@app.get("/")
def root():
    return {
        "project": "BuildHealth",
        "full_name": "Existing Building Health Monitoring & Intelligent Retrofit Decision Platform",
        "phase": "Phase 1 - V1 Core Backend & Data Layer",
        "version": "0.1.0",
        "notice": "All data is simulated (Simulated Data). "
                  "BHI uses Prototype Design Parameters (v1.0), not a national or industry standard. "
                  "Risk classification is Prototype Risk Classification, "
                  "not a legally binding building safety grade.",
    }


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "phase": "Phase 1",
        "components": {
            "api": "ok",
            "database": "ok",
            "analytics": "ok",
        },
    }


# Phase 1: 挂载完整路由
from app.api import buildings, sensors, monitoring, health, risk, dashboard

app.include_router(buildings.router, prefix="/api")
app.include_router(sensors.router, prefix="/api")
app.include_router(monitoring.router, prefix="/api")
app.include_router(health.router, prefix="/api")
app.include_router(risk.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
