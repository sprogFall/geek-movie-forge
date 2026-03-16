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

const DEFAULT_TIMEOUT = 10_000; // 普通请求 10 秒
const LONG_TIMEOUT = 300_000; // 生成类请求 5 分钟

type RequestOptions = RequestInit & { timeout?: number };

async function request<T>(path: string, init?: RequestOptions): Promise<T> {
  const { timeout = DEFAULT_TIMEOUT, ...fetchInit } = init ?? {};
  const token = getStoredToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(fetchInit.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...fetchInit,
      headers,
      signal: fetchInit.signal ?? controller.signal,
    });
  } catch (err) {
    clearTimeout(timeoutId);
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new Error("请求超时，请检查后端服务是否正常运行");
    }
    throw new Error("无法连接到后端服务");
  } finally {
    clearTimeout(timeoutId);
  }

  if (res.status === 401) {
    // 登录/注册接口的 401 表示凭证错误，不应触发"过期"逻辑
    const isAuthEndpoint =
      path.startsWith("/api/v1/auth/login") || path.startsWith("/api/v1/auth/register");
    if (!isAuthEndpoint) {
      clearAuth();
      onUnauthorized?.();
      throw new Error("登录已过期，请重新登录");
    }
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

export function createAsset(body: Record<string, unknown>, params?: Record<string, string>) {
  const qs = params ? "?" + new URLSearchParams(params).toString() : "";
  return request<AssetResponse>(`/api/v1/assets${qs}`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function updateAsset(id: string, body: Record<string, unknown>) {
  return request<AssetResponse>(`/api/v1/assets/${id}`, {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

export function deleteAsset(id: string) {
  return request<void>(`/api/v1/assets/${id}`, { method: "DELETE" });
}

/* ── Generations ── */

export function generateImages(body: Record<string, unknown>) {
  return request<MediaGenerationResponse>("/api/v1/generations/images", {
    method: "POST",
    body: JSON.stringify(body),
    timeout: LONG_TIMEOUT,
  });
}

export function generateVideos(body: Record<string, unknown>) {
  return request<MediaGenerationResponse>("/api/v1/generations/videos", {
    method: "POST",
    body: JSON.stringify(body),
    timeout: LONG_TIMEOUT,
  });
}

export function generateTexts(body: Record<string, unknown>) {
  return request<TextGenerationResponse>("/api/v1/generations/texts", {
    method: "POST",
    body: JSON.stringify(body),
    timeout: LONG_TIMEOUT,
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
