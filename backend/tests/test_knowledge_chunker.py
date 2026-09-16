"""
Knowledge Chunker Tests · Phase 6B
"""
from pathlib import Path
import pytest

from app.knowledge.loader import load_knowledge_base
from app.knowledge.chunker import chunk_document, chunk_documents
from app.knowledge.schemas import KnowledgeChunk


@pytest.fixture
def sample_doc(tmp_path):
    d = tmp_path / "k.md"
    d.write_text(
        "# Title\n"
        "\n"
        "## Section A\n"
        "\n"
        "Content of A.\n"
        "\n"
        "## Section B\n"
        "\n"
        "Content of B with more words.\n",
        encoding="utf-8",
    )
    docs = load_knowledge_base(tmp_path)
    return docs[0]


def test_chunk_by_h2_sections(sample_doc):
    chunks = chunk_document(sample_doc)
    assert len(chunks) == 2
    assert chunks[0].section == "Section A"
    assert chunks[1].section == "Section B"
    assert chunks[0].content == "Content of A."
    assert "Content of B" in chunks[1].content


def test_chunk_id_format(sample_doc):
    chunks = chunk_document(sample_doc)
    assert chunks[0].chunk_id == "k.md::0"
    assert chunks[1].chunk_id == "k.md::1"
    # 唯一
    ids = [c.chunk_id for c in chunks]
    assert len(set(ids)) == len(ids)


def test_word_count_accurate(sample_doc):
    chunks = chunk_document(sample_doc)
    # "Content of A." = 3 words
    assert chunks[0].word_count == 3
    # "Content of B with more words." = 6 words
    assert chunks[1].word_count == 6


def test_doc_with_no_h2_falls_back_to_full(sample_doc):
    # 构造一个只有 # 没有 ## 的 doc
    from app.knowledge.schemas import KnowledgeDocument
    doc = KnowledgeDocument(
        document_id="x.md",
        title="X",
        full_text="# X\n\nJust one block of text here.\n",
    )
    chunks = chunk_document(doc)
    assert len(chunks) == 1
    assert chunks[0].section == "Full Document"
    assert "Just one block" in chunks[0].content


def test_chunk_documents_aggregates(sample_doc):
    # 用另一份 doc 测多文档聚合
    from app.knowledge.schemas import KnowledgeDocument
    doc2 = KnowledgeDocument(
        document_id="y.md",
        title="Y",
        full_text="# Y\n\n## S\n\nbody\n",
    )
    chunks = chunk_documents([sample_doc, doc2])
    # sample_doc: 2 chunks, doc2: 1 chunk
    assert len(chunks) == 3
    doc_ids = {c.document_id for c in chunks}
    assert doc_ids == {"k.md", "y.md"}
