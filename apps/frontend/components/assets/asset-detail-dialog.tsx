"use client";

import { useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { deleteAsset, updateAsset } from "@/lib/api";
import type { AssetResponse } from "@/types/api";

type Props = {
  asset: AssetResponse;
  onClose: () => void;
  onUpdated: (asset: AssetResponse) => void;
  onDeleted: (assetId: string) => void;
};

function parseTags(input: string) {
  const parts = input
    .split(/[\n,]/g)
    .map((v) => v.trim())
    .filter(Boolean);
  const seen = new Set<string>();
  const out: string[] = [];
  for (const part of parts) {
    const key = part.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(part);
  }
  return out;
}

export function AssetDetailDialog({ asset, onClose, onUpdated, onDeleted }: Props) {
  const [mode, setMode] = useState<"preview" | "edit">("preview");
  const [tagsText, setTagsText] = useState(asset.tags.join(", "));
  const [contentText, setContentText] = useState(asset.content_text ?? "");
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState("");

  const canEditText = asset.asset_type === "text";

  const mediaSrc = useMemo(() => {
    if (asset.content_url) return asset.content_url;
    if (asset.content_base64 && asset.asset_type === "image") {
      return `data:${asset.mime_type ?? "image/png"};base64,${asset.content_base64}`;
    }
    if (asset.content_base64 && asset.asset_type === "video") {
      return `data:${asset.mime_type ?? "video/mp4"};base64,${asset.content_base64}`;
    }
    return null;
  }, [asset]);

  async function handleSave() {
    setSaving(true);
    setError("");
    try {
      const body: Record<string, unknown> = { tags: parseTags(tagsText) };
      if (canEditText) body.content_text = contentText;
      const updated = await updateAsset(asset.asset_id, body);
      onUpdated(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "保存失败");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!confirm(`确定删除素材「${asset.name}」？此操作不可恢复。`)) return;
    setDeleting(true);
    setError("");
    try {
      await deleteAsset(asset.asset_id);
      onDeleted(asset.asset_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "删除失败");
      setDeleting(false);
    }
  }

  return (
    <div className="dialog-overlay" role="dialog" aria-modal="true" onClick={onClose}>
      <div className="dialog-panel asset-detail-panel" onClick={(e) => e.stopPropagation()}>
        <div className="media-preview-header">
          <div>
            <h2 style={{ marginBottom: 6 }}>{asset.name}</h2>
            <div style={{ color: "var(--muted)", fontSize: "0.9rem" }}>
              {asset.asset_type.toUpperCase()} · {asset.category} ·{" "}
              {new Date(asset.created_at).toLocaleString("zh-CN")}
            </div>
          </div>
          <button className="btn btn-secondary btn-sm" type="button" onClick={onClose}>
            关闭
          </button>
        </div>

        {error && <div className="error-banner" style={{ marginTop: 16 }}>{error}</div>}

        {asset.asset_type === "image" && mediaSrc && (
          <img className="media-preview-img" src={mediaSrc} alt={asset.name} />
        )}
        {asset.asset_type === "video" && mediaSrc && (
          <video className="media-preview-video" src={mediaSrc} controls />
        )}

        {asset.asset_type === "text" && (
          <div style={{ marginTop: 16 }}>
            <div className="form-actions" style={{ paddingTop: 0 }}>
              <button
                className={`btn btn-sm ${mode === "preview" ? "btn-primary" : "btn-secondary"}`}
                type="button"
                onClick={() => setMode("preview")}
              >
                Markdown 预览
              </button>
              <button
                className={`btn btn-sm ${mode === "edit" ? "btn-primary" : "btn-secondary"}`}
                type="button"
                onClick={() => setMode("edit")}
              >
                编辑
              </button>
            </div>
            {mode === "preview" ? (
              <div className="markdown-preview">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{contentText}</ReactMarkdown>
              </div>
            ) : (
              <textarea
                className="form-textarea"
                value={contentText}
                onChange={(e) => setContentText(e.target.value)}
                rows={10}
              />
            )}
          </div>
        )}

        <div className="panel form-stack" style={{ marginTop: 18 }}>
          <div className="form-group">
            <label className="form-label">
              标签{asset.asset_type === "text" ? "（可编辑标签与内容）" : "（仅允许编辑标签）"}
            </label>
            <span className="form-hint">使用逗号或换行分隔</span>
            <textarea
              className="form-textarea"
              value={tagsText}
              onChange={(e) => setTagsText(e.target.value)}
              rows={2}
            />
          </div>

          <div className="form-actions">
            <button className="btn btn-primary" type="button" onClick={handleSave} disabled={saving || deleting}>
              {saving && <span className="spinner" />}
              {saving ? "保存中..." : "保存"}
            </button>
            <button className="btn btn-danger" type="button" onClick={handleDelete} disabled={saving || deleting}>
              {deleting && <span className="spinner" />}
              {deleting ? "删除中..." : "删除"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
