/**
 * Axios HTTP Client · Phase 2
 * - 统一 baseURL（Vite proxy /api → backend）
 * - 错误拦截 + 友好错误抛出
 */
import axios, { AxiosError } from "axios";

export class APIError extends Error {
  status: number;
  detail: string;
  constructor(status: number, detail: string) {
    super(`API Error ${status}: ${detail}`);
    this.name = "APIError";
    this.status = status;
    this.detail = detail;
  }
}

const apiClient = axios.create({
  baseURL: "/api",
  timeout: 15000,
  headers: { "Content-Type": "application/json" },
});

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<{ detail?: string }>) => {
    if (error.response) {
      const detail = error.response.data?.detail || error.message;
      throw new APIError(error.response.status, detail);
    }
    if (error.request) {
      throw new APIError(0, "Network error: backend not reachable");
    }
    throw new APIError(-1, error.message);
  },
);

export default apiClient;
