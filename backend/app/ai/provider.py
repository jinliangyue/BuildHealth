"""
AI Provider 抽象 · Phase 5 V3

Protocol-only 抽象. 当前唯一实现是 MockProvider.
未来 Phase 6+ 可加 OpenAIProvider / AnthropicProvider 继承此 protocol.
"""
from typing import Protocol

from app.ai.schemas import (
    AIHealthStatus,
    AIResponse,
    EngineeringContext,
)


class AIProvider(Protocol):
    """Provider 必须实现 3 个方法."""

    name: str
    model: str

    def health_check(self) -> AIHealthStatus:
        ...

    def generate_summary(self, context: EngineeringContext) -> AIResponse:
        ...

    def generate_answer(
        self, context: EngineeringContext, question: str
    ) -> AIResponse:
        ...
