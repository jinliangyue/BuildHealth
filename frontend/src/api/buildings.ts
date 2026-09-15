/**
 * Buildings API Service
 */
import apiClient from "./client";
import type { Building, Sensor } from "../types/api";

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
};
