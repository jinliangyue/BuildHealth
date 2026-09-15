/**
 * Buildings API Service
 */
import apiClient from "./client";
import type {
  Building,
  Sensor,
  HealthAssessment,
  RiskClassification,
} from "../types/api";

export interface BuildingOverview {
  building: Building;
  health: HealthAssessment | null;
  risk: RiskClassification | null;
  active_alert_count: number;
}

export interface BuildingsOverviewResponse {
  total: number;
  items: BuildingOverview[];
}

export const buildingsApi = {
  list: async (): Promise<Building[]> => {
    const r = await apiClient.get<Building[]>("/buildings/");
    return r.data;
  },
  get: async (id: number): Promise<Building> => {
    const r = await apiClient.get<Building>(`/buildings/${id}`);
    return r.data;
  },
  sensors: async (id: number): Promise<Sensor[]> => {
    const r = await apiClient.get<Sensor[]>(`/buildings/${id}/sensors`);
    return r.data;
  },
  overview: async (): Promise<BuildingsOverviewResponse> => {
    const r = await apiClient.get<BuildingsOverviewResponse>("/buildings/overview");
    return r.data;
  },
};
