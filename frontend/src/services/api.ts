import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";

// API base URL resolution order:
//  1. window.__API_URL__  — injected at deploy time via /config.js (so the same
//     build artifact works against any deployed API without rebuilding).
//  2. REACT_APP_API_URL   — build-time env (used for local/dev builds).
//  3. http://localhost:8000 — local development fallback.
declare global {
  interface Window {
    __API_URL__?: string;
  }
}

const runtimeApiUrl =
  typeof window !== "undefined" && window.__API_URL__ ? window.__API_URL__ : "";
const RAW_API_BASE_URL = runtimeApiUrl || process.env.REACT_APP_API_URL || "http://localhost:8000";
// Strip any trailing slash so baseURL + "/api/..." composes cleanly.
const API_BASE_URL = RAW_API_BASE_URL.replace(/\/+$/, "");

// In-memory token storage (more secure than localStorage for XSS)
let accessToken: string | null = null;

export const setAccessToken = (token: string | null) => {
  accessToken = token;
};

export const getAccessToken = (): string | null => {
  return accessToken;
};

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Request interceptor — attach JWT token
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    if (accessToken && config.headers) {
      config.headers.Authorization = `Bearer ${accessToken}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor — handle errors (no 401 auto-redirect)
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    return Promise.reject(error);
  }
);

export default api;
