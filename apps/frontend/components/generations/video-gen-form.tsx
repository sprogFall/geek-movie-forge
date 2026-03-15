"use client";

import { useEffect, useState } from "react";
import { createAsset, generateVideos, listProviders } from "@/lib/api";
import { formatElapsed, useElapsedMs } from "@/lib/elapsed";
import type { AssetResponse, MediaGenerationResponse, ProviderResponse } from "@/types/api";

export function VideoGenForm() {
  const [providers, setProviders] = useState<ProviderResponse[]>([]);
  const LAST_PROVIDER_KEY = "gmf_last_provider:video";
  const [providerId, setProviderId] = useState(() => {
    if (typeof window === "undefined") return "";
    return localStorage.getItem(LAST_PROVIDER_KEY) ?? "";
  });
  const [model, setModel] = useState("");
  const [prompt, setPrompt] = useState("");
  const [count, setCount] = useState(1);
  const [imageMaterialUrls, setImageMaterialUrls] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<MediaGenerationResponse | null>(null);
  const [loaded, setLoaded] = useState(false);

  const [saveCategory, setSaveCategory] = useState("生成");
  const [savingAssets, setSavingAssets] = useState(false);
  const [saveError, setSaveError] = useState("");
  const [savedAssets, setSavedAssets] = useState<AssetResponse[]>([]);

  const [preview, setPreview] = useState<{ src: string; poster?: string | null; title: string } | null>(
    null
  );

  const elapsedMs = useElapsedMs(loading);

  useEffect(() => {
    if (!providerId) return;
    void loadProviders();
  }, [providerId]);

  async function loadProviders() {
    if (loaded) return;
    try {
      const data = await listProviders();
      const filtered = data.items.filter((p) =>
        p.models.some((m) => m.capabilities.includes("video"))
      );
      setProviders(filtered);
      setLoaded(true);
      if (providerId && !filtered.some((p) => p.provider_id === providerId)) {
        setProviderId("");
        setModel("");
      }
    } catch {
      setError("加载供应商失败");
    }
  }

  const selectedProvider = providers.find((p) => p.provider_id === providerId);
  const videoModels =
    selectedProvider?.models.filter((m) => m.capabilities.includes("video")) ?? [];

  async function handleSaveToAssets() {
    if (!result) return;
    if (savedAssets.length > 0) return;
    const categoryValue = saveCategory.trim() || "生成";

    setSavingAssets(true);
    setSaveError("");
    try {
      const assets = await Promise.all(
        result.outputs.map((output, index) => {
          const srcUrl = output.url ?? null;
          const base64 = output.base64_data ?? null;
          if (!srcUrl && !base64) {
            throw new Error("生成结果缺少可保存的内容");
          }
          const mimeType =
            base64 != null ? output.mime_type ?? "video/mp4" : (output.mime_type ?? null);
          return createAsset(
            {
              asset_type: "video",
              category: categoryValue,
              name: `video-result-${index + 1}`,
              content_url: srcUrl,
              content_base64: base64,
              mime_type: mimeType,
              metadata: output.metadata ?? {},
              provider_id: result.provider_id,
              model: result.model,
              tags: [],
            },
            { origin: "generated" }
          );
        })
      );
      setSavedAssets(assets);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "保存失败");
    } finally {
      setSavingAssets(false);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    setResult(null);
    setSaveError("");
    setSavedAssets([]);
    try {
      const body: Record<string, unknown> = {
        provider_id: providerId,
        model,
        prompt,
        count,
      };
      if (imageMaterialUrls.trim()) {
        body.image_material_urls = imageMaterialUrls
          .split("\n")
          .map((u) => u.trim())
          .filter(Boolean);
      }
      const res = await generateVideos(body);
      setResult(res);
      localStorage.setItem(LAST_PROVIDER_KEY, providerId);
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
            {videoModels.map((m) => (
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
            placeholder="描述你想生成的视频..."
            rows={4}
            required
          />
        </div>

        <div className="form-group">
          <label className="form-label">参考图片 URL</label>
          <span className="form-hint">每行一个 URL（可选）</span>
          <textarea
            className="form-textarea"
            value={imageMaterialUrls}
            onChange={(e) => setImageMaterialUrls(e.target.value)}
            placeholder="https://example.com/ref1.jpg&#10;https://example.com/ref2.jpg"
            rows={3}
          />
        </div>

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

        <div className="form-actions">
          <button className="btn btn-primary" type="submit" disabled={loading}>
            {loading && <span className="spinner" />}
            {loading ? "生成中..." : "生成视频"}
          </button>
        </div>
      </form>

      <div className="gen-results">
        {error && <div className="error-banner">{error}</div>}

        {result && (
          <>
            <div className="info-banner">
              已生成 {result.outputs.length} 段视频 &middot; {result.resolved_prompt.slice(0, 80)}
              {result.resolved_prompt.length > 80 ? "..." : ""}
            </div>

            <div className="panel form-stack">
              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">保存分类</label>
                  <input
                    className="form-input"
                    type="text"
                    value={saveCategory}
                    onChange={(e) => setSaveCategory(e.target.value)}
                    placeholder="例如：场景片段"
                    disabled={savedAssets.length > 0 || savingAssets}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">素材库</label>
                  <div className="form-actions" style={{ paddingTop: 0 }}>
                    <button
                      className="btn btn-secondary"
                      type="button"
                      onClick={handleSaveToAssets}
                      disabled={savingAssets || savedAssets.length > 0}
                    >
                      {savingAssets && <span className="spinner spinner-dark" />}
                      {savedAssets.length > 0 ? "已加入素材库" : "加入素材库"}
                    </button>
                    {savedAssets.length > 0 && (
                      <span style={{ color: "var(--muted)", fontSize: "0.88rem" }}>
                        已保存 {savedAssets.length} 个
                      </span>
                    )}
                  </div>
                </div>
              </div>
              {saveError && <div className="error-banner">{saveError}</div>}
            </div>

            <div className="gen-output-grid">
              {result.outputs.map((output) => (
                <div key={output.index} className="gen-output-card">
                  {output.url && (
                    <video src={output.url} controls poster={output.cover_image_url ?? undefined} />
                  )}
                  <div className="gen-output-meta gen-output-meta-row">
                    <small>
                      视频 {output.index + 1}
                      {output.duration_seconds != null &&
                        ` \u00B7 ${output.duration_seconds.toFixed(1)}s`}
                    </small>
                    {output.url && (
                      <button
                        className="btn btn-secondary btn-sm"
                        type="button"
                        onClick={() =>
                          setPreview({
                            src: output.url!,
                            poster: output.cover_image_url,
                            title: `生成视频 ${output.index + 1}`,
                          })
                        }
                      >
                        预览
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </>
        )}

        {!result && !error && (
          <div className="gen-empty-shell">
            <div className="gen-empty">
              <div className="gen-empty-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <polygon points="5 3 19 12 5 21 5 3" />
                </svg>
              </div>
              <p>生成结果会显示在这里</p>
            </div>

            {loading && (
              <div className="gen-empty-overlay" role="status" aria-live="polite">
                <span className="spinner spinner-dark" />
                <div className="gen-empty-overlay-text">
                  <strong>生成中...</strong>
                  <span>已用时 {formatElapsed(elapsedMs)}</span>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {preview && (
        <div className="dialog-overlay" role="dialog" aria-modal="true" onClick={() => setPreview(null)}>
          <div className="dialog-panel media-preview-panel" onClick={(e) => e.stopPropagation()}>
            <div className="media-preview-header">
              <h2>{preview.title}</h2>
              <button className="btn btn-secondary btn-sm" type="button" onClick={() => setPreview(null)}>
                关闭
              </button>
            </div>
            <video
              className="media-preview-video"
              src={preview.src}
              controls
              poster={preview.poster ?? undefined}
            />
          </div>
        </div>
      )}
    </div>
  );
}
