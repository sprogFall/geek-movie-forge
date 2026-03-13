"use client";

import { useState } from "react";
import { listProviders, generateImages } from "@/lib/api";
import type { ProviderResponse, MediaGenerationResponse } from "@/types/api";

export function ImageGenForm() {
  const [providers, setProviders] = useState<ProviderResponse[]>([]);
  const [providerId, setProviderId] = useState("");
  const [model, setModel] = useState("");
  const [prompt, setPrompt] = useState("");
  const [count, setCount] = useState(1);
  const [saveEnabled, setSaveEnabled] = useState(false);
  const [category, setCategory] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<MediaGenerationResponse | null>(null);
  const [loaded, setLoaded] = useState(false);

  async function loadProviders() {
    if (loaded) return;
    try {
      const data = await listProviders();
      const filtered = data.items.filter((p) =>
        p.models.some((m) => m.capabilities.includes("image"))
      );
      setProviders(filtered);
      setLoaded(true);
    } catch {
      setError("加载供应商失败");
    }
  }

  const selectedProvider = providers.find((p) => p.provider_id === providerId);
  const imageModels =
    selectedProvider?.models.filter((m) => m.capabilities.includes("image")) ?? [];

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const body: Record<string, unknown> = {
        provider_id: providerId,
        model,
        prompt,
        count,
      };
      if (saveEnabled) {
        body.save = { enabled: true, category: category || "生成", tags: [] };
      }
      const res = await generateImages(body);
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "生成失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="gen-layout">
      <form className="panel form-stack" onSubmit={handleSubmit}>
        <div className="form-group">
          <label className="form-label">供应商</label>
          <select
            className="form-select"
            value={providerId}
            onFocus={loadProviders}
            onChange={(e) => {
              setProviderId(e.target.value);
              setModel("");
            }}
            required
          >
            <option value="">请选择供应商...</option>
            {providers.map((p) => (
              <option key={p.provider_id} value={p.provider_id}>
                {p.name}
              </option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label className="form-label">模型</label>
          <select
            className="form-select"
            value={model}
            onChange={(e) => setModel(e.target.value)}
            required
            disabled={!providerId}
          >
            <option value="">请选择模型...</option>
            {imageModels.map((m) => (
              <option key={m.model} value={m.model}>
                {m.label ?? m.model}
              </option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label className="form-label">提示词</label>
          <textarea
            className="form-textarea"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="描述你想生成的图片..."
            rows={4}
            required
          />
        </div>

        <div className="form-row">
          <div className="form-group">
            <label className="form-label">数量</label>
            <input
              className="form-input"
              type="number"
              min={1}
              max={10}
              value={count}
              onChange={(e) => setCount(Number(e.target.value))}
            />
          </div>
          <div className="form-group">
            <label className="form-label">分类</label>
            <input
              className="form-input"
              type="text"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              placeholder="例如：分镜"
            />
          </div>
        </div>

        <div className="form-check">
          <input
            id="save-image"
            type="checkbox"
            checked={saveEnabled}
            onChange={(e) => setSaveEnabled(e.target.checked)}
          />
          <label htmlFor="save-image" className="form-label">
            保存到素材库
          </label>
        </div>

        <div className="form-actions">
          <button className="btn btn-primary" type="submit" disabled={loading}>
            {loading && <span className="spinner" />}
            {loading ? "生成中..." : "生成图片"}
          </button>
        </div>
      </form>

      <div className="gen-results">
        {error && <div className="error-banner">{error}</div>}

        {result && (
          <>
            <div className="info-banner">
              已生成 {result.outputs.length} 张图片 &middot; {result.resolved_prompt.slice(0, 80)}
              {result.resolved_prompt.length > 80 ? "..." : ""}
            </div>
            <div className="gen-output-grid">
              {result.outputs.map((output) => (
                <div key={output.index} className="gen-output-card">
                  {output.url && (
                    <img src={output.url} alt={`生成图片 ${output.index + 1}`} />
                  )}
                  {output.base64_data && (
                    <img
                      src={`data:${output.mime_type ?? "image/png"};base64,${output.base64_data}`}
                      alt={`生成图片 ${output.index + 1}`}
                    />
                  )}
                  <div className="gen-output-meta">
                    <small>图片 {output.index + 1}</small>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}

        {!result && !error && (
          <div className="gen-empty">
            <div className="gen-empty-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <rect x="3" y="3" width="18" height="18" rx="2" />
                <circle cx="8.5" cy="8.5" r="1.5" />
                <path d="M21 15l-5-5L5 21" />
              </svg>
            </div>
            <p>生成结果会显示在这里</p>
          </div>
        )}
      </div>
    </div>
  );
}
