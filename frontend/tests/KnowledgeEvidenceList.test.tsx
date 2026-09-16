/**
 * KnowledgeEvidenceList 测试 · Phase 6B
 *
 * 覆盖: 空态 / 渲染 / relevance 百分比 / 边界分数 / 安全提示语.
 */
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import KnowledgeEvidenceList from "../src/components/ai/KnowledgeEvidenceList";
import type { KnowledgeEvidence } from "../src/types/api";

const item: KnowledgeEvidence = {
  document: "risk_classification.md",
  section: "Levels",
  content: "Prototype risk tiers: Normal, Attention, Abnormal, HighRisk.",
  relevance_score: 0.7315,
  source: "BuildHealth Internal Engineering Notes",
  chunk_id: "risk_classification.md::1",
};

describe("KnowledgeEvidenceList", () => {
  it("renders the empty state when there are no items", () => {
    render(<KnowledgeEvidenceList items={[]} />);
    expect(screen.getByText(/No knowledge sources retrieved/i)).toBeInTheDocument();
  });

  it("renders document, section and content", () => {
    render(<KnowledgeEvidenceList items={[item]} />);
    expect(screen.getByText("risk_classification.md")).toBeInTheDocument();
    expect(screen.getByText("Levels")).toBeInTheDocument();
    expect(screen.getByText(/Prototype risk tiers/)).toBeInTheDocument();
  });

  it("renders the source label", () => {
    render(<KnowledgeEvidenceList items={[item]} />);
    expect(
      screen.getByText("BuildHealth Internal Engineering Notes"),
    ).toBeInTheDocument();
  });

  it("formats relevance_score as a rounded percentage", () => {
    render(<KnowledgeEvidenceList items={[item]} />);
    expect(screen.getByText("73%")).toBeInTheDocument();
  });

  it("clamps out-of-range relevance scores", () => {
    render(
      <KnowledgeEvidenceList
        items={[
          { ...item, chunk_id: "a::0", relevance_score: 1.8 },
          { ...item, chunk_id: "b::0", relevance_score: -0.5 },
        ]}
      />,
    );
    expect(screen.getByText("100%")).toBeInTheDocument();
    expect(screen.getByText("0%")).toBeInTheDocument();
  });

  it("carries the non-authoritative background notice", () => {
    render(<KnowledgeEvidenceList items={[item]} />);
    expect(screen.getByText(/General background from/i)).toBeInTheDocument();
    expect(screen.getByText(/not an official standard/i)).toBeInTheDocument();
    expect(screen.getByText(/not measurements of this building/i)).toBeInTheDocument();
  });

  it("renders multiple chunks", () => {
    render(
      <KnowledgeEvidenceList
        items={[
          item,
          { ...item, document: "anomaly_detection.md", chunk_id: "anomaly_detection.md::0" },
        ]}
      />,
    );
    expect(screen.getByText("risk_classification.md")).toBeInTheDocument();
    expect(screen.getByText("anomaly_detection.md")).toBeInTheDocument();
  });
});
