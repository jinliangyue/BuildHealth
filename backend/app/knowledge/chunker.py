"""
Knowledge Chunker · Phase 6B
=============================

Splits a KnowledgeDocument into a list of KnowledgeChunk by `##`
heading boundaries. Each `##` section becomes one chunk. If the
document has no `##` section, the whole body is one chunk
("Full Document").

Deterministic + explainable. No semantic chunking.
"""
from typing import List

from app.knowledge.schemas import KnowledgeChunk, KnowledgeDocument


def chunk_document(doc: KnowledgeDocument) -> List[KnowledgeChunk]:
    """
    Split a KnowledgeDocument into chunks. Each chunk = one `##` section
    (or a single "Full Document" chunk if no `##` exists).
    """
    # Re-parse body to extract sections (we don't store raw sections in
    # KnowledgeDocument; the loader only stored full_text)
    from app.knowledge.loader import _parse_title_and_sections

    title, sections = _parse_title_and_sections(doc.full_text)

    chunks: List[KnowledgeChunk] = []
    if not sections:
        # Fallback: 整文档作为 single chunk
        content = doc.full_text.strip()
        chunks.append(
            KnowledgeChunk(
                chunk_id=f"{doc.document_id}::full",
                document_id=doc.document_id,
                document_title=doc.title,
                section="Full Document",
                content=content,
                word_count=len(content.split()),
            )
        )
        return chunks

    for idx, (section, content) in enumerate(sections):
        content = content.strip()
        if not content:
            continue
        chunks.append(
            KnowledgeChunk(
                chunk_id=f"{doc.document_id}::{idx}",
                document_id=doc.document_id,
                document_title=doc.title,
                section=section,
                content=content,
                word_count=len(content.split()),
            )
        )
    return chunks


def chunk_documents(docs: List[KnowledgeDocument]) -> List[KnowledgeChunk]:
    """Chunk all documents and return a flat list of chunks."""
    out: List[KnowledgeChunk] = []
    for d in docs:
        out.extend(chunk_document(d))
    return out
