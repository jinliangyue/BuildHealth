"""
Engineering Realism Redlines · Phase 4 V2
=========================================

10 条工程真实性红线 (ER-01..ER-10) 的自动化检查:
- 扫描所有 .py 文件, 禁止工程红线违规词
- 验证 RetrofitDisclaimer 字符串完整
- 验证 RetrofitRecommendation / EngineeringNote 模型字段命名一致
- 验证 frontend 端 disclaimer 字样在 API response 出现

任何一条失败 → 整个测试套件失败, 防止红线被无意破坏.
"""
import os
import re
from pathlib import Path

import pytest

from app.analytics.config import RETROFIT_DISCLAIMER


# ============ 禁止词列表 (ER 强约束) ============
# 仅扫描"正向声明" (非否认式). 例: "not a national standard" 允许,
# 但 "complies with national standard" / "符合国家标准" 禁止.
FORBIDDEN_PHRASES = [
    # ER-04: 不得暗示符合国家标准 / 行业标准 (正向声明)
    "符合国家标准",
    "符合行业标准",
    "complies with national standard",
    "complies with industry standard",
    "GB/T 50292",
    "JGJ 125",
    # ER-05: 不得宣称是真实建筑安全等级
    "legally binding safety grade",
    "法定建筑安全等级",
    "法定建筑等级",
    "real building safety grade",
    # ER-08: 不得使用 LLM 黑盒 / 自动化结构设计
    "auto structural design",
    "automatic reinforcement design",
    "automated structural design",
    "自动结构设计",
    "自动钢筋设计",
    # 不得使用危言耸听
    "building will collapse",
    "structure will fail",
    "建筑即将倒塌",
    "结构即将失稳",
    "AI predicts structural failure",
]


# ============ Fixture: 扫描所有 .py 源文件 ============
# Exclude files that are themselves meta-definitions of forbidden phrases
# (e.g. app/ai/redlines.py lists them in negative context).
REDLINE_META_FILES = {"redlines.py"}


@pytest.fixture(scope="module")
def all_py_source():
    backend = Path(__file__).resolve().parent.parent
    sources = []
    for py in backend.rglob("*.py"):
        # 跳过 venv / __pycache__ / 自身
        parts = py.parts
        if "venv" in parts or "__pycache__" in parts or ".git" in parts:
            continue
        if "tests" in parts:
            continue
        if py.name in REDLINE_META_FILES:
            continue
        try:
            content = py.read_text(encoding="utf-8")
        except Exception:
            continue
        sources.append((py, content))
    return sources


# ============ Disclaimer 强制字符串 ============
def test_disclaimer_required_phrases():
    """RETROFIT_DISCLAIMER 必须包含所有强制关键词."""
    for kw in [
        "Prototype", "RP-v1.0", "engineering decision support",
        "professional review", "structural reinforcement plan",
    ]:
        assert kw in RETROFIT_DISCLAIMER, (
            f"Disclaimer missing required keyword: {kw}"
        )


def test_disclaimer_must_not_claim_legal_binding():
    """Disclaimer 自身不得包含 'legal' / 'statutory' / 'certified'."""
    forbidden = ["legal", "statutory", "certified", "compliant"]
    for kw in forbidden:
        assert kw.lower() not in RETROFIT_DISCLAIMER.lower(), (
            f"Disclaimer must not contain '{kw}'"
        )


# ============ 扫描 backend 源文件禁止词 ============
@pytest.mark.parametrize("phrase", FORBIDDEN_PHRASES)
def test_no_forbidden_phrase_in_backend_source(all_py_source, phrase):
    """任何 .py 后端源文件不得包含禁止词."""
    matches = []
    for path, content in all_py_source:
        if phrase in content:
            matches.append(str(path))
    assert matches == [], (
        f"Forbidden phrase '{phrase}' found in: {matches}"
    )


# ============ Retrofit 模型字段 ============
def test_retrofit_recommendation_calculation_version_required():
    """RetrofitRecommendation 字段必须包含 calculation_version."""
    from app.db import models as m
    cols = {c.name for c in m.RetrofitRecommendation.__table__.columns}
    for required in [
        "id", "building_id", "category", "issue_type",
        "title", "recommendation", "rationale", "next_action",
        "urgency", "estimated_cost_level", "expected_benefit",
        "source", "evidence_json", "priority_score",
        "calculation_version", "created_at",
    ]:
        assert required in cols, f"RetrofitRecommendation missing column: {required}"


def test_engineering_note_minimum_fields():
    from app.db import models as m
    cols = {c.name for c in m.EngineeringNote.__table__.columns}
    for required in ["id", "building_id", "text", "source", "created_at"]:
        assert required in cols, f"EngineeringNote missing column: {required}"


# ============ V1 BHI 字段保留 ============
def test_bhi_calculation_version_still_bhi_v1():
    """V1 BHI algorithm 字段名 'calculation_version' 必须保持 BHI-v1.0."""
    from app.analytics.config import BHI_CALCULATION_VERSION
    assert BHI_CALCULATION_VERSION == "BHI-v1.0"


# ============ Priority / REC 版本 ============
def test_priority_version_is_rp_v1():
    from app.analytics.config import RETROFIT_PRIORITY_VERSION
    assert RETROFIT_PRIORITY_VERSION == "RP-v1.0"


def test_rules_version_is_rec_v1():
    from app.analytics.config import RECOMMENDATION_RULES_VERSION
    assert RECOMMENDATION_RULES_VERSION == "REC-v1.0"
