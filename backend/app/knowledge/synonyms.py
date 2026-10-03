"""
Engineering synonyms · BuildHealth Phase 7
============================================

Hand-curated synonym groups used by the tokenizer to expand a query
before it is matched against the chunk index.

Why hand-curated and not WordNet / HowNet:
  - The corpus is small (5 engineering docs). Maintenance cost is low
    and the precision of a curated list beats an off-the-shelf
    Chinese general-purpose resource.
  - Synonyms are domain-specific ("BHI" ↔ "健康指数" ↔ "建筑健康指数"
    is meaningful here; the same mapping would be nonsense in news
    text).
  - No external network dependency; the retriever stays pure-stdlib
    apart from jieba for tokenization.

Each group is a frozenset; expansion adds every member when any one
member appears in the query. The token list grows by at most one
copy per non-member token, so the index stays small.

The same dictionary is applied both at index time (chunk
pre-processing) and at query time, so any pair of synonyms
collapses to the same tf-idf footprint.
"""
from __future__ import annotations

from typing import Dict, FrozenSet, List


# Each group is one equivalence class. Membership is bidirectional.
_SYNONYM_GROUPS: List[FrozenSet[str]] = [
    # Core analytics concepts
    frozenset({"异常", "异常检测", "故障", "不正常"}),
    frozenset({"健康指数", "BHI", "建筑健康指数", "building health index"}),
    frozenset({"风险", "危险", "风险等级", "risk"}),
    frozenset({"改造", "retrofit", "更新", "翻新"}),
    frozenset({"优先级", "priority", "优先"}),
    frozenset({"规则引擎", "rule engine", "规则"}),

    # Physical measurements
    frozenset({"裂缝", "裂纹", "crack"}),
    frozenset({"倾斜", "形变", "tilt", "倾角"}),
    frozenset({"温度", "temperature"}),
    frozenset({"湿度", "humidity"}),
    frozenset({"用电", "电力", "electricity", "能耗", "energy"}),

    # Detection methods
    frozenset({"阈值", "threshold"}),
    frozenset({"变化率", "rate of change", "roc"}),
    frozenset({"z-score", "zscore", "z 值", "z分数"}),

    # Risk tiers
    frozenset({"normal", "正常", "normal tier"}),
    frozenset({"attention", "注意", "关注"}),
    frozenset({"abnormal", "异常档", "异常等级"}),
    frozenset({"highrisk", "high risk", "高风险", "高危"}),

    # Subject-system meta
    frozenset({"不做", "不做什么", "拒绝", "refuse", "not do"}),
    frozenset({"安全", "safety", "安全等级"}),
    frozenset({"评估", "assessment", "评价", "评测"}),
    frozenset({"监测", "monitoring", "监控"}),
    frozenset({"传感器", "sensor", "探头", "感应器"}),

    # AI / RAG
    frozenset({"解释", "explain", "explanation"}),
    frozenset({"检索", "retrieval", "召回"}),
    frozenset({"知识库", "knowledge base", "知识"}),
    frozenset({"证据", "evidence"}),
]


def _build_index() -> Dict[str, FrozenSet[str]]:
    """Map each member → the full equivalence group it belongs to."""
    idx: Dict[str, FrozenSet[str]] = {}
    for group in _SYNONYM_GROUPS:
        for member in group:
            idx[member.lower()] = group
    return idx


_INDEX: Dict[str, FrozenSet[str]] = _build_index()


def expand_token(token: str) -> List[str]:
    """Expand a single token to itself plus all synonyms in its group.

    Returns the original token plus its synonyms, deduplicated, with the
    original token always first (preserves ordering for readability
    and determinism).
    """
    key = token.lower()
    group = _INDEX.get(key)
    if group is None:
        return [token]
    # Always include the original casing first.
    return [token] + sorted(m for m in group if m.lower() != key)


def expand_tokens(tokens: List[str]) -> List[str]:
    """Expand a list of tokens by unioning each one's synonym group."""
    seen: Dict[str, None] = {}
    out: List[str] = []
    for tok in tokens:
        for expanded in expand_token(tok):
            if expanded not in seen:
                seen[expanded] = None
                out.append(expanded)
    return out


def synonym_groups() -> List[FrozenSet[str]]:
    """Public read-only view of the synonym groups (for tests / docs)."""
    return list(_SYNONYM_GROUPS)
