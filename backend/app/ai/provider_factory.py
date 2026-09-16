"""
AI Provider Factory · Phase 6A
================================

Singleton. 根据 `AI_PROVIDER` 环境变量选择 provider.

支持:
- "mock" (default)            → MockProvider
- "openai-compatible"         → OpenAICompatibleProvider (需 AI_API_KEY + AI_BASE_URL)
- "openai-compatible" 但缺配置 → _MisconfiguredProvider (health_check 显式错误)
- 其它 / 未知 provider         → 降级 MockProvider

注意: 工厂函数**在每次调用时**读取 env vars (via os.getenv), 而非 import-time,
这样 monkeypatch.setenv / 运行时切换 AI_PROVIDER 都能生效.
"""
import os
from typing import Optional

from app.ai.mock_provider import MockProvider
from app.ai.provider import AIProvider
from app.ai.schemas import AIHealthStatus, AIProviderError


_provider_instance: Optional[AIProvider] = None


class _MisconfiguredProvider:
    """
    当 AI_PROVIDER=openai-compatible 但缺 key/url 时, 包装一个 stub.

    - health_check → status="provider_not_configured", 含原因
    - generate_summary / generate_answer → raise AIProviderError("config_error")
    """

    name = "openai-compatible"
    model = "(misconfigured)"

    def __init__(self, reason: str):
        self._reason = reason

    def health_check(self) -> AIHealthStatus:
        return AIHealthStatus(
            status="provider_not_configured",
            provider=self.name,
            model=self.model,
            message=self._reason,
        )

    def generate_summary(self, context, knowledge_evidence=None):  # noqa: ARG002
        raise AIProviderError("config_error", self._reason)

    def generate_answer(self, context, question, knowledge_evidence=None):  # noqa: ARG002
        raise AIProviderError("config_error", self._reason)


def _read_config():
    """Read env vars at call time. Falls back to safe defaults."""
    return {
        "provider": os.getenv("AI_PROVIDER", "mock").strip().lower(),
        "model": os.getenv("AI_MODEL", "mock-deterministic-v1").strip(),
        "base_url": os.getenv("AI_BASE_URL", "").strip(),
        "api_key": os.getenv("AI_API_KEY", "").strip(),
        "timeout": float(os.getenv("AI_REQUEST_TIMEOUT", "30")),
        "max_tokens": int(os.getenv("AI_MAX_TOKENS", "1500")),
        "temperature": float(os.getenv("AI_TEMPERATURE", "0.2")),
    }


def get_ai_provider() -> AIProvider:
    """Singleton. 第一次调用根据 env 决定, 之后缓存."""
    global _provider_instance
    if _provider_instance is not None:
        return _provider_instance

    cfg = _read_config()
    name = cfg["provider"]
    if name == "mock":
        _provider_instance = MockProvider()
    elif name == "openai-compatible":
        if not cfg["api_key"]:
            _provider_instance = _MisconfiguredProvider(
                "AI_API_KEY is not set. Either set it in the environment "
                "or switch to AI_PROVIDER=mock."
            )
        elif not cfg["base_url"]:
            _provider_instance = _MisconfiguredProvider(
                "AI_BASE_URL is not set. Either set it in the environment "
                "or switch to AI_PROVIDER=mock."
            )
        else:
            from app.ai.real_provider import OpenAICompatibleProvider

            _provider_instance = OpenAICompatibleProvider(
                api_key=cfg["api_key"],
                base_url=cfg["base_url"],
                model=cfg["model"],
                timeout=cfg["timeout"],
                max_tokens=cfg["max_tokens"],
                temperature=cfg["temperature"],
            )
    else:
        _provider_instance = MockProvider()

    return _provider_instance


def reset_ai_provider() -> None:
    """测试辅助: 重置 singleton. 正常代码不要调用."""
    global _provider_instance
    _provider_instance = None
