/**
 * PriorityScoreCard 测试 · Phase 4 V2
 */
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import PriorityScoreCard from "../src/components/retrofit/PriorityScoreCard";

describe("PriorityScoreCard", () => {
  it("renders score, level, and version", () => {
    render(
      <PriorityScoreCard
        score={82.5}
        level="High"
        calculationVersion="RP-v1.0"
      />,
    );
    expect(screen.getByText("82.5")).toBeInTheDocument();
    expect(screen.getByText(/High Priority/i)).toBeInTheDocument();
    expect(screen.getByText(/RP-v1.0/)).toBeInTheDocument();
  });

  it("renders Low level for low score", () => {
    render(
      <PriorityScoreCard score={15.0} level="Low" calculationVersion="RP-v1.0" />,
    );
    expect(screen.getByText("15.0")).toBeInTheDocument();
    expect(screen.getByText(/Low Priority/i)).toBeInTheDocument();
  });

  it("renders Very High level", () => {
    render(
      <PriorityScoreCard
        score={95.0}
        level="VeryHigh"
        calculationVersion="RP-v1.0"
      />,
    );
    expect(screen.getByText("95.0")).toBeInTheDocument();
    expect(screen.getByText(/Very High Priority/i)).toBeInTheDocument();
  });

  it("contains Prototype disclaimer wording", () => {
    render(
      <PriorityScoreCard
        score={50.0}
        level="Medium"
        calculationVersion="RP-v1.0"
      />,
    );
    expect(screen.getByText(/Prototype/i)).toBeInTheDocument();
    expect(screen.getByText(/professional review/i)).toBeInTheDocument();
  });

  it("renders 0 score correctly", () => {
    render(
      <PriorityScoreCard score={0} level="Low" calculationVersion="RP-v1.0" />,
    );
    expect(screen.getByText("0.0")).toBeInTheDocument();
  });

  it("renders subtitle when provided", () => {
    render(
      <PriorityScoreCard
        score={50}
        level="Medium"
        calculationVersion="RP-v1.0"
        subtitle="3 recommendations"
      />,
    );
    expect(screen.getByText("3 recommendations")).toBeInTheDocument();
  });
});
