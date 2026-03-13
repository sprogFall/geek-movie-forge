"use client";

import { useEffect, useState } from "react";
import { listAssets } from "@/lib/api";
import type { AssetResponse, AssetType, AssetOrigin } from "@/types/api";

export function AssetBrowser() {
  const [assets, setAssets] = useState<AssetResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [typeFilter, setTypeFilter] = useState<AssetType | "">("");
  const [originFilter, setOriginFilter] = useState<AssetOrigin | "">("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      const params: Record<string, string> = {};
      if (typeFilter) params.asset_type = typeFilter;
      if (originFilter) params.origin = originFilter;
      const data = await listAssets(params);
      setAssets(data.items);
    } catch {
      setError("加载素材失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [typeFilter, originFilter]);

  function renderThumb(asset: AssetResponse) {
    if (asset.asset_type === "image") {
      if (asset.content_url) {
        return <img className="asset-thumb" src={asset.content_url} alt={asset.name} />;
      }
      if (asset.content_base64) {
        return (
          <img
            className="asset-thumb"
            src={`data:${asset.mime_type ?? "image/png"};base64,${asset.content_base64}`}
            alt={asset.name}
          />
        );
      }
    }
    if (asset.asset_type === "video" && asset.content_url) {
      return <video className="asset-thumb" src={asset.content_url} />;
    }
    if (asset.asset_type === "text") {
      return (
        <div className="asset-text-thumb">
          {(asset.content_text ?? "").slice(0, 120)}
          {(asset.content_text ?? "").length > 120 ? "..." : ""}
        </div>
      );
    }
    return (
      <div className="asset-text-thumb">
        <svg
          width="32"
          height="32"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
        >
          <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
          <path d="M14 2v6h6" />
        </svg>
      </div>
    );
  }

  const typeLabels: Record<AssetType, string> = {
    image: "图片",
    video: "视频",
    text: "文本",
  };
  const originLabels: Record<AssetOrigin, string> = {
    generated: "生成",
    manual: "手动",
  };

  return (
    <div className="stack-lg">
      {error && <div className="error-banner">{error}</div>}

      <div className="filter-bar">
        <select
          className="form-select"
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value as AssetType | "")}
        >
          <option value="">全部类型</option>
          <option value="image">图片</option>
          <option value="video">视频</option>
          <option value="text">文本</option>
        </select>
        <select
          className="form-select"
          value={originFilter}
          onChange={(e) => setOriginFilter(e.target.value as AssetOrigin | "")}
        >
          <option value="">全部来源</option>
          <option value="generated">生成</option>
          <option value="manual">手动上传</option>
        </select>
        <span style={{ marginLeft: "auto", color: "var(--muted)", fontSize: "0.88rem" }}>
          共 {assets.length} 个素材
        </span>
      </div>

      {loading ? (
        <div className="gen-empty">
          <span className="spinner spinner-dark" />
          <p>正在加载素材...</p>
        </div>
      ) : assets.length === 0 ? (
        <div className="gen-empty">
          <div className="gen-empty-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z" />
            </svg>
          </div>
          <p>未找到素材</p>
        </div>
      ) : (
        <div className="asset-gallery">
          {assets.map((asset) => (
            <article key={asset.asset_id} className="asset-card">
              {renderThumb(asset)}
              <div className="asset-info">
                <h4>{asset.name}</h4>
                <div className="asset-info-meta">
                  <span className="tag-pill">{typeLabels[asset.asset_type]}</span>
                  <span className="tag-pill">{originLabels[asset.origin]}</span>
                  {asset.category && <span className="tag-pill">{asset.category}</span>}
                </div>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
