/**
 * UI 组件测试
 */
import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import {
  LoadingState,
  ErrorState,
  EmptyState,
  Card,
  KPITile,
  Badge,
} from "../src/components/ui/StateViews";

describe("LoadingState", () => {
  it("renders default label", () => {
    render(<LoadingState />);
    expect(screen.getByText("Loading...")).toBeInTheDocument();
  });
  it("renders custom label", () => {
    render(<LoadingState label="Fetching buildings" />);
    expect(screen.getByText("Fetching buildings")).toBeInTheDocument();
  });
});

describe("ErrorState", () => {
  it("shows error message", () => {
    render(<ErrorState message="Network failed" />);
    expect(screen.getByText("Network failed")).toBeInTheDocument();
    expect(screen.getByText(/API request failed/)).toBeInTheDocument();
  });
  it("calls retry handler when button clicked", () => {
    let called = false;
    render(<ErrorState message="oops" onRetry={() => (called = true)} />);
    fireEvent.click(screen.getByText("Retry"));
    expect(called).toBe(true);
  });
});

describe("EmptyState", () => {
  it("renders title and hint", () => {
    render(<EmptyState title="No data" hint="Try again later" />);
    expect(screen.getByText("No data")).toBeInTheDocument();
    expect(screen.getByText("Try again later")).toBeInTheDocument();
  });
});

describe("Card", () => {
  it("renders title and children", () => {
    render(
      <Card title="Test Card" subtitle="Sub">
        <div>Body</div>
      </Card>,
    );
    expect(screen.getByText("Test Card")).toBeInTheDocument();
    expect(screen.getByText("Sub")).toBeInTheDocument();
    expect(screen.getByText("Body")).toBeInTheDocument();
  });
});

describe("KPITile", () => {
  it("renders label and value", () => {
    render(<KPITile label="Total" value={42} />);
    expect(screen.getByText("Total")).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
  });
  it("applies danger tone class", () => {
    const { container } = render(<KPITile label="Alerts" value={5} tone="danger" />);
    expect(container.querySelector(".text-red-600")).toBeInTheDocument();
  });
});

describe("Badge", () => {
  it("renders children with default color", () => {
    render(<Badge>Active</Badge>);
    expect(screen.getByText("Active")).toBeInTheDocument();
  });
  it("applies color class", () => {
    const { container } = render(<Badge color="red">High</Badge>);
    expect(container.querySelector(".text-red-700")).toBeInTheDocument();
  });
});
