/**
 * Charts 测试 · 不依赖真实 ECharts 渲染（jsdom 环境）
 * - 验证 component 接收数据并尝试渲染
 * - 验证 empty data 处理
 */
import { describe, it, expect, vi } from "vitest";

// Mock echarts-for-react 避免 jsdom 中真实 canvas 绘制
vi.mock("echarts-for-react", () => ({
  default: ({ option }: { option: unknown }) => (
    <div data-testid="echarts-mock">{JSON.stringify(option)}</div>
  ),
}));

// Mock echarts core 避免 side-effect
vi.mock("../src/components/charts/echarts", () => ({}));

import { render } from "@testing-library/react";
import TrendChart from "../src/components/charts/TrendChart";
import BhiRadar from "../src/components/charts/BhiRadar";
import DistributionPie from "../src/components/charts/DistributionPie";

describe("TrendChart", () => {
  it("renders with series data", () => {
    const { getByTestId } = render(
      <TrendChart
        series={[
          { ts: "2026-01-01T00:00:00", value: 0.1 },
          { ts: "2026-01-02T00:00:00", value: 0.2 },
        ]}
        unit="mm"
        metricLabel="Crack Width"
      />,
    );
    const node = getByTestId("echarts-mock");
    expect(node.textContent).toContain("Crack Width");
    expect(node.textContent).toContain("mm");
  });

  it("renders empty data without crash", () => {
    const { getByTestId } = render(
      <TrendChart series={[]} unit="mm" metricLabel="X" />,
    );
    expect(getByTestId("echarts-mock")).toBeInTheDocument();
  });

  it("accepts anomaly points", () => {
    const { getByTestId } = render(
      <TrendChart
        series={[{ ts: "2026-01-01T00:00:00", value: 0.5 }]}
        anomalies={[
          {
            ts: "2026-01-01T00:00:00",
            value: 0.5,
            severity: "high",
            method: "threshold",
          },
        ]}
        unit="mm"
        metricLabel="X"
      />,
    );
    expect(getByTestId("echarts-mock")).toBeInTheDocument();
  });
});

describe("BhiRadar", () => {
  it("renders with 5 dimension scores", () => {
    const { getByTestId } = render(
      <BhiRadar
        scores={{
          structural_safety: 80,
          facility_condition: 90,
          environmental_quality: 70,
          energy_performance: 85,
          fire_safety: 75,
        }}
      />,
    );
    expect(getByTestId("echarts-mock")).toBeInTheDocument();
  });

  it("handles all-zero scores", () => {
    const { getByTestId } = render(
      <BhiRadar
        scores={{
          structural_safety: 0,
          facility_condition: 0,
          environmental_quality: 0,
          energy_performance: 0,
          fire_safety: 0,
        }}
      />,
    );
    expect(getByTestId("echarts-mock")).toBeInTheDocument();
  });
});

describe("DistributionPie", () => {
  it("renders with risk distribution", () => {
    const { getByTestId } = render(
      <DistributionPie
        distribution={{ Normal: 1, Attention: 1, Abnormal: 0, HighRisk: 1 }}
      />,
    );
    expect(getByTestId("echarts-mock")).toBeInTheDocument();
  });

  it("handles all-zero distribution", () => {
    const { getByTestId } = render(
      <DistributionPie
        distribution={{ Normal: 0, Attention: 0, Abnormal: 0, HighRisk: 0 }}
      />,
    );
    expect(getByTestId("echarts-mock")).toBeInTheDocument();
  });
});
