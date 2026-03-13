"use client";

import { useState } from "react";
import { listProviders, generateVideos } from "@/lib/api";
import type { ProviderResponse, MediaGenerationResponse } from "@/types/api";

export function VideoGenForm() {
  const [providers, setProviders] = useState<ProviderResponse[]>([]);
  const [providerId, setProviderId] = useState("");
  const [model, setModel] = useState("");
  const [prompt, setPrompt] = useState("");
  const [count, setCount] = useState(1);
  const [imageMaterialUrls, setImageMaterialUrls] = useState("");
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
        p.models.some((m) => m.capabilities.includes("video"))
      );
      setProviders(filtered);
      setLoaded(true);
    } catch {
      setError("Failed to load providers");
    }
  }

  const selectedProvider = providers.find((p) => p.provider_id === providerId);
  const videoModels =
    selectedProvider?.models.filter((m) => m.capabilities.includes("video")) ?? [];

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
      if (imageMaterialUrls.trim()) {
        body.image_material_urls = imageMaterialUrls
          .split("\n")
          .map((u) => u.trim())
          .filter(Boolean);
      }
      if (saveEnabled) {
        body.save = { enabled: true, category: category || "generated", tags: [] };
      }
      const res = await generateVideos(body);
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generation failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="gen-layout">
      <form className="panel form-stack" onSubmit={handleSubmit}>
        <div className="form-group">
          <label className="form-label">Provider</label>
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
            <option value="">Select a provider...</option>
            {providers.map((p) => (
              <option key={p.provider_id} value={p.provider_id}>
                {p.name}
              </option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label className="form-label">Model</label>
          <select
            className="form-select"
            value={model}
            onChange={(e) => setModel(e.target.value)}
            required
            disabled={!providerId}
          >
            <option value="">Select a model...</option>
            {videoModels.map((m) => (
              <option key={m.model} value={m.model}>
                {m.label ?? m.model}
              </option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label className="form-label">Prompt</label>
          <textarea
            className="form-textarea"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Describe the video you want to generate..."
            rows={4}
            required
          />
        </div>

        <div className="form-group">
          <label className="form-label">Reference image URLs</label>
          <span className="form-hint">One URL per line (optional)</span>
          <textarea
            className="form-textarea"
            value={imageMaterialUrls}
            onChange={(e) => setImageMaterialUrls(e.target.value)}
            placeholder="https://example.com/ref1.jpg&#10;https://example.com/ref2.jpg"
            rows={3}
          />
        </div>

        <div className="form-row">
          <div className="form-group">
            <label className="form-label">Count</label>
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
            <label className="form-label">Category</label>
            <input
              className="form-input"
              type="text"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              placeholder="e.g. scene-clip"
            />
          </div>
        </div>

        <div className="form-check">
          <input
            id="save-video"
            type="checkbox"
            checked={saveEnabled}
            onChange={(e) => setSaveEnabled(e.target.checked)}
          />
          <label htmlFor="save-video" className="form-label">
            Save to asset library
          </label>
        </div>

        <div className="form-actions">
          <button className="btn btn-primary" type="submit" disabled={loading}>
            {loading && <span className="spinner" />}
            {loading ? "Generating..." : "Generate videos"}
          </button>
        </div>
      </form>

      <div className="gen-results">
        {error && <div className="error-banner">{error}</div>}

        {result && (
          <>
            <div className="info-banner">
              Generated {result.outputs.length} video(s) &middot; {result.resolved_prompt.slice(0, 80)}
              {result.resolved_prompt.length > 80 ? "..." : ""}
            </div>
            <div className="gen-output-grid">
              {result.outputs.map((output) => (
                <div key={output.index} className="gen-output-card">
                  {output.url && (
                    <video src={output.url} controls poster={output.cover_image_url ?? undefined} />
                  )}
                  <div className="gen-output-meta">
                    <small>
                      Video {output.index + 1}
                      {output.duration_seconds != null &&
                        ` \u00B7 ${output.duration_seconds.toFixed(1)}s`}
                    </small>
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
                <polygon points="5 3 19 12 5 21 5 3" />
              </svg>
            </div>
            <p>Generated videos will appear here</p>
          </div>
        )}
      </div>
    </div>
  );
}
