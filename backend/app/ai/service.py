"""
AI Service · Phase 5 V3 + Phase 6A
====================================

Phase 6A 改造:
- 改用 provider_factory.get_ai_provider()
- try/except AIProviderError, 包装为统一错误路径
- 保留 singleton 行为 (reset_ai_provider 从 factory 暴露)

不写库. 不修改任何已有 V1 / V2 service.
"""
from typing import Optional

from sqlalchemy.orm import Session

from app.ai.schemas import (
    AIHealthStatus,
    AIProviderError,
    AIResponse,
)
from app.ai.context_builder import build_engineering_context
from app.ai.provider_factory import get_ai_provider, reset_ai_provider  # re-export
from app.ai.provider import AIProvider


# Re-export for backward compatibility
__all__ = [
    "AIService",
    "get_ai_service",
    "get_ai_provider",
    "reset_ai_provider",
]


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
        try:
            return self.provider.generate_summary(ctx)
        except AIProviderError:
            # 重新抛, 由 API 层统一转 HTTP
            raise
        except Exception as e:
            # 防御性: 任何非 AIProviderError 异常包装为 internal_error
            raise AIProviderError(
                "internal_error", f"unexpected error: {str(e)[:200]}"
            ) from e

    def ask_about_building(
        self, session: Session, building_id: int, question: str
    ) -> Optional[AIResponse]:
        ctx = build_engineering_context(session, building_id)
        if ctx is None:
            return None
        try:
            return self.provider.generate_answer(ctx, question.strip())
        except AIProviderError:
            raise
        except Exception as e:
            raise AIProviderError(
                "internal_error", f"unexpected error: {str(e)[:200]}"
            ) from e


def get_ai_service() -> AIService:
    return AIService(get_ai_provider())
