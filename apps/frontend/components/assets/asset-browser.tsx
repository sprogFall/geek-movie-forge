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
      setError("Failed to load assets");
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

  return (
    <div className="stack-lg">
      {error && <div className="error-banner">{error}</div>}

      <div className="filter-bar">
        <select
          className="form-select"
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value as AssetType | "")}
        >
          <option value="">All types</option>
          <option value="image">Image</option>
          <option value="video">Video</option>
          <option value="text">Text</option>
        </select>
        <select
          className="form-select"
          value={originFilter}
          onChange={(e) => setOriginFilter(e.target.value as AssetOrigin | "")}
        >
          <option value="">All origins</option>
          <option value="generated">Generated</option>
          <option value="manual">Manual</option>
        </select>
        <span style={{ marginLeft: "auto", color: "var(--muted)", fontSize: "0.88rem" }}>
          {assets.length} asset{assets.length !== 1 ? "s" : ""}
        </span>
      </div>

      {loading ? (
        <div className="gen-empty">
          <span className="spinner spinner-dark" />
          <p>Loading assets...</p>
        </div>
      ) : assets.length === 0 ? (
        <div className="gen-empty">
          <div className="gen-empty-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z" />
            </svg>
          </div>
          <p>No assets found</p>
        </div>
      ) : (
        <div className="asset-gallery">
          {assets.map((asset) => (
            <article key={asset.asset_id} className="asset-card">
              {renderThumb(asset)}
              <div className="asset-info">
                <h4>{asset.name}</h4>
                <div className="asset-info-meta">
                  <span className="tag-pill">{asset.asset_type}</span>
                  <span className="tag-pill">{asset.origin}</span>
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
