"""
Real LLM Provider Tests · Phase 6A
====================================

Tests `OpenAICompatibleProvider` by mocking httpx responses.
Never actually calls a real LLM.

覆盖:
- 构造校验 (缺 api_key / base_url)
- health_check (200 / 401 / 403 / timeout / network error)
- _call_chat (各种 status code + JSON parse error)
- _parse_response (成功 / 缺字段 / 含禁词 / disclaimer 强制)
- generate_summary / generate_answer 端到端
"""
import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.ai.real_provider import OpenAICompatibleProvider
from app.ai.schemas import AIProviderError, EngineeringContext
from app.core.config import AI_DISCLAIMER, AI_VERSION


# ============ Fixtures ============
@pytest.fixture
def sample_context(test_session):
    """简单 context (不依赖完整 DB, 用 mock 数据)."""
    from app.db import models as m
    from app.ai.schemas import (
        ContextBuildingInfo,
        ContextHealthInfo,
        ContextMonitoringSummary,
        ContextRetrofitInfo,
        ContextRiskInfo,
    )
    from app.ai.context_builder import build_engineering_context
    b = m.Building(
        name="LLM Test Building",
        address="x",
        year_built=2010,
        building_type="office",
        structure_type="frame",
        floors=10,
        area=5000.0,
        design_life=50,
        current_age=15,
    )
    test_session.add(b)
    test_session.flush()
    ctx = build_engineering_context(test_session, b.id)
    assert ctx is not None
    return ctx


def make_provider(**overrides):
    defaults = dict(
        api_key="test-key-not-real",
        base_url="https://example.com/v1",
        model="test-model",
        timeout=10.0,
        max_tokens=500,
        temperature=0.0,
    )
    defaults.update(overrides)
    return OpenAICompatibleProvider(**defaults)


def mock_response(status_code=200, json_payload=None, text=""):
    r = MagicMock()
    r.status_code = status_code
    r.text = text or (json.dumps(json_payload) if json_payload else "")
    r.json = MagicMock(
        side_effect=lambda: json.loads(r.text) if r.text else None
    )
    if json_payload is not None:
        r.json = MagicMock(return_value=json_payload)
    return r


# ============ Constructor ============
def test_constructor_requires_api_key():
    with pytest.raises(ValueError, match="api_key"):
        OpenAICompatibleProvider(
            api_key="", base_url="https://x", model="m"
        )


def test_constructor_requires_base_url():
    with pytest.raises(ValueError, match="base_url"):
        OpenAICompatibleProvider(api_key="k", base_url="", model="m")


def test_constructor_strips_trailing_slash():
    p = OpenAICompatibleProvider(
        api_key="k", base_url="https://x.com/v1/", model="m"
    )
    assert p._base_url == "https://x.com/v1"


# ============ health_check ============
@patch("app.ai.real_provider.httpx.get")
def test_health_check_ok(mock_get):
    mock_get.return_value = mock_response(200, json_payload={"data": []})
    h = make_provider().health_check()
    assert h.status == "ok"
    assert h.provider == "openai-compatible"
    assert h.model == "test-model"


@patch("app.ai.real_provider.httpx.get")
def test_health_check_401(mock_get):
    mock_get.return_value = mock_response(401, text="Unauthorized")
    h = make_provider().health_check()
    assert h.status == "provider_error"
    assert "401" in h.message


@patch("app.ai.real_provider.httpx.get")
def test_health_check_403(mock_get):
    mock_get.return_value = mock_response(403, text="Forbidden")
    h = make_provider().health_check()
    assert h.status == "provider_error"
    assert "403" in h.message


@patch("app.ai.real_provider.httpx.get")
def test_health_check_timeout(mock_get):
    mock_get.side_effect = httpx.TimeoutException("timeout")
    h = make_provider().health_check()
    assert h.status == "provider_error"
    assert "timeout" in h.message.lower()


@patch("app.ai.real_provider.httpx.get")
def test_health_check_network_error(mock_get):
    mock_get.side_effect = httpx.ConnectError("connection refused")
    h = make_provider().health_check()
    assert h.status == "provider_error"


# ============ _call_chat ============
@patch("app.ai.real_provider.httpx.post")
def test_call_chat_200_success(mock_post):
    mock_post.return_value = mock_response(
        200,
        json_payload={"choices": [{"message": {"content": "Hello"}}]},
    )
    content = make_provider()._call_chat([{"role": "user", "content": "hi"}])
    assert content == "Hello"


@patch("app.ai.real_provider.httpx.post")
def test_call_chat_401_auth_error(mock_post):
    mock_post.return_value = mock_response(401, text="invalid key")
    with pytest.raises(AIProviderError) as exc:
        make_provider()._call_chat([{"role": "user", "content": "x"}])
    assert exc.value.code == "auth_error"


@patch("app.ai.real_provider.httpx.post")
def test_call_chat_429_rate_limit(mock_post):
    mock_post.return_value = mock_response(429, text="rate limited")
    with pytest.raises(AIProviderError) as exc:
        make_provider()._call_chat([{"role": "user", "content": "x"}])
    assert exc.value.code == "rate_limit"


@patch("app.ai.real_provider.httpx.post")
def test_call_chat_500_provider_error(mock_post):
    mock_post.return_value = mock_response(500, text="server error")
    with pytest.raises(AIProviderError) as exc:
        make_provider()._call_chat([{"role": "user", "content": "x"}])
    assert exc.value.code == "provider_error"


@patch("app.ai.real_provider.httpx.post")
def test_call_chat_400_client_error(mock_post):
    mock_post.return_value = mock_response(400, text="bad request")
    with pytest.raises(AIProviderError) as exc:
        make_provider()._call_chat([{"role": "user", "content": "x"}])
    assert exc.value.code == "client_error"


@patch("app.ai.real_provider.httpx.post")
def test_call_chat_timeout(mock_post):
    mock_post.side_effect = httpx.TimeoutException("timeout")
    with pytest.raises(AIProviderError) as exc:
        make_provider()._call_chat([{"role": "user", "content": "x"}])
    assert exc.value.code == "timeout"


@patch("app.ai.real_provider.httpx.post")
def test_call_chat_network_error(mock_post):
    mock_post.side_effect = httpx.ConnectError("dns fail")
    with pytest.raises(AIProviderError) as exc:
        make_provider()._call_chat([{"role": "user", "content": "x"}])
    assert exc.value.code == "network_error"


@patch("app.ai.real_provider.httpx.post")
def test_call_chat_non_json_response(mock_post):
    r = mock_response(200)
    r.text = "<html>not json</html>"
    r.json = MagicMock(side_effect=json.JSONDecodeError("e", "d", 0))
    mock_post.return_value = r
    with pytest.raises(AIProviderError) as exc:
        make_provider()._call_chat([{"role": "user", "content": "x"}])
    assert exc.value.code == "malformed_response"


@patch("app.ai.real_provider.httpx.post")
def test_call_chat_missing_choices(mock_post):
    mock_post.return_value = mock_response(200, json_payload={"other": "x"})
    with pytest.raises(AIProviderError) as exc:
        make_provider()._call_chat([{"role": "user", "content": "x"}])
    assert exc.value.code == "malformed_response"


# ============ _parse_response ============
def test_parse_response_valid_json(sample_context):
    payload = {
        "answer": "Building is at prototype high risk.",
        "key_findings": [
            {"title": "BHI=54.27", "description": "Weakened.", "severity": "high"}
        ],
        "evidence": [
            {"source_type": "health", "source_id": None, "metric": None,
             "description": "BHI=54.27", "reference_path": "/api/buildings/1/health"}
        ],
        "recommended_actions": [
            {"action": "Review", "reason": "Prototype risk.", "urgency": "high"}
        ],
        "disclaimer": "ignored (forced)",
    }
    raw = json.dumps(payload)
    r = make_provider()._parse_response(raw, sample_context)
    assert r.provider == "openai-compatible"
    assert r.model == "test-model"
    assert r.calculation_version == AI_VERSION
    # disclaimer 强制 (不取 LLM 的)
    assert r.disclaimer == AI_DISCLAIMER
    assert "ignored" not in r.disclaimer
    assert r.answer == "Building is at prototype high risk."
    assert len(r.key_findings) == 1
    assert len(r.evidence) == 1
    assert len(r.recommended_actions) == 1


def test_parse_response_invalid_json(sample_context):
    with pytest.raises(AIProviderError) as exc:
        make_provider()._parse_response("not json {", sample_context)
    assert exc.value.code == "malformed_response"


def test_parse_response_not_dict(sample_context):
    with pytest.raises(AIProviderError) as exc:
        make_provider()._parse_response("[1, 2, 3]", sample_context)
    assert exc.value.code == "malformed_response"


def test_parse_response_strips_markdown_fences(sample_context):
    payload = {"answer": "x", "key_findings": [], "evidence": [], "recommended_actions": []}
    raw = "```json\n" + json.dumps(payload) + "\n```"
    r = make_provider()._parse_response(raw, sample_context)
    assert r.answer == "x"


def test_parse_response_missing_lists_uses_empty(sample_context):
    """缺 key_findings / recommended_actions / evidence → empty list, 不崩."""
    raw = json.dumps({"answer": "x"})
    r = make_provider()._parse_response(raw, sample_context)
    assert r.key_findings == []
    assert r.recommended_actions == []
    # evidence 缺失时回退到 context.evidence_chain[:5]
    assert len(r.evidence) >= 1


def test_parse_response_evidence_fallback_to_context(sample_context):
    """LLM 返回空 evidence → 用 context.evidence_chain (grounding 保证)."""
    raw = json.dumps({"answer": "x", "evidence": []})
    r = make_provider()._parse_response(raw, sample_context)
    assert len(r.evidence) >= 1
    # 必须是 context.evidence_chain 中存在的
    ctx_evs = {(e.source_type, e.description) for e in sample_context.evidence_chain}
    for e in r.evidence:
        assert (e.source_type, e.description) in ctx_evs


def test_parse_response_severity_invalid_falls_back_to_info(sample_context):
    raw = json.dumps({
        "answer": "x",
        "key_findings": [{"title": "t", "description": "d", "severity": "INVALID"}],
    })
    r = make_provider()._parse_response(raw, sample_context)
    assert r.key_findings[0].severity == "info"


def test_parse_response_urgency_invalid_falls_back_to_low(sample_context):
    raw = json.dumps({
        "answer": "x",
        "recommended_actions": [{"action": "a", "reason": "r", "urgency": "INVALID"}],
    })
    r = make_provider()._parse_response(raw, sample_context)
    assert r.recommended_actions[0].urgency == "low"


def test_parse_response_safety_violation_blocks(sample_context):
    """LLM 返回含禁词的 answer → 抛 safety_violation."""
    raw = json.dumps({
        "answer": "This building is safe based on LLM analysis.",
        "key_findings": [], "evidence": [], "recommended_actions": [],
    })
    with pytest.raises(AIProviderError) as exc:
        make_provider()._parse_response(raw, sample_context)
    assert exc.value.code == "safety_violation"
    assert "forbidden" in exc.value.message.lower()


def test_parse_response_safety_violation_in_key_finding(sample_context):
    raw = json.dumps({
        "answer": "normal text",
        "key_findings": [
            {"title": "Building will collapse", "description": "x", "severity": "high"}
        ],
        "evidence": [], "recommended_actions": [],
    })
    with pytest.raises(AIProviderError) as exc:
        make_provider()._parse_response(raw, sample_context)
    assert exc.value.code == "safety_violation"


def test_parse_response_disclaimer_always_forced(sample_context):
    """即使 LLM 返回自己的 disclaimer, 也会被 AI_DISCLAIMER 覆盖."""
    raw = json.dumps({
        "answer": "x",
        "disclaimer": "MY OWN DISCLAIMER (should be ignored)",
    })
    r = make_provider()._parse_response(raw, sample_context)
    assert r.disclaimer == AI_DISCLAIMER
    assert "MY OWN" not in r.disclaimer


# ============ End-to-end generate_* ============
@patch("app.ai.real_provider.httpx.post")
def test_generate_summary_end_to_end(mock_post, sample_context):
    payload = {
        "answer": "Building C is at prototype high risk.",
        "key_findings": [],
        "evidence": [],
        "recommended_actions": [],
    }
    mock_post.return_value = mock_response(
        200, json_payload={"choices": [{"message": {"content": json.dumps(payload)}}]}
    )
    r = make_provider().generate_summary(sample_context)
    assert r.provider == "openai-compatible"
    assert r.answer == "Building C is at prototype high risk."
    # 验证 _call_chat 用了 response_format=json_object
    call_kwargs = mock_post.call_args.kwargs
    body = call_kwargs["json"]
    assert body["response_format"] == {"type": "json_object"}


@patch("app.ai.real_provider.httpx.post")
def test_generate_answer_end_to_end(mock_post, sample_context):
    payload = {
        "answer": "Risk is HighRisk based on prototype parameters.",
        "key_findings": [],
        "evidence": [],
        "recommended_actions": [],
    }
    mock_post.return_value = mock_response(
        200, json_payload={"choices": [{"message": {"content": json.dumps(payload)}}]}
    )
    r = make_provider().generate_answer(sample_context, "Why is this building at high risk?")
    assert "prototype" in r.answer.lower()
