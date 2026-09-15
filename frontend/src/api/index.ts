/**
 * API Barrel Export
 */
export { default as apiClient, APIError } from "./client";
export { buildingsApi } from "./buildings";
export { monitoringApi } from "./monitoring";
export type { MonitoringQuery } from "./monitoring";
export { healthApi } from "./health";
export { riskApi } from "./risk";
export { dashboardApi } from "./dashboard";
