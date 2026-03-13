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
      setError("加载供应商失败");
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
        body.save = { enabled: true, category: category || "文本输出", tags: [] };
      }
      const res = await generateTexts(body);
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

        <div className="form-row">
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
              {textModels.map((m) => (
                <option key={m.model} value={m.model}>
                  {m.label ?? m.model}
                </option>
              ))}
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">任务类型</label>
            <select
              className="form-select"
              value={taskType}
              onChange={(e) => setTaskType(e.target.value)}
            >
              <option value="script">脚本写作</option>
              <option value="caption">字幕</option>
              <option value="copy">文案</option>
              <option value="summary">摘要</option>
              <option value="translate">翻译</option>
            </select>
          </div>
        </div>

        <div className="form-group">
          <label className="form-label">源文本</label>
          <textarea
            className="form-textarea"
            value={sourceText}
            onChange={(e) => setSourceText(e.target.value)}
            placeholder="在这里粘贴或输入素材内容..."
            rows={5}
            required
          />
        </div>

        <div className="form-group">
          <label className="form-label">附加提示</label>
          <span className="form-hint">可选，用于补充约束或风格要求</span>
          <textarea
            className="form-textarea"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="例如：控制在 200 字以内，口语化风格..."
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
            保存到素材库
          </label>
        </div>

        <div className="form-actions">
          <button className="btn btn-primary" type="submit" disabled={loading}>
            {loading && <span className="spinner" />}
            {loading ? "生成中..." : "生成文本"}
          </button>
        </div>
      </form>

      <div className="gen-results">
        {error && <div className="error-banner">{error}</div>}

        {result && (
          <>
            <div className="info-banner">
              已生成文本 &middot; 类型：{result.task_type} &middot; 模型：{result.model}
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
            <p>生成结果会显示在这里</p>
          </div>
        )}
      </div>
    </div>
  );
}
