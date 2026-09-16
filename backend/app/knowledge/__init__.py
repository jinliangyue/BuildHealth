"""
Engineering Knowledge RAG · Phase 6B
====================================

Project-internal engineering knowledge retrieval for the AI Engineering
Assistant. No vector DB, no embedding service, no internet. Pure
stdlib lexical retrieval (TF-IDF + cosine).

Architecture:
    Markdown files in backend/knowledge/
        → loader.py  → List[KnowledgeDocument]
        → chunker.py → List[KnowledgeChunk]
        → retriever.py (TF-IDF index, top-K cosine)
        → service layer → inject into AI prompt
"""
