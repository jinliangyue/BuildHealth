"""
配置管理
========

本项目**显式不使用** pydantic-settings / .env 文件,所有可调参数以
Python 常量形式硬编码在此模块顶部 — 保证本地复现性 + 无秘密泄露
风险。

工程参数(BHI 权重 / 风险边界 / 优先权阈值 / anomaly 阈值)全部带
版本号(BHI v1.0 / RP-v1.0 / Risk v1.0)以便参数对比与回滚。

变更历史:Phase 0 (2026-09-15) 占位 → Phase 1 (2026-09-22) 完整
实现 → Phase 6B (2026-09-26) 加入 AI_PROVIDER 系列 + Real LLM
支持。本模块从未再被改"回 Phase 0"。
"""
import os
from typing import Optional

# BHI 权重版本（Prototype Design Parameters v0.1）
BHI_WEIGHTS_V0_1 = {
    "structural_safety": 0.40,
    "facility_condition": 0.20,
    "environmental_quality": 0.15,
    "energy_performance": 0.10,
    "fire_safety": 0.15,
}

CURRENT_BHI_VERSION = "v0.1"

# 风险等级阈值（Prototype Risk Classification v0.1）
RISK_THRESHOLDS = {
    "Normal": (90, 100),
    "Attention": (75, 89),
    "Abnormal": (60, 74),
    "HighRisk": (0, 59),
}

# 监测指标阈值（异常检测用）
SENSOR_THRESHOLDS = {
    "crack_width": {
        "high": {"value": 0.30, "unit": "mm", "severity": "high"},
        "medium": {"value": 0.20, "unit": "mm", "severity": "medium"},
    },
    "tilt": {
        "high": {"value": 4.0, "unit": "‰", "severity": "high"},
        "medium": {"value": 3.0, "unit": "‰", "severity": "medium"},
    },
    "temperature": {
        "medium": {"value": 40.0, "unit": "℃", "severity": "medium"},
    },
    "humidity": {
        "low": {"value": 80.0, "unit": "%", "severity": "low"},
    },
    "electricity": {
        # 用电暂无硬阈值，由变化率检测
    },
}

# 数据库路径（绝对路径 · 避免 cwd 变化导致无法定位）
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(os.path.dirname(_BACKEND_DIR), "data")
DATABASE_URL = f"sqlite:///{os.path.join(DATA_DIR, 'buildhealth.db')}"

# 确保 data 目录存在
os.makedirs(DATA_DIR, exist_ok=True)


# =================================================================
# AI Engineering Assistant · Phase 5 V3
# =================================================================
# Provider 默认 mock. 真实 LLM provider 留待 Phase 6+ 实现.
# 不读 .env, 不安装 SDK. 全部硬编码, 保证本地可运行且无 secret.
AI_PROVIDER = "mock"
AI_MODEL = "mock-deterministic-v1"
AI_VERSION = "AI-v1.0"
AI_DISCLAIMER = (
    "AI Engineering Assistant output is engineering decision support only, "
    "based on Prototype BHI / Risk / Priority parameters. It does not "
    "constitute professional engineering appraisal, automatic structural "
    "design, or a building safety certification. All outputs require "
    "qualified professional review."
)


# =================================================================
# AI Engineering Assistant · Phase 6A · Real LLM Provider
# =================================================================
# 默认 mock provider, 无任何 key 也能跑. 设置后切到真实 LLM.
# 不在源码 / .env.example / Git 中放置真实 key.
# AIProvider: "mock" (default) | "openai-compatible"
# 当 AI_PROVIDER=openai-compatible 时, AI_API_KEY 和 AI_BASE_URL 必填.
import os

AI_PROVIDER = os.getenv("AI_PROVIDER", "mock").strip().lower()
AI_MODEL = os.getenv("AI_MODEL", "mock-deterministic-v1").strip()
AI_BASE_URL = os.getenv("AI_BASE_URL", "").strip()
AI_API_KEY = os.getenv("AI_API_KEY", "").strip()
AI_REQUEST_TIMEOUT = float(os.getenv("AI_REQUEST_TIMEOUT", "30"))
AI_MAX_TOKENS = int(os.getenv("AI_MAX_TOKENS", "1500"))
AI_TEMPERATURE = float(os.getenv("AI_TEMPERATURE", "0.2"))


def validate_ai_config() -> Optional[str]:
    """Phase 6A 启动时 sanity check. 返回 None 表示 OK, 否则返回错误描述."""
    if AI_PROVIDER == "openai-compatible":
        if not AI_API_KEY:
            return (
                "AI_API_KEY is not set. Either set it in the environment "
                "or switch to AI_PROVIDER=mock."
            )
        if not AI_BASE_URL:
            return (
                "AI_BASE_URL is not set. Either set it in the environment "
                "or switch to AI_PROVIDER=mock."
            )
    return None
