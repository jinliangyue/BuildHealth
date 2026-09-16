/**
 * Engineering Parameters · display mirror tests
 *
 * These constants are a display mirror of the backend analytics config.
 * The tests below lock the invariants that matter for display correctness:
 * bands must tile [0, 100] with no gap or overlap, and the formatters must
 * render exactly what the parameter tables previously hardcoded.
 */
import { describe, it, expect } from "vitest";
import {
  BHI_RISK_BANDS,
  DETECTION_THRESHOLDS,
  RETROFIT_PRIORITY_HIGH_MIN,
  RISK_LEVEL_COLORS,
  bhiRiskBandLabel,
  formatThreshold,
  type RiskLevel,
} from "../src/types/api";

const RISK_LEVELS: RiskLevel[] = [
  "Normal",
  "Attention",
  "Abnormal",
  "HighRisk",
];

describe("BHI risk bands", () => {
  it("covers every risk level", () => {
    for (const level of RISK_LEVELS) {
      expect(BHI_RISK_BANDS[level]).toBeDefined();
    }
  });

  it("tiles 0-100 with no gap and no overlap", () => {
    const sorted = [...RISK_LEVELS].sort(
      (a, b) => BHI_RISK_BANDS[a].min - BHI_RISK_BANDS[b].min,
    );
    expect(BHI_RISK_BANDS[sorted[0]].min).toBe(0);
    expect(BHI_RISK_BANDS[sorted[sorted.length - 1]].max).toBe(100);
    for (let i = 1; i < sorted.length; i += 1) {
      // next band starts exactly one above the previous band's max
      expect(BHI_RISK_BANDS[sorted[i]].min).toBe(
        BHI_RISK_BANDS[sorted[i - 1]].max + 1,
      );
    }
  });

  it("matches the prototype BHI-v1.0 boundaries", () => {
    expect(BHI_RISK_BANDS.Normal.min).toBe(90);
    expect(BHI_RISK_BANDS.Attention.min).toBe(75);
    expect(BHI_RISK_BANDS.Abnormal.min).toBe(60);
    expect(BHI_RISK_BANDS.HighRisk.min).toBe(0);
  });

  it("labels bands the way the parameter table renders them", () => {
    expect(bhiRiskBandLabel("Normal")).toBe("90-100");
    expect(bhiRiskBandLabel("Attention")).toBe("75-89");
    expect(bhiRiskBandLabel("Abnormal")).toBe("60-74");
    expect(bhiRiskBandLabel("HighRisk")).toBe("0-59");
  });

  it("uses the same colour for a level on every page", () => {
    expect(RISK_LEVEL_COLORS.HighRisk).toBe("#EF4444");
  });
});

describe("detection thresholds", () => {
  it("lists the four threshold-detected metrics", () => {
    expect(DETECTION_THRESHOLDS.map((t) => t.metric)).toEqual([
      "crack_width",
      "tilt",
      "temperature",
      "humidity",
    ]);
  });

  it("matches the prototype detection parameters", () => {
    const byMetric = Object.fromEntries(
      DETECTION_THRESHOLDS.map((t) => [t.metric, t]),
    );
    expect(byMetric.crack_width.medium).toBe(0.2);
    expect(byMetric.crack_width.high).toBe(0.3);
    expect(byMetric.tilt.medium).toBe(3.0);
    expect(byMetric.tilt.high).toBe(4.0);
    expect(byMetric.temperature.medium).toBe(40.0);
    expect(byMetric.temperature.high).toBeNull();
    expect(byMetric.humidity.medium).toBe(85.0);
    expect(byMetric.humidity.high).toBeNull();
  });

  it("renders thresholds exactly as the parameter table previously did", () => {
    const byMetric = Object.fromEntries(
      DETECTION_THRESHOLDS.map((t) => [t.metric, t]),
    );
    expect(
      formatThreshold(
        byMetric.crack_width.medium,
        byMetric.crack_width.unit,
        byMetric.crack_width.decimals,
      ),
    ).toBe("0.20 mm");
    expect(
      formatThreshold(
        byMetric.tilt.high,
        byMetric.tilt.unit,
        byMetric.tilt.decimals,
      ),
    ).toBe("4.0 ‰");
    expect(
      formatThreshold(
        byMetric.temperature.medium,
        byMetric.temperature.unit,
        byMetric.temperature.decimals,
      ),
    ).toBe("40 ℃");
  });

  it("renders an em dash for an unconfigured tier", () => {
    expect(formatThreshold(null, "mm", 2)).toBe("—");
  });
});

describe("retrofit priority", () => {
  it("uses the High-tier boundary the backend counts against", () => {
    expect(RETROFIT_PRIORITY_HIGH_MIN).toBe(75);
  });
});
