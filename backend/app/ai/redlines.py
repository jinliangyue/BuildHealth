"""
AI Redlines · Phase 5 + Phase 6A
=================================

公共禁词列表 + 扫描函数. 供 real_provider / tests 共用.

Phase 6A 真实 LLM 输出必须经本模块扫描, 发现禁词抛 AIProviderError("safety_violation").
"""
from typing import List


# 禁词清单 (case-insensitive 匹配)
# 1. 不得声称安全 / 倒塌
# 2. 不得声称完成工程鉴定
# 3. 不得自动设计
# 4. 不得假冒专业检查
# 5. 不得声称符合标准
# 6. 不得编造绝对结论
AI_FORBIDDEN_PHRASES: List[str] = [
    # 1
    "this building is safe",
    "this building is unsafe",
    "building will collapse",
    "structure will fail",
    "structure will collapse",
    "structural failure is certain",
    "ai predicts structural failure",
    # 2
    "automatic structural appraisal completed",
    "structural appraisal completed",
    "official safety certification",
    "safety certification issued",
    "official certification",
    "real-world deployment occurred",
    "deployed in production",
    # 3
    "automatic reinforcement design",
    "ai-designed reinforcement",
    "auto-generated structural design",
    "auto-generated reinforcement",
    "ai designed the reinforcement",
    # 4
    "professional inspection completed",
    "engineer has approved",
    "engineer approved",
    # 5
    "complies with national standard",
    "符合国家标准",
    "符合行业标准",
    "符合国标",
    # 6
    "guaranteed safe",
    "guaranteed to fail",
    "definitely safe",
    "absolutely safe",
    "this is a real building",
    "this is a real monitoring",
]


def scan_redlines(text: str) -> List[str]:
    """Return list of forbidden phrases found in text (case-insensitive)."""
    if not text:
        return []
    lower = text.lower()
    return [p for p in AI_FORBIDDEN_PHRASES if p in lower]


def scan_response_for_redlines(
    answer: str,
    key_findings_text: str = "",
    recommended_actions_text: str = "",
    evidence_descriptions: str = "",
) -> List[str]:
    """Scan all parts of an AI response and return unique forbidden phrases found."""
    all_text = " ".join([
        answer or "",
        key_findings_text or "",
        recommended_actions_text or "",
        evidence_descriptions or "",
    ])
    return list(dict.fromkeys(scan_redlines(all_text)))
