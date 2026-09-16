# 19 · Engineering RAG  工程知识检索 (Planned for Phase 6B)

> **NOT IMPLEMENTED IN PHASE 6A**
> Phase 6A 仅交付 Real LLM Provider + 输出验证 + 安全红线.
> Engineering RAG (Retrieval-Augmented Generation) 计划在 Phase 6B 实现.

**文档版本**：v0.1 · Phase 6A (placeholder)
**最后更新**：2026-09-15
**状态**：Planned for Phase 6B

---

## Why this doc exists

本文件作为占位符, 避免 Phase 6B 启动时文档缺失.

Phase 6A 范围**严格**不包含 RAG. 已实现的能力:
- ✓ Real LLM Provider (OpenAI-compatible)
- ✓ Mock provider fallback
- ✓ Pydantic output validation
- ✓ Redline safety scanning
- ✓ Failure handling (timeout / 4xx / 5xx / malformed)

Phase 6B 将增加:
- `knowledge/` 目录 (工程知识 Markdown 文档)
- chunking + lexical retrieval (TF-IDF 或 cosine)
- Knowledge Evidence 区分于 Engineering Data Evidence
- Prompt grounding 改造
- Tests 覆盖 retrieval / top-k / relevance

---

## 未来章节 (Phase 6B)

1. 知识库内容 (anomaly_detection / health_assessment / risk_classification / retrofit_decision / engineering_redlines)
2. RAG 实现方式 (Markdown → chunks → retrieval → top-k → prompt)
3. KnowledgeEvidence schema (document, section, content, relevance_score)
4. Engineering Data Evidence ≠ Knowledge Evidence 强制区分
5. Prompt grounding 改造
6. Tests (RAG / grounding / relevance)

---

**文档版本**：v0.1 · Phase 6A (placeholder)
**最后更新**：2026-09-15
**状态**：Planned for Phase 6B
