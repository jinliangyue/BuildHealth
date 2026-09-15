/**
 * ErrorBoundary 测试
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import ErrorBoundary from "../src/components/ErrorBoundary";

function Boom(): JSX.Element {
  throw new Error("render-failure-test");
}

describe("ErrorBoundary", () => {
  it("catches render errors and shows fallback", () => {
    // 抑制 console.error（react 渲染错误日志）
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    render(
      <ErrorBoundary>
        <Boom />
      </ErrorBoundary>,
    );
    expect(screen.getByText(/Something went wrong/i)).toBeInTheDocument();
    expect(screen.getByText("render-failure-test")).toBeInTheDocument();
    expect(screen.getByText(/Try Again/i)).toBeInTheDocument();
    expect(screen.getByText(/Reload Page/i)).toBeInTheDocument();
    spy.mockRestore();
  });

  it("renders children when no error", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    render(
      <ErrorBoundary>
        <div>OK content</div>
      </ErrorBoundary>,
    );
    expect(screen.getByText("OK content")).toBeInTheDocument();
    spy.mockRestore();
  });
});
