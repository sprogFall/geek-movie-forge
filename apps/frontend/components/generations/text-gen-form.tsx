"use client";

import { useEffect, useState } from "react";
import { createAsset, generateTexts, listProviders } from "@/lib/api";
import { formatElapsed, useElapsedMs } from "@/lib/elapsed";
import type { AssetResponse, ProviderResponse, TextGenerationResponse } from "@/types/api";

export function TextGenForm() {
  const [providers, setProviders] = useState<ProviderResponse[]>([]);
  const LAST_PROVIDER_KEY = "gmf_last_provider:text";
  const [providerId, setProviderId] = useState(() => {
    if (typeof window === "undefined") return "";
    return localStorage.getItem(LAST_PROVIDER_KEY) ?? "";
  });
  const [model, setModel] = useState("");
  const [taskType, setTaskType] = useState("script");
  const [sourceText, setSourceText] = useState("");
  const [prompt, setPrompt] = useState("");
  const [forceChinese, setForceChinese] = useState(true);
  const [forceScript, setForceScript] = useState(taskType === "script");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<TextGenerationResponse | null>(null);
  const [loaded, setLoaded] = useState(false);

  const [saveCategory, setSaveCategory] = useState("文本输出");
  const [savingAssets, setSavingAssets] = useState(false);
  const [saveError, setSaveError] = useState("");
  const [savedAssets, setSavedAssets] = useState<AssetResponse[]>([]);

  const [copyHint, setCopyHint] = useState("");

  const elapsedMs = useElapsedMs(loading);

  useEffect(() => {
    if (!providerId) return;
    void loadProviders();
  }, [providerId]);

  useEffect(() => {
    if (taskType === "script") {
      setForceScript(true);
    }
  }, [taskType]);

  async function loadProviders() {
    if (loaded) return;
    try {
      const data = await listProviders();
      const filtered = data.items.filter((p) =>
        p.models.some((m) => m.capabilities.includes("text"))
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
  const textModels =
    selectedProvider?.models.filter((m) => m.capabilities.includes("text")) ?? [];

  async function copyToClipboard(text: string) {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return;
    }
    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.style.position = "fixed";
    textarea.style.left = "-9999px";
    textarea.style.top = "0";
    document.body.appendChild(textarea);
    textarea.focus();
    textarea.select();
    const ok = document.execCommand("copy");
    document.body.removeChild(textarea);
    if (!ok) {
      throw new Error("复制失败");
    }
  }

  async function handleCopy() {
    if (!result) return;
    setCopyHint("");
    try {
      await copyToClipboard(result.output_text);
      setCopyHint("已复制");
    } catch {
      setCopyHint("复制失败");
    } finally {
      window.setTimeout(() => setCopyHint(""), 2000);
    }
  }

  function composePromptWithConstraints() {
    const constraints: string[] = [];
    if (forceChinese) {
      constraints.push("请使用中文输出，仅保留中文内容，避免英文或代码块。");
    }
    if (forceScript) {
      constraints.push("请以脚本格式组织内容，包含镜头方向、台词与动作，不要解释提示词。");
    }
    const trimmedPrompt = prompt.trim();
    if (trimmedPrompt) {
      constraints.push(trimmedPrompt);
    }
    return constraints.join("\n");
  }

  async function handleSaveToAssets() {
    if (!result) return;
    if (savedAssets.length > 0) return;
    const categoryValue = saveCategory.trim() || "文本输出";

    setSavingAssets(true);
    setSaveError("");
    try {
      const asset = await createAsset(
        {
          asset_type: "text",
          category: categoryValue,
          name: `text-${result.task_type}-result`,
          content_text: result.output_text,
          metadata: {},
          provider_id: result.provider_id,
          model: result.model,
          tags: [],
        },
        { origin: "generated" }
      );
      setSavedAssets([asset]);
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
    setCopyHint("");
    try {
      const body: Record<string, unknown> = {
        provider_id: providerId,
        model,
        task_type: taskType,
        source_text: sourceText,
      };
      const finalPrompt = composePromptWithConstraints();
      if (finalPrompt) {
        body.prompt = finalPrompt;
      }
      const res = await generateTexts(body);
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
          <span className="form-hint">
            可选，用于补充约束或风格要求。系统会额外强制中文纯文本输出，避免返回代码。
          </span>
          <textarea
            className="form-textarea"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="例如：控制在 200 字以内，口语化风格..."
            rows={3}
          />
        </div>

        <div className="form-group">
          <label className="form-label">语言与格式</label>
          <div className="form-actions" style={{ gap: "1rem", flexWrap: "wrap" }}>
            <label style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
              <input
                type="checkbox"
                checked={forceChinese}
                onChange={(e) => setForceChinese(e.target.checked)}
              />
              <span>仅输出中文</span>
            </label>
            <label style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
              <input
                type="checkbox"
                checked={forceScript}
                onChange={(e) => setForceScript(e.target.checked)}
              />
              <span>以脚本格式呈现</span>
            </label>
          </div>
          <span className="form-hint">
            勾选后会在提示词前自动补充约束，以减少英文、讲解性内容或代码。
          </span>
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
            <div className="panel form-stack">
              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">保存分类</label>
                  <input
                    className="form-input"
                    type="text"
                    value={saveCategory}
                    onChange={(e) => setSaveCategory(e.target.value)}
                    placeholder="例如：台词"
                    disabled={savedAssets.length > 0 || savingAssets}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">操作</label>
                  <div className="form-actions" style={{ paddingTop: 0, flexWrap: "wrap" }}>
                    <button className="btn btn-secondary" type="button" onClick={handleCopy}>
                      复制文本
                    </button>
                    <button
                      className="btn btn-secondary"
                      type="button"
                      onClick={handleSaveToAssets}
                      disabled={savingAssets || savedAssets.length > 0}
                    >
                      {savingAssets && <span className="spinner spinner-dark" />}
                      {savedAssets.length > 0 ? "已加入素材库" : "加入素材库"}
                    </button>
                    {copyHint && (
                      <span style={{ color: "var(--muted)", fontSize: "0.88rem" }}>
                        {copyHint}
                      </span>
                    )}
                    {savedAssets.length > 0 && (
                      <span style={{ color: "var(--muted)", fontSize: "0.88rem" }}>
                        已保存 1 个
                      </span>
                    )}
                  </div>
                </div>
              </div>
              {saveError && <div className="error-banner">{saveError}</div>}
            </div>
            <div className="gen-text-output">{result.output_text}</div>
          </>
        )}

        {!result && !error && (
          <div className="gen-empty-shell">
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
    </div>
  );
}
