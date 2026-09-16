/**
 * AIResponsePanel 测试 · Phase 5 V3
 */
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import AIResponsePanel from "../src/components/ai/AIResponsePanel";
import type { AIResponse } from "../src/types/api";

const baseResponse: AIResponse = {
  answer: "Building X is at high risk based on prototype parameters.",
  key_findings: [
    {
      title: "BHI = 54.27",
      description: "Weakened by structural anomalies.",
      severity: "high",
    },
    {
      title: "Risk: HighRisk",
      description: "86 HIGH-severity prototype anomalies.",
      severity: "high",
    },
  ],
  evidence: [
    {
      source_type: "health",
      source_id: null,
      metric: null,
      description: "BHI=54.27 (calculation_version=BHI-v1.0)",
      reference_path: "/api/buildings/1/health",
    },
    {
      source_type: "risk",
      source_id: null,
      metric: null,
      description: "Risk level: HighRisk",
      reference_path: "/api/buildings/1/risk",
    },
  ],
  recommended_actions: [
    {
      action: "Review with engineering personnel",
      reason: "Prototype risk classification indicates concern.",
      urgency: "high",
    },
  ],
  disclaimer:
    "AI Engineering Assistant output is engineering decision support only. " +
    "Based on Prototype BHI / Risk / Priority parameters. " +
    "Qualified professional review is required.",
  provider: "mock",
  model: "mock-deterministic-v1",
  calculation_version: "AI-v1.0",
  created_at: "2026-09-15T00:00:00",
};

describe("AIResponsePanel", () => {
  it("renders answer, key_findings, evidence, recommended_actions, disclaimer", () => {
    render(
      <MemoryRouter>
        <AIResponsePanel response={baseResponse} />
      </MemoryRouter>,
    );
    // answer
    expect(screen.getByText(/Building X is at high risk/)).toBeInTheDocument();
    // key findings
    expect(screen.getByText("BHI = 54.27")).toBeInTheDocument();
    expect(screen.getByText("Risk: HighRisk")).toBeInTheDocument();
    // evidence (EvidenceList renders)
    expect(screen.getByText(/BHI=54.27/)).toBeInTheDocument();
    // recommended actions
    expect(screen.getByText(/Review with engineering personnel/)).toBeInTheDocument();
    // disclaimer
    expect(
      screen.getByText(/AI Engineering Assistant output is engineering decision support only/i),
    ).toBeInTheDocument();
  });

  it("displays provider + model + version tags", () => {
    render(
      <MemoryRouter>
        <AIResponsePanel response={baseResponse} />
      </MemoryRouter>,
    );
    expect(screen.getByText("mock")).toBeInTheDocument();
    expect(screen.getByText("mock-deterministic-v1")).toBeInTheDocument();
    expect(screen.getByText("AI-v1.0")).toBeInTheDocument();
  });

  it("renders without crashing when key_findings is empty", () => {
    render(
      <MemoryRouter>
        <AIResponsePanel response={{ ...baseResponse, key_findings: [] }} />
      </MemoryRouter>,
    );
    expect(screen.getByText(/Building X is at high risk/)).toBeInTheDocument();
  });

  it("renders without crashing when evidence is empty", () => {
    render(
      <MemoryRouter>
        <AIResponsePanel response={{ ...baseResponse, evidence: [] }} />
      </MemoryRouter>,
    );
    expect(screen.getByText(/Building X is at high risk/)).toBeInTheDocument();
  });

  it("contains the engineering disclaimer", () => {
    render(
      <MemoryRouter>
        <AIResponsePanel response={baseResponse} />
      </MemoryRouter>,
    );
    expect(screen.getByText(/AI-v1.0/)).toBeInTheDocument();
    expect(screen.getByText(/qualified professional review/i)).toBeInTheDocument();
  });
});
