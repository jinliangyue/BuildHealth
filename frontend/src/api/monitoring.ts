/**
 * Monitoring API Service
 */
import apiClient from "./client";
import type { MonitoringRecord } from "../types/api";

export interface MonitoringQuery {
  building_id?: number;
  sensor_id?: number;
  start?: string; // ISO datetime
  end?: string;
  limit?: number;
}

export const monitoringApi = {
  query: async (q: MonitoringQuery = {}): Promise<MonitoringRecord[]> => {
    const r = await apiClient.get<MonitoringRecord[]>("/monitoring/", { params: q });
    return r.data;
  },
};
