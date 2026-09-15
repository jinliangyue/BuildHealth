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

# 数据库路径
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
DATABASE_URL = f"sqlite:///{os.path.join(DATA_DIR, 'buildhealth.db')}"
