"""
Knowledge tokenizer · Phase 7
==============================
Tests for jieba-based CJK tokenization and engineering-synonym
expansion. Also covers the integration with the TF-IDF retriever
(queries that previously missed should now hit).
"""
import pytest

from app.knowledge import synonyms, tokenizer
from app.knowledge.retriever import KnowledgeRetriever
from pathlib import Path
from sqlalchemy import select

from app.db import models as m


# --------------------------------------------------------------------- tokenizer
def test_tokenize_empty_returns_empty():
    assert tokenizer.tokenize("") == []
    assert tokenizer.tokenize("   \t\n") == []


def test_tokenize_english_lowercased_and_filtered():
    out = tokenizer.tokenize("The Quick Brown Fox")
    # 'the' is a stop word; everything else is kept
    assert "quick" in out
    assert "brown" in out
    assert "fox" in out
    assert "the" not in out
    for tok in out:
        assert tok == tok.lower()


def test_tokenize_drops_single_ascii_letters():
    # 'a' is a stop word AND too short; 'bhi' is kept
    out = tokenizer.tokenize("BHI a")
    assert "bhi" in out
    assert "a" not in out


def test_tokenize_cjk_segments_with_jieba_when_available():
    """jieba cuts '异常检测' into ['异常', '检测'], not per-character.

    With synonym expansion, the surface form '异常' pulls in its group
    {异常, 异常检测, 故障, 不正常}; '检测' is a single token on its own
    with no synonym group, so total surface = 5. The point of the test
    is that the *meaningful* tokens ('异常' and '检测') are present and
    that jieba (not the per-character fallback) is doing the segmentation.
    """
    out = tokenizer.tokenize("异常检测")
    assert "异常" in out
    assert "检测" in out
    # Synonym expansion pulls 异常 → {异常检测, 故障, 不正常}
    assert "异常检测" in out
    assert "故障" in out
    # No lone single-character fragments from the old per-character
    # tokenizer should dominate (jieba should always beat that for
    # this phrase).
    single_chars = [t for t in out if len(t) == 1]
    # We expect 0 single-character tokens for this phrase; jieba cuts
    # it cleanly and synonym expansion doesn't add 1-char tokens.
    assert single_chars == [], f"unexpected single-char tokens: {single_chars}"


def test_tokenize_chinese_phrase_does_not_split_per_character():
    """Regression guard: the old per-character tokenizer would return
    ['异', '常', '检', '测']. jieba returns ['异常', '检测']. Either way,
    the per-character regression must not be the *dominant* output."""
    out = tokenizer.tokenize("异常检测")
    joined_with_separator = "+".join(out)
    # No per-character stand-alone '异' or '常' followed by per-character
    # '检' or '测' as the only output
    assert "异常" in out and "检测" in out


def test_tokenize_strips_stop_words_both_languages():
    out = tokenizer.tokenize("the BHI 是 5 维度")
    assert "the" not in out
    assert "是" not in out
    assert "bhi" in out
    # 维度 kept (not a stop word)
    assert any("维度" == t or "维度" in t for t in out)


def test_tokenize_mixed_chinese_english():
    out = tokenizer.tokenize("RP-v1.0 改造优先级")
    # English/digit token + Chinese tokens
    assert "rp" in out  # lowered
    assert "v1" in out or "0" in out
    # Synonyms for 改造 include retrofit; for 优先级 include priority
    # (added by synonym expansion)
    assert "priority" in out or "优先" in out


def test_tokenize_expand_false_returns_no_synonyms():
    out = tokenizer.tokenize("异常", expand=False)
    assert out == ["异常"]
    # With expansion, 异常 expands to its group
    expanded = tokenizer.tokenize("异常", expand=True)
    assert "异常检测" in expanded or "故障" in expanded


def test_tokenize_handles_punctuation_gracefully():
    out = tokenizer.tokenize("BHI: 0.40 (structural safety); risk=high")
    assert "bhi" in out
    assert "0" in out or "40" in out
    assert "structural" in out
    assert "safety" in out
    assert "high" in out


# --------------------------------------------------------------------- synonyms
def test_synonym_groups_cover_documented_terms():
    groups = synonyms.synonym_groups()
    # Sanity: the well-known engineering concepts are present (case-preserved).
    flat = {m for g in groups for m in g}
    assert "BHI" in flat
    assert "健康指数" in flat
    assert "异常" in flat
    assert "priority" in flat
    assert "crack" in flat
    assert "tilt" in flat


def test_expand_token_keeps_original_first():
    out = synonyms.expand_token("BHI")
    assert out[0] == "BHI"
    # All synonyms in the same group appear
    assert "健康指数" in out
    assert "building health index" in out


def test_expand_token_is_idempotent_for_unknowns():
    assert synonyms.expand_token("zzznosynonym") == ["zzznosynonym"]


def test_expand_tokens_deduplicates():
    # '异常' and '故障' map to the same group; passing both should
    # collapse to one union without duplicate entries.
    out = synonyms.expand_tokens(["异常", "故障"])
    assert len(out) == len(set(out))


# --------------------------------------------------------------------- integration
def test_retriever_loads_and_handles_chinese_query(tmp_path):
    """Write a tiny in-memory knowledge dir and ensure the retriever
    indexes it; a Chinese query that hits a synonym should retrieve it."""
    knowledge_dir = tmp_path / "k"
    knowledge_dir.mkdir()
    (knowledge_dir / "alpha.md").write_text(
        "# Alpha Doc\n\n"
        "## Detection\n"
        "本节描述异常检测的工程实现细节。\n\n"
        "## Threshold\n"
        "阈值为 0.30 mm。\n",
        encoding="utf-8",
    )
    (knowledge_dir / "beta.md").write_text(
        "# Beta Doc\n\n"
        "## Other\n"
        "完全不相关的内容，关于能耗管理。\n",
        encoding="utf-8",
    )

    retriever = KnowledgeRetriever(knowledge_dir, top_k=3)
    assert retriever.n_documents == 2
    assert retriever.n_chunks >= 3

    # 异常 → synonym group includes 故障 / 不正常; both docs lack those,
    # but the alpha doc's `异常` token will still match because jieba cuts
    # 异常检测 as a phrase containing 异常.
    hits = retriever.retrieve("异常")
    assert hits, "expected at least one hit for query='异常'"
    assert any("alpha.md" in h.document for h in hits)


def test_retriever_synonym_expansion_finds_synonym_doc(tmp_path):
    """A query phrased with the *synonym* of a token in the doc must
    still retrieve the doc. Here the doc talks about 'crack'; the
    query uses '裂缝' (a synonym in the same group)."""
    knowledge_dir = tmp_path / "k"
    knowledge_dir.mkdir()
    (knowledge_dir / "doc.md").write_text(
        "# Doc\n\n"
        "## Crack\n"
        "A crack wider than 0.30 mm is flagged high severity.\n",
        encoding="utf-8",
    )
    retriever = KnowledgeRetriever(knowledge_dir, top_k=3)
    hits = retriever.retrieve("裂缝")
    assert hits, "synonym expansion should bridge 裂缝 ↔ crack"
    assert any("doc.md" in h.document for h in hits)


# --------------------------------------------------------------------- eval regression
def test_tokenize_does_not_break_english_only_query():
    """Pure-English queries (already supported) must still work."""
    out = tokenizer.tokenize("threshold rate of change z-score")
    # Note: the tokenizer splits hyphenated English on '-', so
    # 'z-score' becomes ['z', 'score']. Single ASCII characters are
    # filtered as noise (length<2), so 'z' drops out; 'score' stays
    # and that is what the TF-IDF index actually matches.
    assert "threshold" in out
    assert "rate" in out
    assert "change" in out
    assert "score" in out
