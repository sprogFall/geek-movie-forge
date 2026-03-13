"use client";

import { useState } from "react";
import { listProviders, generateTexts } from "@/lib/api";
import type { ProviderResponse, TextGenerationResponse } from "@/types/api";

export function TextGenForm() {
  const [providers, setProviders] = useState<ProviderResponse[]>([]);
  const [providerId, setProviderId] = useState("");
  const [model, setModel] = useState("");
  const [taskType, setTaskType] = useState("script");
  const [sourceText, setSourceText] = useState("");
  const [prompt, setPrompt] = useState("");
  const [saveEnabled, setSaveEnabled] = useState(false);
  const [category, setCategory] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<TextGenerationResponse | null>(null);
  const [loaded, setLoaded] = useState(false);

  async function loadProviders() {
    if (loaded) return;
    try {
      const data = await listProviders();
      const filtered = data.items.filter((p) =>
        p.models.some((m) => m.capabilities.includes("text"))
      );
      setProviders(filtered);
      setLoaded(true);
    } catch {
      setError("Failed to load providers");
    }
  }

  const selectedProvider = providers.find((p) => p.provider_id === providerId);
  const textModels =
    selectedProvider?.models.filter((m) => m.capabilities.includes("text")) ?? [];

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const body: Record<string, unknown> = {
        provider_id: providerId,
        model,
        task_type: taskType,
        source_text: sourceText,
      };
      if (prompt.trim()) {
        body.prompt = prompt;
      }
      if (saveEnabled) {
        body.save = { enabled: true, category: category || "text-output", tags: [] };
      }
      const res = await generateTexts(body);
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

        <div className="form-row">
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
              {textModels.map((m) => (
                <option key={m.model} value={m.model}>
                  {m.label ?? m.model}
                </option>
              ))}
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">Task type</label>
            <select
              className="form-select"
              value={taskType}
              onChange={(e) => setTaskType(e.target.value)}
            >
              <option value="script">Script writing</option>
              <option value="caption">Caption</option>
              <option value="copy">Copywriting</option>
              <option value="summary">Summary</option>
              <option value="translate">Translation</option>
            </select>
          </div>
        </div>

        <div className="form-group">
          <label className="form-label">Source text</label>
          <textarea
            className="form-textarea"
            value={sourceText}
            onChange={(e) => setSourceText(e.target.value)}
            placeholder="Paste or type your source material here..."
            rows={5}
            required
          />
        </div>

        <div className="form-group">
          <label className="form-label">Additional prompt</label>
          <span className="form-hint">Optional instructions to guide the generation</span>
          <textarea
            className="form-textarea"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="e.g. Keep it under 200 words, use a conversational tone..."
            rows={3}
          />
        </div>

        <div className="form-check">
          <input
            id="save-text"
            type="checkbox"
            checked={saveEnabled}
            onChange={(e) => setSaveEnabled(e.target.checked)}
          />
          <label htmlFor="save-text" className="form-label">
            Save to asset library
          </label>
        </div>

        <div className="form-actions">
          <button className="btn btn-primary" type="submit" disabled={loading}>
            {loading && <span className="spinner" />}
            {loading ? "Generating..." : "Generate text"}
          </button>
        </div>
      </form>

      <div className="gen-results">
        {error && <div className="error-banner">{error}</div>}

        {result && (
          <>
            <div className="info-banner">
              Text generated &middot; {result.task_type} &middot; model: {result.model}
            </div>
            <div className="gen-text-output">{result.output_text}</div>
          </>
        )}

        {!result && !error && (
          <div className="gen-empty">
            <div className="gen-empty-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
                <path d="M14 2v6h6" />
                <path d="M16 13H8" />
                <path d="M16 17H8" />
                <path d="M10 9H8" />
              </svg>
            </div>
            <p>Generated text will appear here</p>
          </div>
        )}
      </div>
    </div>
  );
}
