/**
 * Buildings API Service
 */
import apiClient from "./client";
import type {
  Building,
  Sensor,
  HealthAssessment,
  RiskClassification,
  RiskBoardResponse,
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
  /** 性能轮 R2: RiskHealth 页面专用, 1 次拿回 blocks + 全楼 active alerts.
   * 后端实现: GET /api/buildings/risk-board (固定 6 条 SQL, 与 N 无关). */
  riskBoard: async (): Promise<RiskBoardResponse> => {
    const r = await apiClient.get<RiskBoardResponse>("/buildings/risk-board");
    return r.data;
  },
};
