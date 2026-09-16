"""
配置管理 · Phase 0 占位
Phase 1 引入 pydantic-settings 加载 .env
"""
import os

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
