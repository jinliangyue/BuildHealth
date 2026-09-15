/**
 * Dashboard API Service
 */
import apiClient from "./client";
import type { DashboardSummary } from "../types/api";

export const dashboardApi = {
  summary: async (): Promise<DashboardSummary> => {
    const r = await apiClient.get<DashboardSummary>("/dashboard/summary");
    return r.data;
  },
};
