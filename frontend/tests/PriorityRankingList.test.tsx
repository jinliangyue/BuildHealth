/**
 * PriorityRankingList 测试 · Phase 4 V2
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import PriorityRankingList from "../src/components/retrofit/PriorityRankingList";
import type { RetrofitRecommendation } from "../src/types/api";

function makeRec(
  id: number,
  issue_type: string,
  priority_score: number,
  urgency: "low" | "medium" | "high" | "critical" = "medium",
): RetrofitRecommendation {
  return {
    id,
    building_id: 1,
    component_id: 1,
    category: "Structural",
    issue_type,
    title: `Test Recommendation ${id}`,
    recommendation: "Detailed inspection",
    rationale: "Crack detected",
    next_action: "Engineering review",
    urgency,
    estimated_cost_level: "medium",
    expected_benefit: "high",
    source: "rule:crack_growth",
    calculation_version: "REC-v1.0",
    created_at: "2026-09-15T00:00:00",
    evidence: {
      sensors: [],
      anomalies: [],
      bhi_context: null,
      risk_context: null,
      anomaly_summary: null,
    },
    priority_score,
    priority_breakdown: {
      risk_severity: 80,
      risk_severity_contribution: 28,
      trend: 50,
      trend_contribution: 12.5,
      component_importance: 100,
      component_importance_contribution: 20,
      urgency: 50,
      urgency_contribution: 5,
      cost_efficiency: 60,
      cost_efficiency_contribution: 6,
      total: priority_score,
      calculation_version: "RP-v1.0",
    },
  };
}

describe("PriorityRankingList", () => {
  it("renders empty state when no items", () => {
    render(<PriorityRankingList items={[]} />);
    expect(screen.getByText(/No retrofit recommendations/i)).toBeInTheDocument();
  });

  it("renders items with sequential numbers", () => {
    const items = [
      makeRec(1, "crack_growth", 91),
      makeRec(2, "tilt_trend", 84),
      makeRec(3, "moisture_control", 63),
    ];
    render(<PriorityRankingList items={items} />);
    expect(screen.getByText("01")).toBeInTheDocument();
    expect(screen.getByText("02")).toBeInTheDocument();
    expect(screen.getByText("03")).toBeInTheDocument();
  });

  it("renders priority scores", () => {
    const items = [makeRec(1, "crack_growth", 91.5)];
    render(<PriorityRankingList items={items} />);
    expect(screen.getByText("91.5")).toBeInTheDocument();
  });

  it("renders urgency badge", () => {
    const items = [makeRec(1, "crack_growth", 91, "high")];
    render(<PriorityRankingList items={items} />);
    // urgency shows as "high" in uppercase via CSS
    const badges = screen.getAllByText(/high/i);
    expect(badges.length).toBeGreaterThan(0);
  });

  it("calls onSelect when item clicked", () => {
    const onSelect = vi.fn();
    const items = [makeRec(1, "crack_growth", 91)];
    render(<PriorityRankingList items={items} onSelect={onSelect} />);
    fireEvent.click(screen.getByText(/Test Recommendation 1/));
    expect(onSelect).toHaveBeenCalledOnce();
  });

  it("highlights selected item", () => {
    const items = [makeRec(1, "crack_growth", 91), makeRec(2, "tilt_trend", 80)];
    const { container } = render(
      <PriorityRankingList items={items} selectedId={1} />,
    );
    // selected item has bg-blue-50
    const selectedDiv = container.querySelector(".bg-blue-50");
    expect(selectedDiv).toBeInTheDocument();
  });

  it("hides header when showHeader=false", () => {
    const items = [makeRec(1, "crack_growth", 91)];
    render(<PriorityRankingList items={items} showHeader={false} />);
    expect(screen.queryByText("Priority Ranking")).not.toBeInTheDocument();
  });
});
