/**
 * RiskLevel / Severity 常量映射测试
 * 确保所有等级颜色 / label 与后端 4 档一致
 */
import { describe, it, expect } from "vitest";
import {
  RISK_LEVEL_COLORS,
  RISK_LEVEL_LABELS,
  SEVERITY_COLORS,
  BHI_WEIGHTS,
  type RiskLevel,
  type Severity,
} from "../src/types/api";

describe("RiskLevel mapping", () => {
  const LEVELS: RiskLevel[] = ["Normal", "Attention", "Abnormal", "HighRisk"];

  it("has color for every level", () => {
    LEVELS.forEach((l) => {
      expect(RISK_LEVEL_COLORS[l]).toMatch(/^#[0-9A-Fa-f]{6}$/);
    });
  });

  it("has label for every level", () => {
    LEVELS.forEach((l) => {
      expect(RISK_LEVEL_LABELS[l]).toBeTruthy();
    });
  });

  it("Normal=green, HighRisk=red", () => {
    expect(RISK_LEVEL_COLORS.Normal).toBe("#10B981");
    expect(RISK_LEVEL_COLORS.HighRisk).toBe("#EF4444");
  });

  it("all 4 labels are distinct", () => {
    const labels = LEVELS.map((l) => RISK_LEVEL_LABELS[l]);
    expect(new Set(labels).size).toBe(4);
  });
});

describe("Severity mapping", () => {
  const SEVS: Severity[] = ["low", "medium", "high"];
  it("has color for every severity", () => {
    SEVS.forEach((s) => {
      expect(SEVERITY_COLORS[s]).toMatch(/^#[0-9A-Fa-f]{6}$/);
    });
  });
});

describe("BHI weights", () => {
  it("sums to 1.0", () => {
    const sum = Object.values(BHI_WEIGHTS).reduce((a, b) => a + b, 0);
    expect(Math.abs(sum - 1.0)).toBeLessThan(1e-6);
  });
  it("structural_safety is the highest weight", () => {
    expect(BHI_WEIGHTS.structural_safety).toBe(0.4);
    const others = Object.entries(BHI_WEIGHTS).filter(
      ([k]) => k !== "structural_safety",
    );
    others.forEach(([_, w]) => {
      expect(BHI_WEIGHTS.structural_safety).toBeGreaterThan(w);
    });
  });
});
