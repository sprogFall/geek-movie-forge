"use client";

import { useEffect, useState } from "react";
import { createAsset, generateVideos, listAssets, listProviders } from "@/lib/api";
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
  const [imageMaterialAssetIds, setImageMaterialAssetIds] = useState<string[]>([]);
  const [imageAssets, setImageAssets] = useState<AssetResponse[]>([]);
  const [assetPickerOpen, setAssetPickerOpen] = useState(false);
  const [assetPickerLoading, setAssetPickerLoading] = useState(false);
  const [assetPickerError, setAssetPickerError] = useState("");
  const [uploadingRefs, setUploadingRefs] = useState(false);
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

  const selectedImageAssets = imageAssets.filter((a) => imageMaterialAssetIds.includes(a.asset_id));

  async function openAssetPicker() {
    setAssetPickerOpen(true);
    if (imageAssets.length > 0) return;
    setAssetPickerLoading(true);
    setAssetPickerError("");
    try {
      const data = await listAssets({ asset_type: "image" });
      setImageAssets(data.items);
    } catch (err) {
      setAssetPickerError(err instanceof Error ? err.message : "加载素材失败");
    } finally {
      setAssetPickerLoading(false);
    }
  }

  function toggleImageAsset(assetId: string) {
    setImageMaterialAssetIds((prev) =>
      prev.includes(assetId) ? prev.filter((id) => id !== assetId) : [...prev, assetId]
    );
  }

  async function handleUploadRefs(files: FileList | null) {
    if (!files || files.length === 0) return;
    setUploadingRefs(true);
    setError("");
    try {
      const items = Array.from(files);
      const uploaded = await Promise.all(
        items.map(async (file) => {
          const base64 = await new Promise<string>((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => {
              const result = String(reader.result ?? "");
              const comma = result.indexOf(",");
              if (comma === -1) return reject(new Error("无法读取图片内容"));
              resolve(result.slice(comma + 1));
            };
            reader.onerror = () => reject(new Error("无法读取图片内容"));
            reader.readAsDataURL(file);
          });
          return createAsset({
            asset_type: "image",
            category: "reference",
            name: file.name || "uploaded-reference",
            content_base64: base64,
            mime_type: file.type || "image/png",
            tags: ["reference"],
            metadata: { uploaded_for: "video_generation" },
          });
        })
      );
      setImageAssets((prev) => [...uploaded, ...prev]);
      setImageMaterialAssetIds((prev) => {
        const next = new Set(prev);
        for (const asset of uploaded) next.add(asset.asset_id);
        return Array.from(next);
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "上传失败");
    } finally {
      setUploadingRefs(false);
    }
  }

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
      if (imageMaterialAssetIds.length > 0) {
        body.image_material_asset_ids = imageMaterialAssetIds;
      }
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
          <label className="form-label">参考图片</label>
          <span className="form-hint">支持 URL / 素材库选择 / 本地上传（可选）</span>
          <div className="form-actions" style={{ paddingTop: 0, flexWrap: "wrap" }}>
            <button
              className="btn btn-sm btn-secondary"
              type="button"
              onClick={openAssetPicker}
              disabled={uploadingRefs}
            >
              从素材库选择
            </button>
            <label className="btn btn-sm btn-secondary" style={{ position: "relative", overflow: "hidden" }}>
              {uploadingRefs ? "上传中..." : "上传图片"}
              <input
                type="file"
                accept="image/*"
                multiple
                onChange={(e) => void handleUploadRefs(e.target.files)}
                style={{
                  position: "absolute",
                  inset: 0,
                  opacity: 0,
                  cursor: "pointer",
                }}
                disabled={uploadingRefs}
              />
            </label>
            <span style={{ color: "var(--muted)", fontSize: "0.88rem" }}>
              已选 {imageMaterialAssetIds.length} 张
            </span>
            {imageMaterialAssetIds.length > 0 && (
              <button
                className="btn btn-sm btn-secondary"
                type="button"
                onClick={() => setImageMaterialAssetIds([])}
                disabled={uploadingRefs}
              >
                清空选择
              </button>
            )}
          </div>

          <textarea
            className="form-textarea"
            value={imageMaterialUrls}
            onChange={(e) => setImageMaterialUrls(e.target.value)}
            placeholder="https://example.com/ref1.jpg&#10;https://example.com/ref2.jpg"
            rows={3}
          />
          {selectedImageAssets.length > 0 && (
            <div className="asset-gallery" style={{ marginTop: 12 }}>
              {selectedImageAssets.slice(0, 6).map((asset) => {
                const src = asset.content_url
                  ? asset.content_url
                  : asset.content_base64
                    ? `data:${asset.mime_type ?? "image/png"};base64,${asset.content_base64}`
                    : null;
                return (
                  <article
                    key={asset.asset_id}
                    className="asset-card"
                    style={{ cursor: "pointer" }}
                    onClick={() => toggleImageAsset(asset.asset_id)}
                    title="点击取消选择"
                  >
                    {src ? <img className="asset-thumb" src={src} alt={asset.name} /> : null}
                    <div className="asset-info">
                      <h4 style={{ fontSize: "0.95rem" }}>{asset.name}</h4>
                      <div className="asset-info-meta">
                        <span className="tag-pill">已选</span>
                        <span className="tag-pill">{asset.category}</span>
                      </div>
                    </div>
                  </article>
                );
              })}
            </div>
          )}
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

      {assetPickerOpen && (
        <div
          className="dialog-overlay"
          role="dialog"
          aria-modal="true"
          onClick={() => setAssetPickerOpen(false)}
        >
          <div className="dialog-panel asset-detail-panel" onClick={(e) => e.stopPropagation()}>
            <div className="media-preview-header">
              <h2 style={{ margin: 0 }}>选择参考图片</h2>
              <button className="btn btn-secondary btn-sm" type="button" onClick={() => setAssetPickerOpen(false)}>
                关闭
              </button>
            </div>
            {assetPickerError && <div className="error-banner" style={{ marginTop: 16 }}>{assetPickerError}</div>}
            {assetPickerLoading ? (
              <div className="gen-empty">
                <span className="spinner spinner-dark" />
                <p>正在加载素材...</p>
              </div>
            ) : imageAssets.length === 0 ? (
              <div className="gen-empty">
                <p>素材库中还没有图片素材</p>
              </div>
            ) : (
              <div className="asset-gallery" style={{ marginTop: 16 }}>
                {imageAssets.map((asset) => {
                  const src = asset.content_url
                    ? asset.content_url
                    : asset.content_base64
                      ? `data:${asset.mime_type ?? "image/png"};base64,${asset.content_base64}`
                      : null;
                  const selected = imageMaterialAssetIds.includes(asset.asset_id);
                  return (
                    <article
                      key={asset.asset_id}
                      className="asset-card"
                      style={{ outline: selected ? "2px solid var(--accent)" : undefined }}
                      onClick={() => toggleImageAsset(asset.asset_id)}
                    >
                      {src ? <img className="asset-thumb" src={src} alt={asset.name} /> : null}
                      <div className="asset-info">
                        <h4>{asset.name}</h4>
                        <div className="asset-info-meta">
                          <span className="tag-pill">{selected ? "已选" : "点击选择"}</span>
                          <span className="tag-pill">{asset.origin === "manual" ? "手动" : "生成"}</span>
                          {asset.category && <span className="tag-pill">{asset.category}</span>}
                        </div>
                      </div>
                    </article>
                  );
                })}
              </div>
            )}
            <div className="form-actions" style={{ marginTop: 16 }}>
              <button className="btn btn-primary" type="button" onClick={() => setAssetPickerOpen(false)}>
                确认（已选 {imageMaterialAssetIds.length} 张）
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
