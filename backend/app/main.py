"""
BuildHealth FastAPI Application
Phase 0: 仅初始化 + 健康检查
Phase 1: 挂载完整 API 路由
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="BuildHealth API",
    description="既有建筑健康监测与智能更新决策平台 · Phase 0 Skeleton",
    version="0.0.1",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS（开发期放开 Vite 默认端口）
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
    """根路径 - 项目标识"""
    return {
        "project": "BuildHealth",
        "full_name": "Existing Building Health Monitoring & Intelligent Retrofit Decision Platform",
        "phase": "Phase 0 - Project Initialization",
        "status": "skeleton",
        "version": "0.0.1",
        "notice": "All data is simulated. Not a national or industry standard.",
    }


@app.get("/api/health")
def health_check():
    """健康检查端点"""
    return {
        "status": "ok",
        "phase": "Phase 0",
        "components": {
            "api": "ok",
            "database": "not_initialized",
            "analytics": "not_initialized",
        },
    }


# Phase 1: 在此挂载完整路由
# from app.api import buildings, components, sensors, monitoring, health, risk, analytics
# app.include_router(buildings.router, prefix="/api/buildings", tags=["buildings"])
# app.include_router(components.router, prefix="/api/components", tags=["components"])
# app.include_router(sensors.router, prefix="/api/sensors", tags=["sensors"])
# app.include_router(monitoring.router, prefix="/api/monitoring", tags=["monitoring"])
# app.include_router(health.router, prefix="/api/health", tags=["health"])
# app.include_router(risk.router, prefix="/api/risk", tags=["risk"])
# app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
