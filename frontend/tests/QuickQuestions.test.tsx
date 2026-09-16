/**
 * QuickQuestions 测试 · Phase 5 V3
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import QuickQuestions from "../src/components/ai/QuickQuestions";

describe("QuickQuestions", () => {
  it("renders 5 quick question buttons", () => {
    render(<QuickQuestions onSelect={() => {}} />);
    expect(screen.getByText("Summarize Health")).toBeInTheDocument();
    expect(screen.getByText("Explain Risk")).toBeInTheDocument();
    expect(screen.getByText("Explain Anomalies")).toBeInTheDocument();
    expect(screen.getByText("Explain Retrofit Priority")).toBeInTheDocument();
    expect(screen.getByText("What Should Engineers Review Next?")).toBeInTheDocument();
  });

  it("calls onSelect with correct question text on click", () => {
    const onSelect = vi.fn();
    render(<QuickQuestions onSelect={onSelect} />);
    fireEvent.click(screen.getByText("Explain Risk"));
    expect(onSelect).toHaveBeenCalledOnce();
    expect(onSelect).toHaveBeenCalledWith("Explain the current risk level and why");
  });

  it("all 5 questions are clickable", () => {
    const onSelect = vi.fn();
    render(<QuickQuestions onSelect={onSelect} />);
    fireEvent.click(screen.getByText("Summarize Health"));
    fireEvent.click(screen.getByText("Explain Anomalies"));
    fireEvent.click(screen.getByText("Explain Retrofit Priority"));
    fireEvent.click(screen.getByText("What Should Engineers Review Next?"));
    fireEvent.click(screen.getByText("Explain Risk"));
    expect(onSelect).toHaveBeenCalledTimes(5);
  });

  it("disabled state prevents click", () => {
    const onSelect = vi.fn();
    render(<QuickQuestions onSelect={onSelect} disabled={true} />);
    fireEvent.click(screen.getByText("Explain Risk"));
    expect(onSelect).not.toHaveBeenCalled();
  });

  it("disabled buttons have visual disabled state", () => {
    render(<QuickQuestions onSelect={() => {}} disabled={true} />);
    const btn = screen.getByText("Explain Risk").closest("button");
    expect(btn).toBeDisabled();
  });
});
