/**
 * Engineering Parameters API Service
 * Read-only prototype parameters served from backend/app/analytics/config.py.
 */
import apiClient from "./client";
import type { EngineeringParameters } from "../types/api";

export const parametersApi = {
  get: async (): Promise<EngineeringParameters> => {
    const r = await apiClient.get<EngineeringParameters>(
      "/engineering-parameters",
    );
    return r.data;
  },
};
