/**
 * Health API Service
 */
import apiClient from "./client";
import type { HealthAssessment } from "../types/api";

export const healthApi = {
  get: async (buildingId: number): Promise<HealthAssessment> => {
    const r = await apiClient.get<HealthAssessment>(`/buildings/${buildingId}/health`);
    return r.data;
  },
  recompute: async (buildingId: number): Promise<HealthAssessment> => {
    const r = await apiClient.post<HealthAssessment>(
      `/buildings/${buildingId}/health/recompute`,
    );
    return r.data;
  },
};
