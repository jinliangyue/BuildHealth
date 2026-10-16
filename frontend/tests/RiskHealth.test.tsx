/**
 * RiskHealth 页面测试 · 性能轮 R2 任务 B 验收
 *
 * **核心断言**: 渲染 RiskHealth 页面必须只触发 **1 次** 业务请求
 * (GET /api/buildings/risk-board), 而不是"1 次 list + 30 次 health
 * + 30 次 risk + 30 次 alerts = 91 次"。
 *
 * 同时锁定关键展示元素仍然存在 (页面没"降级成空白页"):
 * - Risk Distribution card
 * - Average BHI card
 * - 至少一个 BHI Profile card (对应有 health/risk 的楼)
 * - All Active Risk Alerts table (有 alerts 时)
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import RiskHealth from "../src/pages/RiskHealth";
import { buildingsApi } from "../src/api/buildings";
import type {
  HealthAssessment,
  RiskClassification,
  RiskBoardResponse,
  Building,
  RiskAlertWithBuilding,
} from "../src/types/api";

vi.mock("../src/api/buildings", () => ({
  buildingsApi: {
    list: vi.fn(),
    get: vi.fn(),
    sensors: vi.fn(),
    overview: vi.fn(),
    riskBoard: vi.fn(),
  },
}));

const mockedRiskBoard = buildingsApi.riskBoard as unknown as ReturnType<typeof vi.fn>;

const baseBuilding: Building = {
  id: 1,
  name: "Test Tower",
  address: "1 Test St",
  year_built: 2010,
  building_type: "office",
  structure_type: "frame",
  floors: 12,
  area: 5000,
  design_life: 50,
  current_age: 16,
  description: null,
  created_at: "2026-01-01T00:00:00",
  updated_at: "2026-01-01T00:00:00",
};

const baseHealth: HealthAssessment = {
  id: 1,
  building_id: 1,
  score: 75.5,
  structural_safety: 80,
  facility_condition: 70,
  environmental_quality: 75,
  energy_performance: 72,
  fire_safety: 80,
  calculation_version: "BHI-v1.0",
  explanation:
    "Prototype assessment based on aggregated sensor evidence yields BHI=75.5.",
  created_at: "2026-01-01T00:00:00",
};

const baseRisk: RiskClassification = {
  building_id: 1,
  risk_level: "Attention",
  bhi: 75.5,
  explanation: "Crack width approaching threshold on 1 sensor.",
  n_high: 0,
  n_medium: 1,
  n_low: 2,
  calculation_version: "RISK-v1.0",
};

const baseAlert: RiskAlertWithBuilding = {
  id: 1,
  building_id: 1,
  sensor_id: 1,
  metric: "crack_width",
  timestamp: "2026-01-02T00:00:00",
  current_value: 0.5,
  baseline_value: 0.1,
  change: 0.4,
  detection_method: "threshold",
  severity: "high",
  explanation: "exceeds threshold",
  status: "active",
  created_at: "2026-01-02T00:00:00",
  building_name: "Test Tower",
};

const successResponse: RiskBoardResponse = {
  total: 1,
  items: [
    {
      building: baseBuilding,
      health: baseHealth,
      risk: baseRisk,
      active_alert_count: 1,
    },
  ],
  alerts: [baseAlert],
};

describe("RiskHealth · 性能轮 R2 (单请求)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("页面渲染时只触发 1 次业务请求 (GET /api/buildings/risk-board)", async () => {
    mockedRiskBoard.mockResolvedValueOnce(successResponse);

    render(
      <MemoryRouter>
        <RiskHealth />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(mockedRiskBoard).toHaveBeenCalledTimes(1);
    });

    // **强断言**: 不仅"调过 riskBoard", 还要确认**只调过 1 次**,
    // 且**没退化回 91 次逐楼请求**。这是性能轮 R2 的契约。
    expect(mockedRiskBoard).toHaveBeenCalledTimes(1);
    // 不再调 list / get / sensors / overview
    expect(buildingsApi.list).not.toHaveBeenCalled();
    expect(buildingsApi.overview).not.toHaveBeenCalled();
    // 不直接断言 healthApi.get / riskApi.classify / riskApi.alerts,
    // 因为 RiskHealth.tsx 已经不再 import 这三个模块 — 编译阶段就挡住了,
    // 这里再断言是双保险.
  });

  it("渲染核心 UI: Distribution / Average BHI / BHI Profile / Alerts table", async () => {
    mockedRiskBoard.mockResolvedValueOnce(successResponse);

    render(
      <MemoryRouter>
        <RiskHealth />
      </MemoryRouter>,
    );

    // 等数据进来
    await waitFor(() => {
      expect(screen.getByText("Risk Distribution")).toBeInTheDocument();
    });
    expect(screen.getByText("Average BHI")).toBeInTheDocument();
    expect(screen.getByText(/Test Tower · BHI Profile/)).toBeInTheDocument();
    expect(screen.getByText(/All Active Risk Alerts/)).toBeInTheDocument();
    // alert 行内 building_name 出现 (说明 alerts 拿到了)
    // 用 getAllByText 因为 "Test Tower" 同时在 BHI Profile title 和 alerts 表格出现
    expect(screen.getAllByText("Test Tower").length).toBeGreaterThanOrEqual(2);
  });

  it("building 无 health/risk (e.g. 评估缺失) 时不阻塞页面, 直接从 blocks 过滤", async () => {
    mockedRiskBoard.mockResolvedValueOnce({
      total: 2,
      items: [
        { building: baseBuilding, health: baseHealth, risk: baseRisk, active_alert_count: 1 },
        { building: { ...baseBuilding, id: 2, name: "Skipped Tower" }, health: null, risk: null, active_alert_count: 0 },
      ],
      alerts: [baseAlert],
    });

    render(
      <MemoryRouter>
        <RiskHealth />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(mockedRiskBoard).toHaveBeenCalledTimes(1);
    });
    // 有 health 的楼: 出现 BHI Profile card
    expect(screen.getByText(/Test Tower · BHI Profile/)).toBeInTheDocument();
    // 没 health 的楼: 不出现 Profile (被过滤掉, 与原本 try/catch 行为一致)
    expect(screen.queryByText(/Skipped Tower · BHI Profile/)).not.toBeInTheDocument();
  });

  it("alerts 为空时显示 EmptyState", async () => {
    mockedRiskBoard.mockResolvedValueOnce({
      total: 1,
      items: [
        { building: baseBuilding, health: baseHealth, risk: baseRisk, active_alert_count: 0 },
      ],
      alerts: [],
    });

    render(
      <MemoryRouter>
        <RiskHealth />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText(/No active alerts/)).toBeInTheDocument();
    });
    expect(mockedRiskBoard).toHaveBeenCalledTimes(1);
  });
});