"use client";

import { useEffect, useState } from "react";
import { listCallLogs, listProviders } from "@/lib/api";
import type {
  CallLogResponse,
  CallLogStatus,
  ProviderResponse,
} from "@/types/api";

const capabilityLabels: Record<string, string> = {
  image: "图片",
  video: "视频",
  text: "文本",
};

export function CallLogList() {
  const [logs, setLogs] = useState<CallLogResponse[]>([]);
  const [providers, setProviders] = useState<ProviderResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  /* filters */
  const [filterProvider, setFilterProvider] = useState("");
  const [filterCapability, setFilterCapability] = useState("");
  const [filterStatus, setFilterStatus] = useState("");

  /* expanded error row */
  const [expandedId, setExpandedId] = useState<string | null>(null);

  async function load() {
    setError("");
    try {
      const params: Record<string, string> = {};
      if (filterProvider) params.provider_id = filterProvider;
      if (filterCapability) params.capability = filterCapability;
      if (filterStatus) params.status = filterStatus;
      const data = await listCallLogs(
        Object.keys(params).length > 0 ? params : undefined
      );
      setLogs(data.items);
    } catch {
      setError("加载调用日志失败");
    } finally {
      setLoading(false);
    }
  }

  async function loadProviders() {
    try {
      const data = await listProviders();
      setProviders(data.items);
    } catch {
      /* ignore */
    }
  }

  useEffect(() => {
    load();
    loadProviders();
  }, []);

  useEffect(() => {
    setLoading(true);
    load();
  }, [filterProvider, filterCapability, filterStatus]);

  if (loading && logs.length === 0) {
    return (
      <div className="gen-empty">
        <span className="spinner spinner-dark" />
        <p>正在加载调用日志...</p>
      </div>
    );
  }

  return (
    <div className="stack-lg">
      {error && <div className="error-banner">{error}</div>}

      <div className="form-row" style={{ gap: "1rem", flexWrap: "wrap" }}>
        <div className="form-group" style={{ minWidth: "160px" }}>
          <label className="form-label">供应商</label>
          <select
            className="form-input"
            value={filterProvider}
            onChange={(e) => setFilterProvider(e.target.value)}
          >
            <option value="">全部</option>
            {providers.map((p) => (
              <option key={p.provider_id} value={p.provider_id}>
                {p.name}
              </option>
            ))}
          </select>
        </div>
        <div className="form-group" style={{ minWidth: "120px" }}>
          <label className="form-label">能力类型</label>
          <select
            className="form-input"
            value={filterCapability}
            onChange={(e) => setFilterCapability(e.target.value)}
          >
            <option value="">全部</option>
            <option value="image">图片</option>
            <option value="video">视频</option>
            <option value="text">文本</option>
          </select>
        </div>
        <div className="form-group" style={{ minWidth: "120px" }}>
          <label className="form-label">状态</label>
          <select
            className="form-input"
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value as CallLogStatus | "")}
          >
            <option value="">全部</option>
            <option value="success">成功</option>
            <option value="error">失败</option>
          </select>
        </div>
      </div>

      {logs.length === 0 ? (
        <div className="gen-empty">
          <div className="gen-empty-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2" />
              <rect x="9" y="3" width="6" height="4" rx="1" />
            </svg>
          </div>
          <p>暂无调用日志</p>
        </div>
      ) : (
        <div className="panel" style={{ overflow: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.9rem" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border, #e0d6cc)" }}>
                <th style={thStyle}>时间</th>
                <th style={thStyle}>供应商</th>
                <th style={thStyle}>模型</th>
                <th style={thStyle}>类型</th>
                <th style={thStyle}>状态</th>
                <th style={thStyle}>耗时</th>
                <th style={thStyle}>令牌用量</th>
                <th style={thStyle}>摘要</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => (
                <LogRow
                  key={log.log_id}
                  log={log}
                  expanded={expandedId === log.log_id}
                  onToggle={() =>
                    setExpandedId(expandedId === log.log_id ? null : log.log_id)
                  }
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

const thStyle: React.CSSProperties = {
  textAlign: "left",
  padding: "0.6rem 0.8rem",
  fontWeight: 600,
  color: "var(--muted)",
  whiteSpace: "nowrap",
};

const tdStyle: React.CSSProperties = {
  padding: "0.6rem 0.8rem",
  verticalAlign: "top",
};

function LogRow({
  log,
  expanded,
  onToggle,
}: {
  log: CallLogResponse;
  expanded: boolean;
  onToggle: () => void;
}) {
  const isError = log.response_status === "error";

  return (
    <>
      <tr
        style={{
          borderBottom: "1px solid var(--border, #e0d6cc)",
          cursor: isError ? "pointer" : "default",
          background: isError ? "rgba(220,60,60,0.04)" : undefined,
        }}
        onClick={isError ? onToggle : undefined}
      >
        <td style={tdStyle}>
          {new Date(log.created_at).toLocaleString("zh-CN", {
            month: "2-digit",
            day: "2-digit",
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
          })}
        </td>
        <td style={tdStyle}>{log.provider_name}</td>
        <td style={tdStyle}>{log.model}</td>
        <td style={tdStyle}>
          <span className={`model-tag`}>
            <span className={`cap-dot cap-${log.capability}`} />
            {capabilityLabels[log.capability] ?? log.capability}
          </span>
        </td>
        <td style={tdStyle}>
          <span
            className="status-pill"
            style={{
              background: isError ? "var(--tone-risk, #dc3c3c)" : "var(--tone-complete, #3aaf5c)",
              color: "#fff",
              fontSize: "0.78rem",
              padding: "0.15rem 0.6rem",
              borderRadius: "999px",
            }}
          >
            {isError ? "失败" : "成功"}
          </span>
        </td>
        <td style={tdStyle}>{log.duration_ms}ms</td>
        <td style={tdStyle}>
          {log.token_usage?.total_tokens != null ? (
            <div style={{ display: "grid", gap: 2 }}>
              <strong style={{ fontSize: "0.86rem" }}>{log.token_usage.total_tokens}</strong>
              <small style={{ color: "var(--muted)" }}>
                输入 {log.token_usage.prompt_tokens ?? 0} / 输出 {log.token_usage.completion_tokens ?? 0}
              </small>
            </div>
          ) : (
            <span style={{ color: "var(--muted)" }}>-</span>
          )}
        </td>
        <td style={{ ...tdStyle, maxWidth: "200px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {log.request_body_summary}
        </td>
      </tr>
      {expanded && isError && log.error_detail && (
        <tr>
          <td colSpan={8} style={{ padding: "0.8rem 1.2rem", background: "rgba(220,60,60,0.06)" }}>
            <div style={{ fontFamily: "monospace", fontSize: "0.82rem", whiteSpace: "pre-wrap", color: "var(--tone-risk, #dc3c3c)" }}>
              {log.error_detail}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}
