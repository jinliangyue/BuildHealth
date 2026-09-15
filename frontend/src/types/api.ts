/**
 * 与后端 Pydantic 模型对应的 TypeScript 类型
 * Phase 0 占位 · Phase 1 完善
 */

export type BuildingType = "residential" | "office" | "mixed" | "industrial";

export type Metric =
  | "crack_width"
  | "tilt"
  | "temperature"
  | "humidity"
  | "electricity";

export type RiskLevel = "Normal" | "Attention" | "Abnormal" | "HighRisk";

export type Severity = "low" | "medium" | "high";

export interface Building {
  id: number;
  name: string;
  address: string;
  city: string;
  building_type: BuildingType;
  built_year: number;
  total_floors: number;
  created_at: string;
  updated_at: string;
}

export interface Component {
  id: number;
  building_id: number;
  name: string;
  component_type: string;
  location: string;
  created_at: string;
}

export interface Sensor {
  id: number;
  component_id: number;
  metric: Metric;
  unit: string;
  install_date: string;
  is_active: boolean;
  created_at: string;
}

export interface MonitoringRecord {
  id: number;
  sensor_id: number;
  ts: string;
  value: number;
  is_simulated: boolean;
  created_at: string;
}

export interface HealthAssessment {
  id: number;
  building_id: number;
  assessment_date: string;
  structural_safety: number;
  facility_condition: number;
  environmental_quality: number;
  energy_performance: number;
  fire_safety: number;
  bhi: number;
  bhi_version: string;
  created_at: string;
}

export interface RiskAlert {
  id: number;
  building_id: number;
  alert_date: string;
  risk_level: RiskLevel;
  bhi_at_alert: number;
  top_reason: string;
  is_active: boolean;
  created_at: string;
}

export interface Anomaly {
  sensor_id: number;
  metric: Metric;
  time_range_start: string;
  time_range_end: string;
  current_value: number;
  baseline_value: number;
  delta: number;
  method: "threshold" | "rate_of_change" | "zscore";
  severity: Severity;
  reason: string;
}
