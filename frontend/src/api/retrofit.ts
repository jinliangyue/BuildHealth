/**
 * Retrofit Decision API Service · Phase 4 V2
 */
import apiClient from "./client";
import type {
  RetrofitDecision,
  RetrofitRecommendation,
  RetrofitOverviewResponse,
} from "../types/api";

export const retrofitApi = {
  decision: async (buildingId: number): Promise<RetrofitDecision> => {
    const r = await apiClient.get<RetrofitDecision>(
      `/buildings/${buildingId}/retrofit`,
    );
    return r.data;
  },
  recommendation: async (
    buildingId: number,
    recId: number,
  ): Promise<RetrofitRecommendation> => {
    const r = await apiClient.get<RetrofitRecommendation>(
      `/buildings/${buildingId}/retrofit/${recId}`,
    );
    return r.data;
  },
  overview: async (): Promise<RetrofitOverviewResponse> => {
    const r = await apiClient.get<RetrofitOverviewResponse>(
      "/retrofit/overview",
    );
    return r.data;
  },
};
