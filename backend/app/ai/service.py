"""
AI Service · Phase 5 V3
========================

编排: Provider + Context Builder.
Singleton provider 实例 (mock default).

不写库. 不修改任何已有 V1 / V2 service.
"""
from typing import Optional

from sqlalchemy.orm import Session

from app.ai.schemas import (
    AIHealthStatus,
    AIResponse,
    EngineeringContext,
)
from app.ai.context_builder import build_engineering_context
from app.ai.mock_provider import MockProvider
from app.ai.provider import AIProvider
from app.core.config import AI_PROVIDER


# Singleton provider
_provider_instance: Optional[AIProvider] = None


def get_ai_provider() -> AIProvider:
    """Return singleton AI provider. 真实 LLM 未实现 → 始终 Mock."""
    global _provider_instance
    if _provider_instance is None:
        if AI_PROVIDER == "mock":
            _provider_instance = MockProvider()
        else:
            # 真实 provider 未实现 → 显式降级到 mock
            # 未来 Phase 6+ 在此处加 OpenAIProvider / AnthropicProvider
            _provider_instance = MockProvider()
    return _provider_instance


def reset_ai_provider() -> None:
    """测试辅助: 重置 singleton. 正常代码不要调用."""
    global _provider_instance
    _provider_instance = None


class AIService:
    def __init__(self, provider: AIProvider):
        self.provider = provider

    def get_health(self) -> AIHealthStatus:
        return self.provider.health_check()

    def summarize_building(
        self, session: Session, building_id: int
    ) -> Optional[AIResponse]:
        ctx = build_engineering_context(session, building_id)
        if ctx is None:
            return None
        return self.provider.generate_summary(ctx)

    def ask_about_building(
        self, session: Session, building_id: int, question: str
    ) -> Optional[AIResponse]:
        ctx = build_engineering_context(session, building_id)
        if ctx is None:
            return None
        return self.provider.generate_answer(ctx, question.strip())


def get_ai_service() -> AIService:
    return AIService(get_ai_provider())
