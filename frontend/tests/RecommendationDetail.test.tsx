/**
 * RecommendationDetail 测试 · Phase 4 V2
 */
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import RecommendationDetail from "../src/components/retrofit/RecommendationDetail";
import type { RetrofitRecommendation } from "../src/types/api";

const baseRec: RetrofitRecommendation = {
  id: 1,
  building_id: 1,
  component_id: 1,
  category: "Structural",
  issue_type: "crack_growth",
  title: "Conduct detailed inspection of affected structural components",
  recommendation:
    "Conduct detailed inspection of affected structural components to evaluate crack propagation.",
  rationale: "Crack monitoring indicates a sustained increasing trend.",
  next_action: "Review by qualified engineering personnel.",
  urgency: "high",
  estimated_cost_level: "medium",
  expected_benefit: "high",
  source: "rule:crack_growth",
  calculation_version: "REC-v1.0",
  created_at: "2026-09-15T00:00:00",
  evidence: {
    sensors: [
      {
        sensor_id: 3,
        metric: "crack_width",
        name: "Crack Width Sensor #03",
        unit: "mm",
        location: "F1-Column-A1",
        recent_values: [
          { timestamp: "2026-09-01T00:00:00", value: 0.2 },
          { timestamp: "2026-09-02T00:00:00", value: 0.3 },
        ],
        anomaly_count_by_severity: { high: 4, medium: 1, low: 0 },
      },
    ],
    anomalies: [
      {
        sensor_id: 3,
        metric: "crack_width",
        timestamp: "2026-09-01T00:00:00",
        current_value: 0.45,
        detection_method: "threshold",
        severity: "high",
        explanation: "exceeded threshold",
      },
    ],
    bhi_context: { score: 54.27, weakest_dimension: "structural_safety" },
    risk_context: { risk_level: "HighRisk", explanation: "High risk building" },
    anomaly_summary: { total: 86, high: 86, medium: 0 },
  },
  priority_score: 91.5,
  priority_breakdown: {
    risk_severity: 100,
    risk_severity_contribution: 35,
    trend: 80,
    trend_contribution: 20,
    component_importance: 100,
    component_importance_contribution: 20,
    urgency: 80,
    urgency_contribution: 8,
    cost_efficiency: 60,
    cost_efficiency_contribution: 6,
    total: 91.5,
    calculation_version: "RP-v1.0",
  },
};

describe("RecommendationDetail", () => {
  it("renders title, recommendation, and priority score", () => {
    render(<RecommendationDetail rec={baseRec} />);
    // title appears as first h3, use getAllByRole
    const headings = screen.getAllByRole("heading", { level: 3 });
    expect(headings[0].textContent).toMatch(/Conduct detailed inspection/i);
    expect(screen.getByText("91.5")).toBeInTheDocument();
  });

  it("renders all 5 priority breakdown dimensions", () => {
    render(<RecommendationDetail rec={baseRec} />);
    expect(screen.getByText("Risk Severity")).toBeInTheDocument();
    expect(screen.getByText("Trend / Deterioration")).toBeInTheDocument();
    expect(screen.getByText("Component Importance")).toBeInTheDocument();
    expect(screen.getByText("Intervention Urgency")).toBeInTheDocument();
    expect(screen.getByText("Cost Efficiency")).toBeInTheDocument();
  });

  it("renders urgency, cost, benefit badges", () => {
    render(<RecommendationDetail rec={baseRec} />);
    expect(screen.getByText(/Urgency: high/)).toBeInTheDocument();
    expect(screen.getByText(/Cost: medium/)).toBeInTheDocument();
    expect(screen.getByText(/Benefit: high/)).toBeInTheDocument();
  });

  it("contains Prototype disclaimer", () => {
    render(<RecommendationDetail rec={baseRec} />);
    expect(screen.getByText(/Prototype Retrofit Recommendation/i)).toBeInTheDocument();
  });

  it("renders rationale and next action", () => {
    render(<RecommendationDetail rec={baseRec} />);
    expect(
      screen.getByText(/Crack monitoring indicates a sustained increasing trend/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Review by qualified engineering personnel/i),
    ).toBeInTheDocument();
  });

  it("renders evidence chain with sensor info", () => {
    render(<RecommendationDetail rec={baseRec} />);
    expect(screen.getByText(/Crack Width Sensor #03/)).toBeInTheDocument();
    expect(screen.getByText("54.27")).toBeInTheDocument(); // BHI score
    expect(screen.getByText("HighRisk")).toBeInTheDocument(); // risk level
  });

  it("shows source and calculation version", () => {
    render(<RecommendationDetail rec={baseRec} />);
    expect(screen.getByText(/rule:crack_growth/)).toBeInTheDocument();
    expect(screen.getByText(/REC-v1.0/)).toBeInTheDocument();
  });
});
