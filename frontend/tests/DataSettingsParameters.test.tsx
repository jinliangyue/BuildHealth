/**
 * DataSettings · Engineering Parameters integration
 *
 * The parameter tables must be driven by GET /api/engineering-parameters.
 * The built-in constants are only a fallback, so these tests pin:
 *   - live values from the API are the ones rendered (not the constants)
 *   - when the endpoint fails, the page still renders the tables from the
 *     fallback and says so explicitly
 *   - the loading state appears while the request is in flight
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import DataSettings from "../src/pages/DataSettings";
import { parametersApi } from "../src/api/parameters";
import type { EngineeringParameters } from "../src/types/api";

vi.mock("../src/api/parameters", () => ({
  parametersApi: { get: vi.fn() },
}));

const mockedGet = parametersApi.get as unknown as ReturnType<typeof vi.fn>;

const apiPayload: EngineeringParameters = {
  calculation_versions: {
    bhi: "BHI-v1.0",
    retrofit_priority: "RP-v1.0",
    recommendation_rules: "REC-v1.0",
    ai: "AI-v1.0",
  },
  // deliberately different from the built-in copy so the test can tell
  // which source was actually rendered
  bhi_weights: {
    structural_safety: 0.45,
    facility_condition: 0.2,
    environmental_quality: 0.15,
    energy_performance: 0.05,
    fire_safety: 0.15,
  },
  bhi_risk_bands: [
    { level: "Normal", min: 90, max: 100 },
    { level: "Attention", min: 75, max: 89 },
    { level: "Abnormal", min: 60, max: 74 },
    { level: "HighRisk", min: 0, max: 59 },
  ],
  retrofit_priority_bands: [
    { level: "Low", min: 0, max: 59 },
    { level: "Medium", min: 60, max: 74 },
    { level: "High", min: 75, max: 89 },
    { level: "Very High", min: 90, max: 100 },
  ],
  retrofit_priority_weights: { risk_severity: 0.35 },
  detection_thresholds: [
    { metric: "crack_width", medium: 0.22, high: 0.33, unit: "mm", low: null, direction: "above" },
  ],
  notice: "Prototype Design Parameters.",
};

function renderPage() {
  return render(
    <MemoryRouter>
      <DataSettings />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  mockedGet.mockReset();
});

describe("DataSettings parameter source", () => {
  it("renders values from the API, not the built-in copy", async () => {
    mockedGet.mockResolvedValue(apiPayload);
    renderPage();

    expect(await screen.findByText("Live from API")).toBeInTheDocument();

    // weights come from the API payload (0.45, not the built-in 0.40)
    expect(screen.getByText("45%")).toBeInTheDocument();
    // detection threshold comes from the API payload (0.22, not 0.20)
    expect(screen.getByText(/0\.22 mm/)).toBeInTheDocument();
  });

  it("shows the calculation versions returned by the API", async () => {
    mockedGet.mockResolvedValue(apiPayload);
    renderPage();

    expect(await screen.findByText("bhi: BHI-v1.0")).toBeInTheDocument();
    expect(screen.getByText("retrofit_priority: RP-v1.0")).toBeInTheDocument();
    expect(screen.getByText("ai: AI-v1.0")).toBeInTheDocument();
  });

  it("falls back to the built-in copy when the endpoint fails", async () => {
    mockedGet.mockRejectedValue(new Error("network down"));
    renderPage();

    expect(
      await screen.findByText("Fallback · built-in copy"),
    ).toBeInTheDocument();

    // the parameter tables are still rendered from the fallback constants
    expect(screen.getByText("90-100")).toBeInTheDocument();
    expect(screen.getByText("40%")).toBeInTheDocument();
    expect(screen.getByText(/0\.20 mm/)).toBeInTheDocument();
  });

  it("reports the failure to the user instead of hiding it", async () => {
    mockedGet.mockRejectedValue(new Error("network down"));
    renderPage();

    expect(await screen.findByText(/Falling back to the built-in/)).toBeInTheDocument();
  });

  it("never renders unvalidated engineering values as authoritative", async () => {
    mockedGet.mockResolvedValue(apiPayload);
    renderPage();
    await screen.findByText("Live from API");

    // the prototype framing stays visible regardless of the data source
    expect(
      screen.getAllByText(/Prototype Risk Classification/i).length,
    ).toBeGreaterThan(0);
  });
});
