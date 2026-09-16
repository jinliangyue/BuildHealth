"""
AI Provider Factory Tests · Phase 6A
======================================

Tests the env-based provider selection in provider_factory.
"""
import pytest

from app.ai.mock_provider import MockProvider
from app.ai.provider_factory import (
    _MisconfiguredProvider,
    get_ai_provider,
    reset_ai_provider,
)
from app.ai.real_provider import OpenAICompatibleProvider


@pytest.fixture(autouse=True)
def _reset_singleton():
    reset_ai_provider()
    yield
    reset_ai_provider()


def test_default_mock_when_no_env(monkeypatch):
    """无 AI_PROVIDER env → MockProvider."""
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    monkeypatch.delenv("AI_API_KEY", raising=False)
    monkeypatch.delenv("AI_BASE_URL", raising=False)
    p = get_ai_provider()
    assert isinstance(p, MockProvider)
    assert p.name == "mock"


def test_explicit_mock(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "mock")
    p = get_ai_provider()
    assert isinstance(p, MockProvider)


def test_openai_compatible_with_full_config(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "openai-compatible")
    monkeypatch.setenv("AI_API_KEY", "test-key")
    monkeypatch.setenv("AI_BASE_URL", "https://example.com/v1")
    monkeypatch.setenv("AI_MODEL", "gpt-test")
    p = get_ai_provider()
    assert isinstance(p, OpenAICompatibleProvider)
    assert p.model == "gpt-test"
    assert p._api_key == "test-key"


def test_openai_compatible_missing_api_key(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "openai-compatible")
    monkeypatch.delenv("AI_API_KEY", raising=False)
    monkeypatch.setenv("AI_BASE_URL", "https://example.com/v1")
    p = get_ai_provider()
    assert isinstance(p, _MisconfiguredProvider)
    h = p.health_check()
    assert h.status == "provider_not_configured"
    assert "AI_API_KEY" in h.message


def test_openai_compatible_missing_base_url(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "openai-compatible")
    monkeypatch.setenv("AI_API_KEY", "k")
    monkeypatch.delenv("AI_BASE_URL", raising=False)
    p = get_ai_provider()
    assert isinstance(p, _MisconfiguredProvider)
    h = p.health_check()
    assert h.status == "provider_not_configured"
    assert "AI_BASE_URL" in h.message


def test_unknown_provider_falls_back_to_mock(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "anthropic-future")
    p = get_ai_provider()
    assert isinstance(p, MockProvider)


def test_provider_singleton(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "mock")
    p1 = get_ai_provider()
    p2 = get_ai_provider()
    assert p1 is p2


def test_reset_ai_provider_clears_singleton(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "mock")
    p1 = get_ai_provider()
    reset_ai_provider()
    p2 = get_ai_provider()
    assert p1 is not p2


def test_misconfigured_summary_raises(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "openai-compatible")
    monkeypatch.delenv("AI_API_KEY", raising=False)
    monkeypatch.setenv("AI_BASE_URL", "https://x")
    p = get_ai_provider()
    from app.ai.schemas import AIProviderError
    with pytest.raises(AIProviderError) as exc:
        p.generate_summary(None)
    assert exc.value.code == "config_error"


def test_real_provider_carries_config_settings(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "openai-compatible")
    monkeypatch.setenv("AI_API_KEY", "k")
    monkeypatch.setenv("AI_BASE_URL", "https://x.com/v1")
    monkeypatch.setenv("AI_MODEL", "gpt-x")
    monkeypatch.setenv("AI_REQUEST_TIMEOUT", "45")
    monkeypatch.setenv("AI_MAX_TOKENS", "2000")
    monkeypatch.setenv("AI_TEMPERATURE", "0.5")
    p = get_ai_provider()
    assert p._timeout == 45.0
    assert p._max_tokens == 2000
    assert p._temperature == 0.5
