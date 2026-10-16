"""
Knowledge Retriever · Phase 6B + 7
====================================

Pure-stdlib lexical retrieval: TF-IDF + cosine similarity.
No sklearn, no vector DB, no embedding model. Deterministic.

Algorithm:
    1. tokenize(query) → List[str] of tokens
    2. For each chunk: tokenize → tf(t) for each term
    3. df(t) = number of chunks containing t
    4. idf(t) = log((N + 1) / (df(t) + 1)) + 1  (smoothed)
    5. tfidf(t, d) = tf(t, d) * idf(t)
    6. score(q, d) = cosine(tfidf(q), tfidf(d))
    7. Return top-K with score > 0

Tokens (Phase 7): English / digit runs split as `[a-z0-9]+`; CJK
runs are segmented by jieba (when available) and then expanded with
the engineering synonym dictionary (`app.knowledge.synonyms`).
"""
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.knowledge import tokenizer
from app.knowledge.chunker import chunk_documents
from app.knowledge.loader import load_knowledge_base
from app.knowledge.schemas import (
    KNOWLEDGE_SOURCE_LABEL,
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeEvidence,
)


def _tokenize(text: str) -> List[str]:
    """Compatibility wrapper for the index/scoring code below.

    All tokenization policy lives in `app.knowledge.tokenizer`; this
    function exists only to keep the rest of the file readable.
    """
    return tokenizer.tokenize(text, expand=True)


class _TfidfIndex:
    """Internal TF-IDF index for a fixed list of chunks."""

    def __init__(self, chunks: List[KnowledgeChunk]):
        self._chunks = chunks
        self._n = len(chunks)
        # term → doc count
        self._df: Dict[str, int] = defaultdict(int)
        # chunk_idx → Counter[term → count]
        self._tf: List[Counter] = []
        # chunk_idx → L2 norm of tfidf vector (precomputed)
        self._norm: List[float] = []
        self._build()

    def _build(self):
        for chunk in self._chunks:
            tokens = _tokenize(chunk.content)
            counter = Counter(tokens)
            self._tf.append(counter)
            for t in counter:
                self._df[t] += 1
        # compute norm of each chunk's tfidf vector
        for counter in self._tf:
            sq = 0.0
            for t, c in counter.items():
                w = self._weight(t, c)
                sq += w * w
            self._norm.append(math.sqrt(sq) if sq > 0 else 0.0)

    def _idf(self, term: str) -> float:
        # smoothed idf: log((N + 1) / (df + 1)) + 1
        return math.log((self._n + 1) / (self._df.get(term, 0) + 1)) + 1.0

    def _weight(self, term: str, count: int) -> float:
        # raw tf * smoothed idf
        return float(count) * self._idf(term)

    def score_query(self, query: str) -> List[float]:
        """Return a per-chunk score for the query."""
        q_tokens = _tokenize(query)
        if not q_tokens or self._n == 0:
            return [0.0] * self._n
        # build query vector
        q_counter = Counter(q_tokens)
        q_vec = {t: self._weight(t, c) for t, c in q_counter.items()}
        q_sq = sum(w * w for w in q_vec.values())
        q_norm = math.sqrt(q_sq) if q_sq > 0 else 0.0
        if q_norm == 0:
            return [0.0] * self._n

        scores: List[float] = []
        for idx, d_counter in enumerate(self._tf):
            d_norm = self._norm[idx]
            if d_norm == 0:
                scores.append(0.0)
                continue
            # dot product
            dot = 0.0
            for t, q_w in q_vec.items():
                c = d_counter.get(t, 0)
                if c > 0:
                    dot += q_w * self._weight(t, c)
            scores.append(dot / (q_norm * d_norm))
        return scores


class KnowledgeRetriever:
    """
    知识库检索. 构造时加载 knowledge/ 目录, 之后 retrieve(query) 返回 top-K
    List[KnowledgeEvidence] (按 relevance_score 降序, 过滤 0 分).
    """

    def __init__(self, knowledge_dir: Path, top_k: int = 3):
        self._dir = knowledge_dir
        self._top_k = top_k
        self._docs: List[KnowledgeDocument] = []
        self._chunks: List[KnowledgeChunk] = []
        self._index: Optional[_TfidfIndex] = None
        self._load()

    def _load(self):
        self._docs = load_knowledge_base(self._dir)
        self._chunks = chunk_documents(self._docs)
        if self._chunks:
            self._index = _TfidfIndex(self._chunks)
        else:
            self._index = None

    @property
    def n_chunks(self) -> int:
        return len(self._chunks)

    @property
    def n_documents(self) -> int:
        return len(self._docs)

    def retrieve(self, query: str) -> List[KnowledgeEvidence]:
        """Top-K relevant chunks as KnowledgeEvidence list."""
        if self._index is None or not query.strip():
            return []
        scores = self._index.score_query(query)
        # 排序 (索引, score) 按 score 降序
        ranked: List[Tuple[int, float]] = sorted(
            enumerate(scores), key=lambda x: x[1], reverse=True
        )
        results: List[KnowledgeEvidence] = []
        for idx, score in ranked[: self._top_k]:
            if score <= 0.0:
                break  # 没有相关内容
            chunk = self._chunks[idx]
            # relevance_score 截断到 4 位, 0-1
            rel = round(min(max(score, 0.0), 1.0), 4)
            results.append(
                KnowledgeEvidence(
                    document=chunk.document_id,
                    section=chunk.section,
                    content=chunk.content[:300],  # 截断
                    relevance_score=rel,
                    source=KNOWLEDGE_SOURCE_LABEL,
                    chunk_id=chunk.chunk_id,
                )
            )
        return results


# Module-level singleton cache. See `get_default_retriever` docstring.
# We intentionally avoid `@lru_cache` on a no-arg function: the
# `get_default_retriever_returns_none_when_no_knowledge_dir` test
# monkeypatches `cwd` and expects the function to keep responding to
# the directory's existence on every call (the existing path is computed
# from `__file__`, not cwd, so this is mostly a smoke test, but the
# contract is: missing dir → None, never cached as None).
_cached_retriever: Optional[KnowledgeRetriever] = None
_cached_dir_path: Optional[Path] = None


def get_default_retriever() -> Optional[KnowledgeRetriever]:
    """
    Load the default knowledge/ retriever as a process-wide singleton.

    Behaviour:
        - First call: read `backend/knowledge/*.md`, build the TF-IDF
          index (jieba tokenization happens here).
        - Subsequent calls: return the cached `KnowledgeRetriever`
          instance, **no disk reads, no re-tokenization**.

    Graceful degradation:
        - If the `knowledge/` directory does not exist, or contains no
          `.md` files, return `None` (RAG disabled, AI endpoints stay up).
          The `None` result is **not** cached, so the next call re-checks
          the directory.

    Concurrency:
        - FastAPI runs sync endpoints in a thread pool, so two threads
          may race on first call. Both may construct an instance; one
          is discarded. The retriever itself is read-only after
          construction, so no shared-state corruption is possible.

    Cache invalidation:
        - Knowledge files are bundled with the package and treated as
          static. **Editing `knowledge/*.md` requires a process restart
          to take effect.** This is an explicit trade-off: it buys us
          O(construct-once) per process at the cost of a reload ritual.
        - For tests that need a fresh instance, call
          `reset_default_retriever_cache()`.
    """
    # retriever.py is at backend/app/knowledge/retriever.py
    # knowledge/ is at backend/knowledge/
    # → 3 个 parent 即可
    global _cached_retriever, _cached_dir_path
    default_dir = Path(__file__).resolve().parent.parent.parent / "knowledge"
    if not default_dir.exists() or not any(default_dir.glob("*.md")):
        # 不缓存 None: 目录就绪后下次调用仍能正常加载
        return None
    if _cached_retriever is None or _cached_dir_path != default_dir:
        _cached_retriever = KnowledgeRetriever(default_dir, top_k=3)
        _cached_dir_path = default_dir
    return _cached_retriever


def reset_default_retriever_cache() -> None:
    """
    Reset the module-level singleton cache. Intended for tests that
    monkeypatch the knowledge directory at runtime; production callers
    should not need this because `knowledge/` is static and bundled
    with the package.
    """
    global _cached_retriever, _cached_dir_path
    _cached_retriever = None
    _cached_dir_path = None
