"use client";

import { useEffect, useState } from "react";
import {
  listProviders,
  createProvider,
  updateProvider,
  deleteProvider,
} from "@/lib/api";
import type { ProviderResponse, ModelCapability, ProviderRoutes } from "@/types/api";

type ModelRow = { model: string; capabilities: ModelCapability[]; label: string };

const emptyModel: ModelRow = { model: "", capabilities: [], label: "" };

type RouteKey = "text" | "image" | "video";
type RouteState = { path: string; timeout_seconds: number };
type RoutesState = Record<RouteKey, RouteState>;

const defaultRoutes: RoutesState = {
  text: { path: "/text/generations", timeout_seconds: 60 },
  image: { path: "/image/generations", timeout_seconds: 60 },
  video: { path: "/video/generations", timeout_seconds: 60 },
};

function hasTextCapability(models: ModelRow[]) {
  return models.some((model) => model.capabilities.includes("text"));
}

function looksLikeVersionRootEndpoint(value: string) {
  const trimmed = value.trim().replace(/\/+$/, "");
  if (!trimmed) {
    return false;
  }
  if (trimmed === "/v1" || trimmed === "v1") {
    return true;
  }
  try {
    return new URL(trimmed).pathname.replace(/\/+$/, "") === "/v1";
  } catch {
    return false;
  }
}

function isDefaultRoutes(routes: ProviderRoutes) {
  return (
    routes.text.path === defaultRoutes.text.path &&
    routes.text.timeout_seconds === defaultRoutes.text.timeout_seconds &&
    routes.image.path === defaultRoutes.image.path &&
    routes.image.timeout_seconds === defaultRoutes.image.timeout_seconds &&
    routes.video.path === defaultRoutes.video.path &&
    routes.video.timeout_seconds === defaultRoutes.video.timeout_seconds
  );
}

export function ProviderManager() {
  const [providers, setProviders] = useState<ProviderResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);

  /* editing state — null means "create" mode */
  const [editingProvider, setEditingProvider] = useState<ProviderResponse | null>(null);

  /* form state */
  const [name, setName] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [models, setModels] = useState<ModelRow[]>([{ ...emptyModel }]);
  const [routes, setRoutes] = useState<RoutesState>({ ...defaultRoutes });
  const [showRoutes, setShowRoutes] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const textProviderSelected = hasTextCapability(models);
  const textRouteLooksWrong = textProviderSelected && looksLikeVersionRootEndpoint(routes.text.path);

  async function load() {
    try {
      const data = await listProviders();
      setProviders(data.items);
    } catch {
      setError("加载供应商失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  function resetForm() {
    setName("");
    setBaseUrl("");
    setApiKey("");
    setModels([{ ...emptyModel }]);
    setRoutes({ ...defaultRoutes });
    setShowRoutes(false);
    setEditingProvider(null);
  }

  function startEdit(p: ProviderResponse) {
    setEditingProvider(p);
    setName(p.name);
    setBaseUrl(p.base_url);
    setApiKey("");
    setModels(
      p.models.map((m) => ({
        model: m.model,
        capabilities: [...m.capabilities],
        label: m.label ?? "",
      }))
    );
    setRoutes({
      text: {
        path: p.routes.text.path ?? defaultRoutes.text.path,
        timeout_seconds: p.routes.text.timeout_seconds ?? defaultRoutes.text.timeout_seconds,
      },
      image: {
        path: p.routes.image.path ?? defaultRoutes.image.path,
        timeout_seconds: p.routes.image.timeout_seconds ?? defaultRoutes.image.timeout_seconds,
      },
      video: {
        path: p.routes.video.path ?? defaultRoutes.video.path,
        timeout_seconds: p.routes.video.timeout_seconds ?? defaultRoutes.video.timeout_seconds,
      },
    });
    setShowRoutes(!isDefaultRoutes(p.routes));
    setShowForm(true);
  }

  function cancelForm() {
    setShowForm(false);
    resetForm();
  }

  function toggleCap(idx: number, cap: ModelCapability) {
    setModels((prev) =>
      prev.map((m, i) => {
        if (i !== idx) return m;
        const has = m.capabilities.includes(cap);
        return {
          ...m,
          capabilities: has
            ? m.capabilities.filter((c) => c !== cap)
            : [...m.capabilities, cap],
        };
      })
    );
  }

  function updateModel(idx: number, field: "model" | "label", value: string) {
    setModels((prev) =>
      prev.map((m, i) => (i === idx ? { ...m, [field]: value } : m))
    );
  }

  function addModelRow() {
    setModels((prev) => [...prev, { ...emptyModel }]);
  }

  function removeModelRow(idx: number) {
    setModels((prev) => prev.filter((_, i) => i !== idx));
  }

  function updateRoute(route: RouteKey, field: keyof RouteState, value: string) {
    setRoutes((prev) => {
      const current = prev[route];
      if (field === "timeout_seconds") {
        const parsed = Number(value);
        return {
          ...prev,
          [route]: {
            ...current,
            timeout_seconds:
              Number.isFinite(parsed) && parsed > 0
                ? parsed
                : defaultRoutes[route].timeout_seconds,
          },
        };
      }
      return { ...prev, [route]: { ...current, path: value } };
    });
  }

  async function handleDelete(p: ProviderResponse) {
    if (!confirm(`确定删除供应商「${p.name}」？此操作不可恢复。`)) return;
    setError("");
    try {
      await deleteProvider(p.provider_id);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "删除供应商失败");
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      const cleanModels = models
        .filter((m) => m.model && m.capabilities.length > 0)
        .map((m) => ({
          model: m.model,
          capabilities: m.capabilities,
          label: m.label || null,
        }));

      if (editingProvider) {
        const body: Record<string, unknown> = {
          name,
          base_url: baseUrl,
          models: cleanModels,
          routes,
        };
        if (apiKey) body.api_key = apiKey;
        await updateProvider(editingProvider.provider_id, body);
      } else {
        await createProvider({
          name,
          base_url: baseUrl,
          api_key: apiKey,
          models: cleanModels,
          routes,
        });
      }
      setShowForm(false);
      resetForm();
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "保存供应商失败");
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <div className="gen-empty">
        <span className="spinner spinner-dark" />
        <p>正在加载供应商...</p>
      </div>
    );
  }

  const isEditing = editingProvider !== null;

  return (
    <div className="stack-lg">
      {error && <div className="error-banner">{error}</div>}

      <div className="form-actions">
        <button
          className="btn btn-primary"
          onClick={() => {
            if (showForm) {
              cancelForm();
            } else {
              resetForm();
              setShowForm(true);
            }
          }}
        >
          {showForm ? "取消" : "新增供应商"}
        </button>
      </div>

      {showForm && (
        <form className="panel form-stack" onSubmit={handleSubmit}>
          <div className="form-row">
            <div className="form-group">
              <label className="form-label">名称</label>
              <input
                className="form-input"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="例如：openai-main"
                required
              />
            </div>
            <div className="form-group">
              <label className="form-label">接口地址</label>
              <input
                className="form-input"
                type="url"
                value={baseUrl}
                onChange={(e) => setBaseUrl(e.target.value)}
                placeholder="https://api.example.com"
                required
              />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">
              API Key{isEditing ? "（留空则不更新）" : ""}
            </label>
            <input
              className="form-input"
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="sk-..."
              required={!isEditing}
            />
          </div>

          <div className="form-group">
            <label className="form-label">模型</label>
            <div className="stack-sm">
              {models.map((m, idx) => (
                <div key={idx} className="form-row" style={{ alignItems: "end" }}>
                  <div className="form-group">
                    <input
                      className="form-input"
                      value={m.model}
                      onChange={(e) => updateModel(idx, "model", e.target.value)}
                      placeholder="模型ID"
                    />
                  </div>
                  <div className="form-group">
                    <input
                      className="form-input"
                      value={m.label}
                      onChange={(e) => updateModel(idx, "label", e.target.value)}
                      placeholder="展示名称（可选）"
                    />
                  </div>
                  <div className="model-list">
                    {(["text", "image", "video"] as ModelCapability[]).map((cap) => (
                      <button
                        type="button"
                        key={cap}
                        className={`model-tag${m.capabilities.includes(cap) ? " is-selected" : ""}`}
                        onClick={() => toggleCap(idx, cap)}
                        style={{
                          cursor: "pointer",
                          opacity: m.capabilities.includes(cap) ? 1 : 0.45,
                        }}
                      >
                        <span className={`cap-dot cap-${cap}`} />
                        {{ text: "文本", image: "图片", video: "视频" }[cap] ?? cap}
                      </button>
                    ))}
                  </div>
                  {models.length > 1 && (
                    <button
                      type="button"
                      className="btn btn-sm btn-danger"
                      onClick={() => removeModelRow(idx)}
                    >
                      删除
                    </button>
                  )}
                </div>
              ))}
              <button
                type="button"
                className="btn btn-sm btn-secondary"
                onClick={addModelRow}
              >
                + 添加模型
              </button>
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Routes（高级）</label>
            <div className="form-hint">
              path 支持相对路径（如 /text/generations）或完整 URL（如 https://api.example.com/v1/text/generations）。
            </div>
            {textProviderSelected && (
              <div className="form-hint">
                For OpenAI-compatible text APIs, use <code>https://api.example.com/v1</code> as
                the base URL and <code>/chat/completions</code> as the text path.
              </div>
            )}
            {textRouteLooksWrong && (
              <div className="error-banner">
                Text route looks incomplete. <code>/v1</code> is usually a version prefix, not a
                POST endpoint. If this provider is OpenAI-compatible, set the text path to{" "}
                <code>/chat/completions</code>.
              </div>
            )}
            <div className="form-actions" style={{ paddingTop: 0 }}>
              <button
                type="button"
                className="btn btn-sm btn-secondary"
                onClick={() => setShowRoutes((prev) => !prev)}
              >
                {showRoutes ? "收起" : "展开"}
              </button>
              <button
                type="button"
                className="btn btn-sm btn-secondary"
                onClick={() => setRoutes({ ...defaultRoutes })}
              >
                重置默认
              </button>
            </div>

            {showRoutes && (
              <div className="stack-sm">
                {(["text", "image", "video"] as RouteKey[]).map((key) => (
                  <div key={key} className="stack-sm">
                    <div style={{ fontWeight: 700, color: "var(--text)" }}>
                      {{ text: "文本", image: "图片", video: "视频" }[key] ?? key}
                    </div>
                    <div className="form-row" style={{ gridTemplateColumns: "2fr 1fr" }}>
                      <div className="form-group">
                        <label className="form-hint">path</label>
                        <input
                          className="form-input"
                          value={routes[key].path}
                          onChange={(e) => updateRoute(key, "path", e.target.value)}
                          placeholder="/text/generations 或 https://api.example.com/v1/text/generations"
                          aria-label={`${key} path`}
                          required
                        />
                      </div>
                      <div className="form-group">
                        <label className="form-hint">timeout_seconds</label>
                        <input
                          className="form-input"
                          type="number"
                          min={0.1}
                          step={0.1}
                          value={routes[key].timeout_seconds}
                          onChange={(e) =>
                            updateRoute(key, "timeout_seconds", e.target.value)
                          }
                          aria-label={`${key} timeout_seconds`}
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="form-actions">
            <button className="btn btn-primary" type="submit" disabled={submitting}>
              {submitting && <span className="spinner" />}
              {submitting
                ? isEditing ? "保存中..." : "创建中..."
                : isEditing ? "保存修改" : "创建供应商"}
            </button>
          </div>
        </form>
      )}

      {providers.length === 0 && !showForm ? (
        <div className="gen-empty">
          <div className="gen-empty-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M12 2L2 7l10 5 10-5-10-5z" />
              <path d="M2 17l10 5 10-5" />
              <path d="M2 12l10 5 10-5" />
            </svg>
          </div>
          <p>还没有配置供应商</p>
        </div>
      ) : (
        <div className="provider-grid">
          {providers.map((p) => (
            <article key={p.provider_id} className="provider-card">
              <div>
                <h3>{p.name}</h3>
                <div className="provider-card-url">{p.base_url}</div>
                <div className="provider-card-key">{p.api_key_masked}</div>
              </div>
              <div className="model-list">
                {p.models.map((m) => (
                  <span key={m.model} className="model-tag">
                    {m.capabilities.map((c) => (
                      <span key={c} className={`cap-dot cap-${c}`} />
                    ))}
                    {m.label ?? m.model}
                  </span>
                ))}
              </div>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <span style={{ fontSize: "0.82rem", color: "var(--muted)" }}>
                  创建于 {new Date(p.created_at).toLocaleDateString("zh-CN")}
                </span>
                <span style={{ display: "flex", gap: "0.5rem" }}>
                  <button
                    className="btn btn-sm btn-secondary"
                    onClick={() => startEdit(p)}
                  >
                    编辑
                  </button>
                  <button
                    className="btn btn-sm btn-danger"
                    onClick={() => handleDelete(p)}
                  >
                    删除
                  </button>
                </span>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
