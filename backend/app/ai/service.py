"""
AI Service · Phase 5 V3 + Phase 6A + Phase 6B
==============================================

Phase 6B 改造:
- 接 knowledge_retriever (默认 None)
- summarize_building / ask_about_building 先 build context, 再 retrieve
  knowledge evidence, 再调 provider.generate_*
- 优雅降级: retriever=None 或 exception → knowledge_evidence=[]

不写库. 不修改任何已有 V1 / V2 service.
"""
from typing import List, Optional

from sqlalchemy.orm import Session

from app.ai.schemas import (
    AIHealthStatus,
    AIProviderError,
    AIResponse,
)
from app.ai.context_builder import build_engineering_context
from app.ai.provider_factory import get_ai_provider, reset_ai_provider
from app.ai.provider import AIProvider
from app.knowledge.query_builder import build_retrieval_query


__all__ = [
    "AIService",
    "get_ai_service",
    "get_ai_provider",
    "reset_ai_provider",
]


class AIService:
    def __init__(self, provider: AIProvider, knowledge_retriever=None):
        """
        knowledge_retriever: optional KnowledgeRetriever instance.
            If None, RAG is disabled and knowledge_evidence=[] in responses.
        """
        self.provider = provider
        self.knowledge_retriever = knowledge_retriever

    def get_health(self) -> AIHealthStatus:
        return self.provider.health_check()

    def _retrieve_knowledge_safe(self, query: str) -> List[dict]:
        """Run retriever; return [] on any error (graceful degradation)."""
        if self.knowledge_retriever is None:
            return []
        try:
            evidences = self.knowledge_retriever.retrieve(query)
        except Exception:
            return []
        # Convert to dict (Pydantic model → dict) for transport
        return [e.model_dump() if hasattr(e, "model_dump") else e for e in evidences]

    def summarize_building(
        self, session: Session, building_id: int
    ) -> Optional[AIResponse]:
        ctx = build_engineering_context(session, building_id)
        if ctx is None:
            return None
        query = build_retrieval_query(
            "Summarize this building's current engineering status.", ctx
        )
        knowledge_ev = self._retrieve_knowledge_safe(query)
        try:
            return self.provider.generate_summary(
                ctx, knowledge_evidence=knowledge_ev
            )
        except AIProviderError:
            raise
        except Exception as e:
            raise AIProviderError(
                "internal_error", f"unexpected error: {str(e)[:200]}"
            ) from e

    def ask_about_building(
        self, session: Session, building_id: int, question: str
    ) -> Optional[AIResponse]:
        ctx = build_engineering_context(session, building_id)
        if ctx is None:
            return None
        query = build_retrieval_query(question, ctx)
        knowledge_ev = self._retrieve_knowledge_safe(query)
        try:
            return self.provider.generate_answer(
                ctx, question.strip(), knowledge_evidence=knowledge_ev
            )
        except AIProviderError:
            raise
        except Exception as e:
            raise AIProviderError(
                "internal_error", f"unexpected error: {str(e)[:200]}"
            ) from e


def get_ai_service() -> AIService:
    """
    Singleton AI service. Phase 6B: 自动注入 default knowledge retriever.
    若 knowledge/ 目录不存在或无 .md 文件, retriever = None (RAG disabled).
    """
    provider = get_ai_provider()
    retriever = None
    try:
        from app.knowledge.retriever import get_default_retriever
        retriever = get_default_retriever()
    except Exception:
        retriever = None
    return AIService(provider, knowledge_retriever=retriever)
