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

export const METRIC_LABELS: Record<Metric, string> = {
  crack_width: "Crack Width",
  tilt: "Tilt",
  temperature: "Temperature",
  humidity: "Humidity",
  electricity: "Electricity",
};
