"""
Knowledge tokenizer · BuildHealth Phase 7
=========================================

Replaces the per-character CJK tokenization that lived in retriever.py
with a jieba-backed tokenizer plus optional synonym expansion.

Behaviour
---------
1. Lowercase the input (so mixed-case English matches regardless).
2. Split English / digit runs as `[a-z0-9]+` (unchanged from before).
3. Split CJK runs with jieba.lcut, falling back to per-character when
   jieba is not importable (defensive — it is pinned in requirements.txt,
   but tests or air-gapped environments may not have it).
4. Drop stop words.
5. Apply synonym expansion: for each surviving token, add every
   member of its synonym group (from `app.knowledge.synonyms`).

Determinism
-----------
jieba's initialisation runs deterministic dict loading. There is no
user-dict injection in this codebase, so two cold imports of jieba
on the same machine produce identical segmentations. This matches the
project-wide guarantee that retrieval is reproducible.
"""
from __future__ import annotations

import re
from typing import List, Optional

from app.knowledge import synonyms

# Same stop-word list the previous per-character tokenizer used.
_STOP_WORDS = frozenset({
    # English
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "and", "or", "but", "if", "then", "else", "of", "in", "on", "at", "to",
    "for", "with", "by", "as", "from", "this", "that", "these", "those",
    "it", "its", "i", "you", "he", "she", "we", "they", "them", "their",
    "do", "no", "not", "so", "up", "use",
    "which", "who", "whom", "whose", "what", "where", "when", "why", "how",
    # Chinese 常见停用词 (单字)
    "的", "了", "是", "在", "和", "与", "或", "但", "如", "则", "于",
    "为", "以", "由", "本", "此", "这", "那", "它", "我", "你", "他", "她",
    "们", "中", "上", "下", "也", "都", "而", "及", "之", "没",
    "个", "些", "这", "那", "么", "吗", "呢", "啊", "吧", "嘛",
})

_TOKEN_RE = re.compile(r"[a-z0-9]+|[一-鿿]+")

# Lazy-initialised so importing this module does not block on jieba
# dict loading. Once set, _seg_cjk becomes a stable callable.
_seg_cjk = None  # type: Optional[callable]  # noqa: F821


def _get_seg_cjk():
    """Return a function that splits CJK text into word tokens.

    Uses jieba when available; falls back to per-character splitting
    so unit tests and environments without jieba still work.
    """
    global _seg_cjk
    if _seg_cjk is None:
        try:
            import jieba  # type: ignore
            # jieba emits one item per word; whitespace-padded output
            # from lcut is deterministic for the same input.
            def _seg(text: str) -> List[str]:
                # Filter empty strings jieba occasionally emits around
                # punctuation for safety.
                return [w for w in jieba.lcut(text) if w]
            _seg_cjk = _seg
        except ImportError:
            # Fallback: per-character split, matching the old behaviour.
            _seg_cjk = lambda text: list(text)
    return _seg_cjk


def _is_cjk(token: str) -> bool:
    return bool(token) and all("一" <= c <= "鿿" for c in token)


def tokenize(
    text: str,
    *,
    expand: bool = True,
) -> List[str]:
    """Split `text` into tokens, drop stop words, optionally expand synonyms.

    - English / digit runs are kept as single tokens.
    - CJK runs are split by jieba (or per character if jieba is absent).
    - Single ASCII letters and single-character tokens are dropped
      because they're noise (matches the prior tokenizer's filter).
    - When `expand=True`, each surviving token is unioned with the
      synonyms in its group (e.g. "异常" → ["异常", "异常检测",
      "故障", "不正常"]).
    """
    if not text:
        return []

    seg = _get_seg_cjk()
    lower = text.lower()
    raw: List[str] = []
    for match in _TOKEN_RE.finditer(lower):
        chunk = match.group(0)
        if _is_cjk(chunk):
            raw.extend(seg(chunk))
        else:
            raw.append(chunk)

    # Length + stopword filter. A single CJK character survives
    # because it is a meaningful Chinese token.
    filtered = [
        t for t in raw
        if t and t not in _STOP_WORDS and (len(t) >= 2 or _is_cjk(t))
    ]
    if not expand:
        return filtered
    return synonyms.expand_tokens(filtered)
