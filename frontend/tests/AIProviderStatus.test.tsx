/**
 * ProviderBadge 测试 · Phase 6A
 * 验证 Mock / Live / Not Configured 三种 mode 正确显示.
 */
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ProviderBadge } from "../src/pages/AIAssistant";
import type { AIHealthStatus } from "../src/types/api";

const baseHealth: AIHealthStatus = {
  status: "ok",
  provider: "mock",
  model: "mock-deterministic-v1",
  message: "OK",
};

describe("ProviderBadge", () => {
  it("renders Mock Mode for mock provider with status=ok", () => {
    render(<ProviderBadge health={baseHealth} />);
    const badge = screen.getByTestId("provider-badge");
    expect(badge).toHaveAttribute("data-mode", "mock");
    expect(badge).toHaveTextContent(/Mock Mode/i);
  });

  it("renders Live AI for openai-compatible provider with status=ok", () => {
    const h: AIHealthStatus = {
      ...baseHealth,
      provider: "openai-compatible",
      model: "gpt-4",
      message: "Live",
    };
    render(<ProviderBadge health={h} />);
    const badge = screen.getByTestId("provider-badge");
    expect(badge).toHaveAttribute("data-mode", "live");
    expect(badge).toHaveTextContent(/Live AI/i);
    expect(badge).toHaveTextContent("openai-compatible");
  });

  it("renders Not Configured for status=provider_not_configured", () => {
    const h: AIHealthStatus = {
      status: "provider_not_configured",
      provider: "openai-compatible",
      model: "(misconfigured)",
      message: "AI_API_KEY is not set",
    };
    render(<ProviderBadge health={h} />);
    const badge = screen.getByTestId("provider-badge");
    expect(badge).toHaveAttribute("data-mode", "misconfigured");
    expect(badge).toHaveTextContent(/Not Configured/i);
  });

  it("provider_not_configured takes precedence over provider name", () => {
    const h: AIHealthStatus = {
      status: "provider_not_configured",
      provider: "openai-compatible",
      model: "(misconfigured)",
      message: "missing key",
    };
    render(<ProviderBadge health={h} />);
    const badge = screen.getByTestId("provider-badge");
    expect(badge).toHaveAttribute("data-mode", "misconfigured");
    // NOT "Live AI"
    expect(badge.textContent).not.toMatch(/Live AI/);
  });

  it("renders without crashing for unknown future provider", () => {
    const h: AIHealthStatus = {
      ...baseHealth,
      // Intentionally a value the AIProviderType union does not include,
      // so this exercises the fallback render branch rather than a known path.
      provider: "future-anthropic-2027" as unknown as AIHealthStatus["provider"],
      model: "x",
    };
    render(<ProviderBadge health={h} />);
    const badge = screen.getByTestId("provider-badge");
    expect(badge).toHaveAttribute("data-mode", "live");
    expect(badge).toHaveTextContent("future-anthropic-2027");
  });
});
