/**
 * WorkflowStrip 测试
 *
 * 该组件是导航定位用的，不渲染任何工程数据。测试锁定两点:
 * 1. 链条步骤齐全且顺序稳定
 * 2. 每一步都链到 app 中真实存在的路由
 */
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import WorkflowStrip from "../src/components/layout/WorkflowStrip";

/** Routes declared in App.tsx — keep in sync if routes change. */
const APP_ROUTES = new Set([
  "/",
  "/buildings",
  "/monitoring",
  "/risk-health",
  "/retrofit",
  "/ai-assistant",
  "/data",
  "/settings",
]);

describe("WorkflowStrip", () => {
  it("renders every step of the engineering chain in order", () => {
    render(
      <MemoryRouter>
        <WorkflowStrip />
      </MemoryRouter>,
    );
    const labels = [
      "Building",
      "Monitoring",
      "Anomaly",
      "Health & Risk",
      "Retrofit",
      "AI Explanation",
    ];
    const rendered = screen
      .getAllByRole("link")
      .map((a) => a.textContent ?? "");
    labels.forEach((label, idx) => {
      expect(rendered[idx]).toContain(label);
    });
  });

  it("links only to routes that exist in the app", () => {
    render(
      <MemoryRouter>
        <WorkflowStrip />
      </MemoryRouter>,
    );
    for (const link of screen.getAllByRole("link")) {
      const href = link.getAttribute("href") ?? "";
      expect(APP_ROUTES.has(href)).toBe(true);
    }
  });

  it("states that parameters are prototype decision-support values", () => {
    render(
      <MemoryRouter>
        <WorkflowStrip />
      </MemoryRouter>,
    );
    expect(
      screen.getByText(/prototype decision-support values/i),
    ).toBeInTheDocument();
  });

  it("does not render any engineering numbers", () => {
    const { container } = render(
      <MemoryRouter>
        <WorkflowStrip />
      </MemoryRouter>,
    );
    // 方向性组件不应出现分数/阈值数字
    expect(container.textContent ?? "").not.toMatch(/\d{2,}/);
  });
});
