import type {
  TokenResponse,
  UserResponse,
  ProviderResponse,
  ProviderListResponse,
  AssetListResponse,
  AssetResponse,
  ProjectListResponse,
  ProjectResponse,
  TaskListResponse,
  TaskResponse,
  MediaGenerationResponse,
  TextGenerationResponse,
  CallLogListResponse,
  CallLogResponse,
} from "@/types/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const TOKEN_KEY = "gmf_token";
const USER_KEY = "gmf_user";

/* ── Token persistence ── */

export function getStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function getStoredUser(): UserResponse | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function storeAuth(token: string, user: UserResponse) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearAuth() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

/* ── Core request ── */

let onUnauthorized: (() => void) | null = null;

export function setOnUnauthorized(cb: () => void) {
  onUnauthorized = cb;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getStoredToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init?.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, { ...init, headers });

  if (res.status === 401) {
    clearAuth();
    onUnauthorized?.();
    throw new Error("登录已过期，请重新登录");
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Request failed: ${res.status}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

/* ── Auth ── */

export function register(username: string, password: string) {
  return request<TokenResponse>("/api/v1/auth/register", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export function login(username: string, password: string) {
  return request<TokenResponse>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export function fetchMe() {
  return request<UserResponse>("/api/v1/auth/me");
}

/* ── Providers ── */

export function listProviders() {
  return request<ProviderListResponse>("/api/v1/providers");
}

export function getProvider(id: string) {
  return request<ProviderResponse>(`/api/v1/providers/${id}`);
}

export function createProvider(body: Record<string, unknown>) {
  return request<ProviderResponse>("/api/v1/providers", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function updateProvider(id: string, body: Record<string, unknown>) {
  return request<ProviderResponse>(`/api/v1/providers/${id}`, {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

export function deleteProvider(id: string) {
  return request<void>(`/api/v1/providers/${id}`, { method: "DELETE" });
}

/* ── Assets ── */

export function listAssets(params?: Record<string, string>) {
  const qs = params ? "?" + new URLSearchParams(params).toString() : "";
  return request<AssetListResponse>(`/api/v1/assets${qs}`);
}

export function getAsset(id: string) {
  return request<AssetResponse>(`/api/v1/assets/${id}`);
}

export function createAsset(body: Record<string, unknown>) {
  return request<AssetResponse>("/api/v1/assets", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

/* ── Generations ── */

export function generateImages(body: Record<string, unknown>) {
  return request<MediaGenerationResponse>("/api/v1/generations/images", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function generateVideos(body: Record<string, unknown>) {
  return request<MediaGenerationResponse>("/api/v1/generations/videos", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function generateTexts(body: Record<string, unknown>) {
  return request<TextGenerationResponse>("/api/v1/generations/texts", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

/* 鈹€鈹€ Projects 鈹€鈹€ */

export function listProjects() {
  return request<ProjectListResponse>("/api/v1/projects");
}

export function getProject(id: string) {
  return request<ProjectResponse>(`/api/v1/projects/${id}`);
}

export function createProject(body: Record<string, unknown>) {
  return request<ProjectResponse>("/api/v1/projects", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

/* 鈹€鈹€ Tasks 鈹€鈹€ */

export function listTasks(params?: Record<string, string>) {
  const qs = params ? "?" + new URLSearchParams(params).toString() : "";
  return request<TaskListResponse>(`/api/v1/tasks${qs}`);
}

export function getTask(id: string) {
  return request<TaskResponse>(`/api/v1/tasks/${id}`);
}

export function createTask(body: Record<string, unknown>) {
  return request<TaskResponse>("/api/v1/tasks", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

/* -- Call Logs -- */

export function listCallLogs(params?: Record<string, string>) {
  const qs = params ? "?" + new URLSearchParams(params).toString() : "";
  return request<CallLogListResponse>(`/api/v1/call-logs${qs}`);
}

export function getCallLog(id: string) {
  return request<CallLogResponse>(`/api/v1/call-logs/${id}`);
}
