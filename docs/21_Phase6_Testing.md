# 21 · Phase 6A Testing  Phase 6A 测试策略

> Phase 6A · Real LLM Provider 测试覆盖
> Backend 2 新文件 + 1 扩展 · Frontend 1 新文件

**文档版本**：v0.1 · Phase 6A
**最后更新**：2026-09-15
**状态**：Implemented & tested

---

## 1. 测试目标

- **V1+V2+V3 回归**: 278 个 backend tests + 60 个 frontend tests 必须全部继续通过
- **V6A 新增**: 至少 40 个 backend tests + 5 个 frontend tests
- **Real Provider mock 友好**: 不真实调用外部 API, 用 `unittest.mock` 模拟 httpx
- **Mock Mode 不退化**: 所有 V1+V2+V3 测试零修改全保留

---

## 2. Backend 测试 (321 total)

### V1+V2+V3 保留 (278 tests)

零修改. Phase 6A 的所有改动都隔离在 `app/ai/` 和 `app/api/ai.py` 范围.

### V6A 新增 (43 tests · 3 文件)

| 文件 | 测试数 | 主题 |
|---|---|---|
| test_real_provider.py | ~30 | OpenAICompatibleProvider 全部方法 (mock httpx) |
| test_ai_provider_factory.py | 10 | env-based 4 路径 + singleton + config |
| test_ai_api.py (扩展) | 3 | misconfigured 503 + health 200 显式 provider_not_configured |

**Backend 总计: 321 tests**

---

## 3. Frontend 测试 (65 total)

### V1+V2+V3 保留 (60 tests)

零修改. Phase 6A 的改动只新增 ProviderBadge 子组件, 不影响现有页面渲染.

### V6A 新增 (5 tests · 1 文件)

| 文件 | 测试数 | 主题 |
|---|---|---|
| AIProviderStatus.test.tsx | 5 | Mock Mode / Live AI / Not Configured 3 mode + precedence + 未来 provider |

**Frontend 总计: 65 tests**

---

## 4. Real Provider 测试策略

**核心原则**: 不真实调用任何 LLM. 全部用 `unittest.mock` 模拟 httpx.

### 4.1 构造校验 (3 tests)
- 缺 api_key → ValueError
- 缺 base_url → ValueError
- 末尾 `/` 去除

### 4.2 health_check (5 tests)
- 200 → "ok"
- 401 → "provider_error" + 401 in message
- 403 → "provider_error" + 403
- httpx.TimeoutException → "provider_error" + "timeout"
- httpx.ConnectError → "provider_error"

### 4.3 _call_chat (9 tests)
- 200 正常 → 返回 content
- 401 → AIProviderError("auth_error")
- 429 → AIProviderError("rate_limit")
- 500 → AIProviderError("provider_error")
- 400 → AIProviderError("client_error")
- httpx.TimeoutException → AIProviderError("timeout")
- httpx.HTTPError → AIProviderError("network_error")
- 非 JSON 响应 → AIProviderError("malformed_response")
- 缺 choices → AIProviderError("malformed_response")

### 4.4 _parse_response (~10 tests)
- 正常 JSON → AIResponse (provider="openai-compatible", disclaimer=AI_DISCLAIMER)
- 非 JSON → AIProviderError
- 非 dict → AIProviderError
- 含 ```json``` 围栏 → 正确解析
- 缺 key_findings / actions / evidence → 空 list
- 缺 evidence → 回退到 context.evidence_chain[:5] (grounding)
- severity 不合法 → "info"
- urgency 不合法 → "low"
- answer 含禁词 → AIProviderError("safety_violation")
- key_finding 含禁词 → AIProviderError("safety_violation")
- LLM 的 disclaimer 被强制覆盖

### 4.5 End-to-end (2 tests)
- generate_summary (mock httpx) → 完整 AIResponse
- generate_answer (mock httpx) → 完整 AIResponse
- 验证 response_format={"type": "json_object"} 传给 LLM

---

## 5. Provider Factory 测试

### 5.1 Env 路径 (4 tests)
- `AI_PROVIDER=mock` → MockProvider
- `AI_PROVIDER=openai-compatible` + 完整 config → OpenAICompatibleProvider
- `AI_PROVIDER=openai-compatible` + 缺 AI_API_KEY → _MisconfiguredProvider
- `AI_PROVIDER=openai-compatible` + 缺 AI_BASE_URL → _MisconfiguredProvider
- `AI_PROVIDER=unknown` → MockProvider (降级)

### 5.2 Singleton (2 tests)
- 同一 env → 同一 instance
- `reset_ai_provider()` 清理 singleton

### 5.3 Misconfigured 行为 (1 test)
- `_MisconfiguredProvider.generate_summary()` → AIProviderError("config_error")

### 5.4 Config 传递 (1 test)
- `AI_REQUEST_TIMEOUT=45` / `AI_MAX_TOKENS=2000` / `AI_TEMPERATURE=0.5` → provider 字段正确

### 5.5 关键设计: `get_ai_provider()` 每次调用读 env

`monkeypatch.setenv` 必须生效. 通过在 `provider_factory.py` 中用 `os.getenv()` 而非 import from `config` 实现.

---

## 6. API Misconfigured 测试

### 6.1 503 端点 (2 tests)
- `POST /api/ai/buildings/{id}/summary` 在 `AI_PROVIDER=openai-compatible` + 缺 key → 503 + body detail.provider_error="config_error"
- `POST /api/ai/buildings/{id}/ask` → 同样 503

### 6.2 health 端点 (1 test)
- `GET /api/ai/health` → 200 + body status="provider_not_configured" (HTTP 200 是故意的, health 端点总是 200)

---

## 7. Frontend ProviderBadge 测试

5 个测试覆盖:
- mock + status=ok → "Mock Mode" (data-mode="mock")
- openai-compatible + status=ok → "Live AI · openai-compatible" (data-mode="live")
- openai-compatible + status=provider_not_configured → "Not Configured" (data-mode="misconfigured")
- provider_not_configured 优先级最高
- 未知 provider → 仍 "live" + 显示 provider 名

---

## 8. 回归保护

- V1 76 tests 不能动
- V2 123 tests 不能动
- V3 79 tests 不能动
- `AI_FORBIDDEN_PHRASES` 列表 (redlines.py) 与 V3 test_ai_redlines.py 完全一致 (V1 test_engineering_redlines.py 排除 redlines.py 文件本身)

---

**文档版本**：v0.1 · Phase 6A
**最后更新**：2026-09-15
**状态**：Implemented & tested
