"use client";

import { useEffect, useState, type FormEvent } from "react";
import {
  listProviders,
  createProvider,
  updateProvider,
  deleteProvider,
} from "@/lib/api";
import type { ProviderResponse, ModelCapability, ProviderRoutes } from "@/types/api";

type ModelRow = { model: string; capabilities: ModelCapability[]; label: string };
type RouteKey = "text" | "image" | "video";
type RouteState = { path: string; timeout_seconds: number };
type RoutesState = Record<RouteKey, RouteState>;

const emptyModel: ModelRow = { model: "", capabilities: [], label: "" };

const capabilityLabels: Record<ModelCapability, string> = {
  text: "文本",
  image: "图片",
  video: "视频",
};

const routeLabels: Record<RouteKey, string> = {
  text: "文本",
  image: "图片",
  video: "视频",
};

const routeDefaults = {
  text: { path: "/text/generations", timeout_seconds: 60 },
  image: { path: "/image/generations", timeout_seconds: 60 },
  video: { path: "/video/generations", timeout_seconds: 600 },
} satisfies RoutesState;

function createDefaultRoutes(): RoutesState {
  return {
    text: { ...routeDefaults.text },
    image: { ...routeDefaults.image },
    video: { ...routeDefaults.video },
  };
}

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
    routes.text.path === routeDefaults.text.path &&
    routes.text.timeout_seconds === routeDefaults.text.timeout_seconds &&
    routes.image.path === routeDefaults.image.path &&
    routes.image.timeout_seconds === routeDefaults.image.timeout_seconds &&
    routes.video.path === routeDefaults.video.path &&
    routes.video.timeout_seconds === routeDefaults.video.timeout_seconds
  );
}

export function ProviderManager() {
  const [providers, setProviders] = useState<ProviderResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [editingProvider, setEditingProvider] = useState<ProviderResponse | null>(null);

  const [name, setName] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [models, setModels] = useState<ModelRow[]>([{ ...emptyModel }]);
  const [routes, setRoutes] = useState<RoutesState>(createDefaultRoutes());
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
    setRoutes(createDefaultRoutes());
    setShowRoutes(false);
    setEditingProvider(null);
  }

  function startEdit(provider: ProviderResponse) {
    setEditingProvider(provider);
    setName(provider.name);
    setBaseUrl(provider.base_url);
    setApiKey("");
    setModels(
      provider.models.map((model) => ({
        model: model.model,
        capabilities: [...model.capabilities],
        label: model.label ?? "",
      }))
    );
    setRoutes({
      text: {
        path: provider.routes.text.path ?? routeDefaults.text.path,
        timeout_seconds:
          provider.routes.text.timeout_seconds ?? routeDefaults.text.timeout_seconds,
      },
      image: {
        path: provider.routes.image.path ?? routeDefaults.image.path,
        timeout_seconds:
          provider.routes.image.timeout_seconds ?? routeDefaults.image.timeout_seconds,
      },
      video: {
        path: provider.routes.video.path ?? routeDefaults.video.path,
        timeout_seconds:
          provider.routes.video.timeout_seconds ?? routeDefaults.video.timeout_seconds,
      },
    });
    setShowRoutes(!isDefaultRoutes(provider.routes));
    setShowForm(true);
  }

  function cancelForm() {
    setShowForm(false);
    resetForm();
  }

  function toggleCap(index: number, capability: ModelCapability) {
    setModels((prev) =>
      prev.map((model, currentIndex) => {
        if (currentIndex !== index) return model;
        const hasCapability = model.capabilities.includes(capability);
        return {
          ...model,
          capabilities: hasCapability
            ? model.capabilities.filter((item) => item !== capability)
            : [...model.capabilities, capability],
        };
      })
    );
  }

  function updateModel(index: number, field: "model" | "label", value: string) {
    setModels((prev) =>
      prev.map((model, currentIndex) =>
        currentIndex === index ? { ...model, [field]: value } : model
      )
    );
  }

  function addModelRow() {
    setModels((prev) => [...prev, { ...emptyModel }]);
  }

  function removeModelRow(index: number) {
    setModels((prev) => prev.filter((_, currentIndex) => currentIndex !== index));
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
                : routeDefaults[route].timeout_seconds,
          },
        };
      }
      return { ...prev, [route]: { ...current, path: value } };
    });
  }

  async function handleDelete(provider: ProviderResponse) {
    if (provider.is_builtin) {
      setError("内置供应商不允许删除");
      return;
    }
    if (!confirm(`确定删除供应商「${provider.name}」吗？此操作不可恢复。`)) {
      return;
    }
    setError("");
    try {
      await deleteProvider(provider.provider_id);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "删除供应商失败");
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      const cleanModels = models
        .filter((model) => model.model && model.capabilities.length > 0)
        .map((model) => ({
          model: model.model,
          capabilities: model.capabilities,
          label: model.label || null,
        }));

      if (editingProvider) {
        const body: Record<string, unknown> = {
          name,
          base_url: baseUrl,
          models: cleanModels,
          routes,
        };
        if (apiKey) {
          body.api_key = apiKey;
        }
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
      {error ? <div className="error-banner">{error}</div> : null}

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

      {showForm ? (
        <form className="panel form-stack" onSubmit={handleSubmit}>
          <div className="form-row">
            <div className="form-group">
              <label className="form-label">名称</label>
              <input
                className="form-input"
                value={name}
                onChange={(event) => setName(event.target.value)}
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
                onChange={(event) => setBaseUrl(event.target.value)}
                placeholder="https://api.example.com"
                required
              />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">
              API 密钥{isEditing ? "（留空则不更新）" : ""}
            </label>
            <input
              className="form-input"
              type="password"
              value={apiKey}
              onChange={(event) => setApiKey(event.target.value)}
              placeholder="sk-..."
              required={!isEditing}
            />
          </div>

          <div className="form-group">
            <label className="form-label">模型</label>
            <div className="stack-sm">
              {models.map((model, index) => (
                <div key={index} className="form-row" style={{ alignItems: "end" }}>
                  <div className="form-group">
                    <input
                      className="form-input"
                      value={model.model}
                      onChange={(event) => updateModel(index, "model", event.target.value)}
                      placeholder="模型标识"
                    />
                  </div>
                  <div className="form-group">
                    <input
                      className="form-input"
                      value={model.label}
                      onChange={(event) => updateModel(index, "label", event.target.value)}
                      placeholder="展示名称（可选）"
                    />
                  </div>
                  <div className="model-list">
                    {(["text", "image", "video"] as ModelCapability[]).map((capability) => (
                      <button
                        type="button"
                        key={capability}
                        className={`model-tag${model.capabilities.includes(capability) ? " is-selected" : ""}`}
                        onClick={() => toggleCap(index, capability)}
                        style={{
                          cursor: "pointer",
                          opacity: model.capabilities.includes(capability) ? 1 : 0.45,
                        }}
                      >
                        <span className={`cap-dot cap-${capability}`} />
                        {capabilityLabels[capability]}
                      </button>
                    ))}
                  </div>
                  {models.length > 1 ? (
                    <button
                      type="button"
                      className="btn btn-sm btn-danger"
                      onClick={() => removeModelRow(index)}
                    >
                      删除
                    </button>
                  ) : null}
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
            <label className="form-label">路由配置（高级）</label>
            <div className="form-hint">
              请求路径支持相对路径（如 <code>/text/generations</code>）或完整地址
              （如 <code>https://api.example.com/v1/text/generations</code>）。
            </div>
            {textProviderSelected ? (
              <div className="form-hint">
                如果是兼容 OpenAI 的文本接口，基础地址建议填写
                <code>https://api.example.com/v1</code>，文本路径填写
                <code>/chat/completions</code>。
              </div>
            ) : null}
            {textRouteLooksWrong ? (
              <div className="error-banner">
                文本路由看起来不完整。<code>/v1</code> 通常只是版本前缀，不是可直接调用的
                POST 接口。如果该供应商兼容 OpenAI，请将文本路径设置为
                <code>/chat/completions</code>。
              </div>
            ) : null}
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
                onClick={() => setRoutes(createDefaultRoutes())}
              >
                重置默认
              </button>
            </div>

            {showRoutes ? (
              <div className="stack-sm">
                {(["text", "image", "video"] as RouteKey[]).map((key) => (
                  <div key={key} className="stack-sm">
                    <div style={{ fontWeight: 700, color: "var(--text)" }}>{routeLabels[key]}</div>
                    <div className="form-row" style={{ gridTemplateColumns: "2fr 1fr" }}>
                      <div className="form-group">
                        <label className="form-hint">请求路径</label>
                        <input
                          className="form-input"
                          value={routes[key].path}
                          onChange={(event) => updateRoute(key, "path", event.target.value)}
                          placeholder="/text/generations 或 https://api.example.com/v1/text/generations"
                          aria-label={`${routeLabels[key]}请求路径`}
                          required
                        />
                      </div>
                      <div className="form-group">
                        <label className="form-hint">超时时间（秒）</label>
                        <input
                          className="form-input"
                          type="number"
                          min={0.1}
                          step={0.1}
                          value={routes[key].timeout_seconds}
                          onChange={(event) =>
                            updateRoute(key, "timeout_seconds", event.target.value)
                          }
                          aria-label={`${routeLabels[key]}超时时间（秒）`}
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : null}
          </div>

          <div className="form-actions">
            <button className="btn btn-primary" type="submit" disabled={submitting}>
              {submitting ? <span className="spinner" /> : null}
              {submitting
                ? isEditing
                  ? "保存中..."
                  : "创建中..."
                : isEditing
                  ? "保存修改"
                  : "创建供应商"}
            </button>
          </div>
        </form>
      ) : null}

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
          {providers.map((provider) => (
            <article key={provider.provider_id} className="provider-card">
              <div>
                <h3>
                  {provider.name}
                  {provider.is_builtin ? (
                    <span className="tag-pill builtin-badge" style={{ marginLeft: "0.5rem" }}>
                      系统内置
                    </span>
                  ) : null}
                </h3>
                <div className="provider-card-url">{provider.base_url}</div>
                <div className="provider-card-key">{provider.api_key_masked}</div>
              </div>
              <div className="model-list">
                {provider.models.map((model) => (
                  <span key={model.model} className="model-tag">
                    {model.capabilities.map((capability) => (
                      <span key={capability} className={`cap-dot cap-${capability}`} />
                    ))}
                    {model.label ?? model.model}
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
                  创建于 {new Date(provider.created_at).toLocaleDateString("zh-CN")}
                </span>
                <span style={{ display: "flex", gap: "0.5rem" }}>
                  <button
                    className="btn btn-sm btn-secondary"
                    onClick={() => startEdit(provider)}
                  >
                    编辑
                  </button>
                  <button
                    className="btn btn-sm btn-danger"
                    disabled={provider.is_builtin}
                    onClick={() => handleDelete(provider)}
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
