/**
 * AI Engineering Assistant API Service · Phase 5 V3
 */
import apiClient from "./client";
import type { AIHealthStatus, AIResponse } from "../types/api";

export const aiApi = {
  health: async (): Promise<AIHealthStatus> => {
    const r = await apiClient.get<AIHealthStatus>("/ai/health");
    return r.data;
  },
  summarize: async (buildingId: number): Promise<AIResponse> => {
    const r = await apiClient.post<AIResponse>(
      `/ai/buildings/${buildingId}/summary`,
    );
    return r.data;
  },
  ask: async (buildingId: number, question: string): Promise<AIResponse> => {
    const r = await apiClient.post<AIResponse>(
      `/ai/buildings/${buildingId}/ask`,
      { question },
    );
    return r.data;
  },
};
