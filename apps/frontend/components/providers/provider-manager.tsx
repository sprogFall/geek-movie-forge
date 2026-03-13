"use client";

import { useEffect, useState } from "react";
import { listProviders, createProvider } from "@/lib/api";
import type { ProviderResponse, ModelCapability } from "@/types/api";

type ModelRow = { model: string; capabilities: ModelCapability[]; label: string };

const emptyModel: ModelRow = { model: "", capabilities: [], label: "" };

export function ProviderManager() {
  const [providers, setProviders] = useState<ProviderResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);

  /* form state */
  const [name, setName] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [models, setModels] = useState<ModelRow[]>([{ ...emptyModel }]);
  const [submitting, setSubmitting] = useState(false);

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

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      const body = {
        name,
        base_url: baseUrl,
        api_key: apiKey,
        models: models
          .filter((m) => m.model && m.capabilities.length > 0)
          .map((m) => ({
            model: m.model,
            capabilities: m.capabilities,
            label: m.label || null,
          })),
      };
      await createProvider(body);
      setShowForm(false);
      setName("");
      setBaseUrl("");
      setApiKey("");
      setModels([{ ...emptyModel }]);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "创建供应商失败");
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

  return (
    <div className="stack-lg">
      {error && <div className="error-banner">{error}</div>}

      <div className="form-actions">
        <button
          className="btn btn-primary"
          onClick={() => setShowForm(!showForm)}
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
            <label className="form-label">API Key</label>
            <input
              className="form-input"
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="sk-..."
              required
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

          <div className="form-actions">
            <button className="btn btn-primary" type="submit" disabled={submitting}>
              {submitting && <span className="spinner" />}
              {submitting ? "创建中..." : "创建供应商"}
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
              <div style={{ fontSize: "0.82rem", color: "var(--muted)" }}>
                创建于 {new Date(p.created_at).toLocaleDateString("zh-CN")}
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
