/**
 * Risk API Service
 */
import apiClient from "./client";
import type { RiskAlert, RiskClassification } from "../types/api";

export const riskApi = {
  classify: async (buildingId: number): Promise<RiskClassification> => {
    const r = await apiClient.get<RiskClassification>(`/buildings/${buildingId}/risk`);
    return r.data;
  },
  alerts: async (
    buildingId: number,
    activeOnly = true,
  ): Promise<RiskAlert[]> => {
    const r = await apiClient.get<RiskAlert[]>(`/buildings/${buildingId}/alerts`, {
      params: { active_only: activeOnly },
    });
    return r.data;
  },
};
