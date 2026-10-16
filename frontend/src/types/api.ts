/**
 * TypeScript 类型 · 与后端 Pydantic schemas 严格对齐
 * 任何字段名/类型不一致都会在编译期或渲染期暴露。
 */

// ===== Enums =====
export type RiskLevel = "Normal" | "Attention" | "Abnormal" | "HighRisk";
export type Severity = "low" | "medium" | "high";
export type DetectionMethod = "threshold" | "rate_of_change" | "zscore";
export type Metric =
  | "crack_width"
  | "tilt"
  | "temperature"
  | "humidity"
  | "electricity";

// ===== Entity Types =====
export interface Building {
  id: number;
  name: string;
  address: string;
  year_built: number;
  building_type: string;
  structure_type: string;
  floors: number;
  area: number;
  design_life: number;
  current_age: number;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface Sensor {
  id: number;
  building_id: number;
  component_id: number | null;
  sensor_type: Metric;
  name: string;
  unit: string;
  location: string;
  status: string;
}

export interface MonitoringRecord {
  id: number;
  sensor_id: number;
  timestamp: string;
  value: number;
  quality_flag: string;
}

export interface HealthAssessment {
  id: number;
  building_id: number;
  score: number;
  structural_safety: number;
  facility_condition: number;
  environmental_quality: number;
  energy_performance: number;
  fire_safety: number;
  calculation_version: string;
  explanation: string;
  created_at: string;
}

export interface RiskAlert {
  id: number;
  building_id: number;
  sensor_id: number | null;
  metric: string;
  timestamp: string;
  current_value: number;
  baseline_value: number | null;
  change: number | null;
  detection_method: DetectionMethod;
  severity: Severity;
  explanation: string;
  status: string;
  created_at: string;
}

export interface RiskClassification {
  building_id: number;
  risk_level: RiskLevel;
  bhi: number;
  explanation: string;
  n_high: number;
  n_medium: number;
  n_low: number;
  /** Prototype Risk Classification version (e.g. "RISK-v1.0"). */
  calculation_version?: string;
}

export interface RiskDistribution {
  Normal: number;
  Attention: number;
  Abnormal: number;
  HighRisk: number;
}

export interface BuildingRankingItem {
  building_id: number;
  name: string;
  bhi: number;
  risk_level: RiskLevel;
}

export interface DashboardSummary {
  total_buildings: number;
  monitoring_points: number;
  active_alerts: number;
  average_health_score: number;
  risk_distribution: RiskDistribution;
  building_ranking: BuildingRankingItem[];
  recent_alerts: RiskAlert[];
}

// ===== Risk Board (RiskHealth 页面 91→1 单请求聚合) =====
/** 与 backend/app/schemas/api.py::RiskAlertWithBuildingRead 一致 */
export interface RiskAlertWithBuilding extends RiskAlert {
  building_name: string;
}

/** 与 backend BuildingOverviewItem 一致 */
export interface RiskBoardItem {
  building: Building;
  health: HealthAssessment | null;
  risk: RiskClassification | null;
  active_alert_count: number;
}

/** 与 backend RiskBoardResponse 一致 */
export interface RiskBoardResponse {
  total: number;
  items: RiskBoardItem[];
  alerts: RiskAlertWithBuilding[];
}

// ===== Display Helpers =====
export interface DimensionInfo {
  key: keyof Pick<
    HealthAssessment,
    | "structural_safety"
    | "facility_condition"
    | "environmental_quality"
    | "energy_performance"
    | "fire_safety"
  >;
  label: string;
  weight: number;
  score: number;
}

export const BHI_WEIGHTS: Record<DimensionInfo["key"], number> = {
  structural_safety: 0.40,
  facility_condition: 0.20,
  environmental_quality: 0.15,
  energy_performance: 0.10,
  fire_safety: 0.15,
};

export const DIMENSION_LABELS: Record<DimensionInfo["key"], string> = {
  structural_safety: "Structural Safety",
  facility_condition: "Facility Condition",
  environmental_quality: "Environmental Quality",
  energy_performance: "Energy Performance",
  fire_safety: "Fire Safety",
};

export const RISK_LEVEL_COLORS: Record<RiskLevel, string> = {
  Normal: "#10B981",
  Attention: "#F59E0B",
  Abnormal: "#F97316",
  HighRisk: "#EF4444",
};

export const RISK_LEVEL_LABELS: Record<RiskLevel, string> = {
  Normal: "Normal",
  Attention: "Attention",
  Abnormal: "Abnormal",
  HighRisk: "High Risk",
};

export const SEVERITY_COLORS: Record<Severity, string> = {
  low: "#94A3B8",
  medium: "#F59E0B",
  high: "#EF4444",
};

/**
 * Prototype Engineering Parameters · display mirror
 * =================================================
 * Single source of truth is the backend:
 *   backend/app/analytics/config.py   - BHI weights, anomaly detection thresholds
 *   backend/app/analytics/risk.py     - BHI risk-tier boundaries
 *   backend/app/analytics/priority.py - RP-v1.0 priority boundaries
 *
 * These constants exist for LABELS and colour thresholds only. A risk level or
 * a priority level is always computed by the backend and returned by the API;
 * the UI must never re-derive one from a raw score.
 *
 * If a backend threshold changes, update it here and in the backend together.
 * These are Prototype Design Parameters, not national or industry standards.
 */

/** BHI-v1.0 risk-tier boundaries. Mirrors risk.py (>=90 Normal, >=75 Attention, >=60 Abnormal). */
export const BHI_RISK_BANDS: Record<RiskLevel, { min: number; max: number }> = {
  Normal: { min: 90, max: 100 },
  Attention: { min: 75, max: 89 },
  Abnormal: { min: 60, max: 74 },
  HighRisk: { min: 0, max: 59 },
};

/** Inclusive display range for a risk tier, e.g. "90-100". */
export function bhiRiskBandLabel(level: RiskLevel): string {
  const b = BHI_RISK_BANDS[level];
  return `${b.min}-${b.max}`;
}

/**
 * RP-v1.0 priority boundary for the High tier. Mirrors priority.py
 * PRIORITY_LEVEL_THRESHOLDS and retrofit_service high_priority_count (>= 75.0).
 */
export const RETROFIT_PRIORITY_HIGH_MIN = 75;

/** Prototype anomaly detection thresholds. Mirrors config.py THRESHOLD_RULES. */
export interface DetectionThreshold {
  metric: string;
  medium: number | null;
  high: number | null;
  unit: string;
  /** Decimal places used when rendering this metric's thresholds. */
  decimals: number;
}

export const DETECTION_THRESHOLDS: DetectionThreshold[] = [
  { metric: "crack_width", medium: 0.2, high: 0.3, unit: "mm", decimals: 2 },
  { metric: "tilt", medium: 3.0, high: 4.0, unit: "‰", decimals: 1 },
  { metric: "temperature", medium: 40.0, high: null, unit: "℃", decimals: 0 },
  { metric: "humidity", medium: 85.0, high: null, unit: "%", decimals: 0 },
];

/** Render one threshold value, or an em dash when the tier is not configured. */
export function formatThreshold(
  value: number | null,
  unit: string,
  decimals: number,
): string {
  if (value === null) return "—";
  return `${value.toFixed(decimals)} ${unit}`;
}

/**
 * Engineering Parameters API (read-only)
 * ======================================
 * Served by GET /api/engineering-parameters from backend/app/analytics/config.py.
 * This is the NORMAL data source for the parameter tables. The constants above
 * are a pure-UI fallback for the case where the endpoint is unreachable; they
 * are not meant to be the source of truth and are guarded by
 * backend/tests/test_frontend_parameter_consistency.py.
 *
 * The frontend renders these values and never recomputes engineering results
 * from them — risk level and priority level always come from the API.
 */
export interface EngineeringParameterBand {
  level: string;
  min: number;
  max: number;
}

export interface EngineeringDetectionThreshold {
  metric: string;
  medium: number | null;
  high: number | null;
  low: number | null;
  unit: string;
  direction: string;
}

export interface EngineeringParameters {
  calculation_versions: Record<string, string>;
  bhi_weights: Record<string, number>;
  bhi_risk_bands: EngineeringParameterBand[];
  retrofit_priority_bands: EngineeringParameterBand[];
  retrofit_priority_weights: Record<string, number>;
  detection_thresholds: EngineeringDetectionThreshold[];
  notice: string;
}

/**
 * Presentation-only: decimal places per metric when rendering thresholds.
 * This is formatting, not engineering data, so it stays on the frontend.
 */
export const THRESHOLD_DISPLAY_DECIMALS: Record<string, number> = {
  crack_width: 2,
  tilt: 1,
  temperature: 0,
  humidity: 0,
  electricity: 0,
};

export const METRIC_LABELS: Record<Metric, string> = {
  crack_width: "Crack Width",
  tilt: "Tilt",
  temperature: "Temperature",
  humidity: "Humidity",
  electricity: "Electricity",
};

// ===== Retrofit Decision (V2) =====
export type RetrofitCategory =
  | "Structural"
  | "Envelope"
  | "MEP"
  | "Environment"
  | "Energy"
  | "FireSafety";

export type RetrofitUrgency = "low" | "medium" | "high" | "critical";
export type RetrofitCostLevel = "low" | "medium" | "high";
export type RetrofitBenefitLevel = "low" | "medium" | "high";
export type RetrofitPriorityLevel = "Low" | "Medium" | "High" | "VeryHigh";

export interface RetrofitEvidenceSensor {
  sensor_id: number;
  metric: Metric;
  name: string;
  unit: string;
  location: string;
  recent_values: Array<{ timestamp: string; value: number }>;
  anomaly_count_by_severity: { high: number; medium: number; low: number };
}

export interface RetrofitEvidence {
  sensors: RetrofitEvidenceSensor[];
  anomalies: Array<{
    sensor_id: number | null;
    metric: string;
    timestamp: string;
    current_value: number;
    detection_method: DetectionMethod;
    severity: Severity;
    explanation: string;
  }>;
  bhi_context: { score: number; weakest_dimension: string } | null;
  risk_context: { risk_level: RiskLevel; explanation: string } | null;
  anomaly_summary: { total: number; high: number; medium: number } | null;
}

export interface PriorityScoreBreakdown {
  risk_severity: number;
  risk_severity_contribution: number;
  trend: number;
  trend_contribution: number;
  component_importance: number;
  component_importance_contribution: number;
  urgency: number;
  urgency_contribution: number;
  cost_efficiency: number;
  cost_efficiency_contribution: number;
  total: number;
  calculation_version: string;
}

export interface RetrofitRecommendation {
  id: number;
  building_id: number;
  component_id: number | null;
  category: RetrofitCategory;
  issue_type: string;
  title: string;
  recommendation: string;
  rationale: string;
  next_action: string;
  urgency: RetrofitUrgency;
  estimated_cost_level: RetrofitCostLevel;
  expected_benefit: RetrofitBenefitLevel;
  source: string;
  calculation_version: string;
  created_at: string;
  evidence: RetrofitEvidence;
  priority_score: number;
  priority_breakdown: PriorityScoreBreakdown;
}

export interface EngineeringNote {
  id: number;
  building_id: number;
  component_id: number | null;
  text: string;
  source: string;
  created_at: string;
}

export interface RetrofitDecision {
  building_id: number;
  building: Building;
  overall_priority: number;
  overall_priority_level: RetrofitPriorityLevel;
  calculation_version: string;
  recommendations: RetrofitRecommendation[];
  engineering_notes: EngineeringNote[];
  disclaimer: string;
}

export interface RetrofitOverviewItem {
  building: Building;
  overall_priority: number;
  overall_priority_level: RetrofitPriorityLevel;
  recommendation_count: number;
  high_priority_count: number;
  top_category: string;
}

export interface RetrofitOverviewResponse {
  total: number;
  items: RetrofitOverviewItem[];
  average_priority: number;
  calculation_version: string;
  disclaimer: string;
}

// ===== Retrofit Display Helpers =====
export const PRIORITY_LEVEL_COLORS: Record<RetrofitPriorityLevel, string> = {
  Low: "#94A3B8",
  Medium: "#F59E0B",
  High: "#F97316",
  VeryHigh: "#EF4444",
};

export const PRIORITY_LEVEL_LABELS: Record<RetrofitPriorityLevel, string> = {
  Low: "Low",
  Medium: "Medium",
  High: "High",
  VeryHigh: "Very High",
};

export const URGENCY_COLORS: Record<RetrofitUrgency, string> = {
  low: "#94A3B8",
  medium: "#F59E0B",
  high: "#F97316",
  critical: "#EF4444",
};

export const CATEGORY_LABELS: Record<RetrofitCategory, string> = {
  Structural: "Structural",
  Envelope: "Envelope",
  MEP: "MEP",
  Environment: "Environment",
  Energy: "Energy",
  FireSafety: "Fire Safety",
};

export const ISSUE_TYPE_LABELS: Record<string, string> = {
  crack_growth: "Crack Growth",
  tilt_trend: "Tilt Trend",
  moisture_control: "Moisture Control",
  energy_efficiency: "Energy Efficiency",
  comprehensive_assessment: "Comprehensive Assessment",
};

export const COST_LEVEL_COLORS: Record<RetrofitCostLevel, string> = {
  low: "#10B981",
  medium: "#F59E0B",
  high: "#EF4444",
};

// ===== AI Engineering Assistant (V3) =====
export type AIProviderType = "mock" | "openai" | "openai-compatible" | "anthropic" | "other";
export type AISeverity = "info" | "low" | "medium" | "high";
export type AIUrgency = "low" | "medium" | "high";
export type AIEvidenceSourceType =
  | "sensor"
  | "anomaly"
  | "health"
  | "risk"
  | "retrofit_recommendation"
  | "engineering_note"
  | "building";

export interface AIEvidenceRef {
  source_type: AIEvidenceSourceType;
  source_id: number | null;
  metric: string | null;
  description: string;
  reference_path: string | null;
}

export interface AIKeyFinding {
  title: string;
  description: string;
  severity: AISeverity;
}

export interface AIRecommendedAction {
  action: string;
  reason: string;
  urgency: AIUrgency;
}

/**
 * KnowledgeEvidence (Phase 6B · RAG)
 *
 * 来自 project-internal knowledge/ 的通用工程知识文档片段。
 * 明确区别于 AIEvidenceRef (engineering data evidence):
 * 知识片段是背景解释, 不是本建筑的实测证据.
 */
export interface KnowledgeEvidence {
  document: string;
  section: string;
  content: string;
  relevance_score: number;
  source: string;
  chunk_id: string;
}

export interface AIResponse {
  answer: string;
  key_findings: AIKeyFinding[];
  evidence: AIEvidenceRef[];
  /** Phase 6B RAG · general engineering knowledge, distinct from `evidence`. */
  knowledge_evidence: KnowledgeEvidence[];
  recommended_actions: AIRecommendedAction[];
  disclaimer: string;
  provider: AIProviderType;
  model: string;
  calculation_version: string;
  created_at: string;
}

export interface AIHealthStatus {
  status: "ok" | "provider_not_configured" | "provider_error";
  provider: AIProviderType;
  model: string;
  message: string;
}

export const AI_SEVERITY_COLORS: Record<AISeverity, string> = {
  info: "#3B82F6",
  low: "#94A3B8",
  medium: "#F59E0B",
  high: "#EF4444",
};

export const AI_URGENCY_COLORS: Record<AIUrgency, string> = {
  low: "#10B981",
  medium: "#F59E0B",
  high: "#EF4444",
};
