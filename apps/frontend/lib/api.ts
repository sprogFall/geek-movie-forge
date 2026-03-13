const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Request failed: ${res.status}`);
  }
  return res.json();
}

/* ── Providers ── */

import type {
  ProviderResponse,
  ProviderListResponse,
  AssetListResponse,
  AssetResponse,
  MediaGenerationResponse,
  TextGenerationResponse,
} from "@/types/api";

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
