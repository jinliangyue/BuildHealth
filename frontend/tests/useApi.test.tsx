/**
 * useApi hook 测试 · 覆盖 loading / success / error / refetch
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { useApi } from "../src/hooks/useApi";

function TestComponent({ fetcher }: { fetcher: () => Promise<string> }) {
  const { data, loading, error, refetch } = useApi(fetcher);
  return (
    <div>
      <div data-testid="loading">{String(loading)}</div>
      <div data-testid="data">{data ?? "null"}</div>
      <div data-testid="error">{error ?? "null"}</div>
      <button onClick={() => void refetch()}>Refetch</button>
    </div>
  );
}

describe("useApi · loading state", () => {
  it("starts in loading state", () => {
    const slow = () => new Promise<string>(() => {});
    render(<TestComponent fetcher={slow} />);
    expect(screen.getByTestId("loading").textContent).toBe("true");
  });
});

describe("useApi · success", () => {
  it("resolves to data", async () => {
    const ok = () => Promise.resolve("hello");
    render(<TestComponent fetcher={ok} />);
    await waitFor(() => {
      expect(screen.getByTestId("loading").textContent).toBe("false");
    });
    expect(screen.getByTestId("data").textContent).toBe("hello");
    expect(screen.getByTestId("error").textContent).toBe("null");
  });
});

describe("useApi · error", () => {
  it("captures error message", async () => {
    const boom = () => Promise.reject(new Error("boom"));
    render(<TestComponent fetcher={boom} />);
    await waitFor(() => {
      expect(screen.getByTestId("loading").textContent).toBe("false");
    });
    expect(screen.getByTestId("error").textContent).toBe("boom");
    expect(screen.getByTestId("data").textContent).toBe("null");
  });
});

describe("useApi · refetch", () => {
  it("refetch triggers re-execution", async () => {
    let count = 0;
    const fn = () => {
      count += 1;
      return Promise.resolve(`r${count}`);
    };
    render(<TestComponent fetcher={fn} />);
    await waitFor(() => {
      expect(screen.getByTestId("data").textContent).toBe("r1");
    });
    fireEvent.click(screen.getByText("Refetch"));
    await waitFor(() => {
      expect(screen.getByTestId("data").textContent).toBe("r2");
    });
  });
});
