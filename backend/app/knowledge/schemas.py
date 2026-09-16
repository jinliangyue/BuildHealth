"""
Knowledge Schemas · Phase 6B
"""
from typing import List, Optional

from pydantic import BaseModel, Field


KNOWLEDGE_SOURCE_LABEL = "BuildHealth Internal Engineering Notes"


class KnowledgeDocument(BaseModel):
    document_id: str  # e.g. "anomaly_detection.md"
    title: str
    source: str = Field(default=KNOWLEDGE_SOURCE_LABEL)
    sections: List["KnowledgeChunk"] = Field(default_factory=list)
    full_text: str = ""  # 用于 fallback single-chunk 文档


class KnowledgeChunk(BaseModel):
    chunk_id: str  # "{document_id}::{section_index}" or "::{full}"
    document_id: str
    document_title: str
    section: str  # 章节标题 or "Full Document"
    content: str
    word_count: int = 0


class KnowledgeEvidence(BaseModel):
    """RAG retrieval output. 注入 AIResponse."""
    document: str
    section: str
    content: str
    relevance_score: float = Field(ge=0.0, le=1.0)
    source: str = Field(default=KNOWLEDGE_SOURCE_LABEL)
    chunk_id: str


# Resolve forward reference
KnowledgeDocument.model_rebuild()
