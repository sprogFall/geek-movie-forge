"use client";

import { useEffect, useState } from "react";

import { ProjectCard } from "@/components/projects/project-card";
import { AppShell } from "@/components/shell/app-shell";
import { createProject, listProjects } from "@/lib/api";
import type { ProjectResponse, ProjectStatus } from "@/types/api";

export default function ProjectsPage() {
  const [projects, setProjects] = useState<ProjectResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);

  /* form state */
  const [title, setTitle] = useState("");
  const [summary, setSummary] = useState("");
  const [platform, setPlatform] = useState("douyin");
  const [aspectRatio, setAspectRatio] = useState("9:16");
  const [status, setStatus] = useState<ProjectStatus>("active");
  const [submitting, setSubmitting] = useState(false);

  async function load() {
    setLoading(true);
    setError("");
    try {
      const data = await listProjects();
      setProjects(data.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      await createProject({
        title,
        summary,
        platform,
        aspect_ratio: aspectRatio,
        status,
      });
      setTitle("");
      setSummary("");
      setPlatform("douyin");
      setAspectRatio("9:16");
      setStatus("active");
      setShowForm(false);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "创建项目失败");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AppShell
      eyebrow="项目"
      title="项目流水线"
      description="创建项目，并跟踪不同平台的制作进度。"
    >
      <div className="stack-lg">
        {error && <div className="error-banner">{error}</div>}

        <div className="form-actions">
          <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>
            {showForm ? "取消" : "新建项目"}
          </button>
        </div>

        {showForm && (
          <form className="panel form-stack" onSubmit={handleSubmit}>
            <div className="form-group">
              <label className="form-label">项目标题</label>
              <input
                className="form-input"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="例如：科幻解说合集"
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">项目简介</label>
              <textarea
                className="form-textarea"
                value={summary}
                onChange={(e) => setSummary(e.target.value)}
                placeholder="一句话说明项目内容、风格、输出规格等..."
                rows={3}
                required
              />
            </div>

            <div className="form-row">
              <div className="form-group">
                <label className="form-label">平台</label>
                <select
                  className="form-select"
                  value={platform}
                  onChange={(e) => setPlatform(e.target.value)}
                >
                  <option value="douyin">抖音</option>
                  <option value="xiaohongshu">小红书</option>
                  <option value="bilibili">B 站</option>
                  <option value="youtube">YouTube</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">画面比例</label>
                <select
                  className="form-select"
                  value={aspectRatio}
                  onChange={(e) => setAspectRatio(e.target.value)}
                >
                  <option value="9:16">9:16（竖屏）</option>
                  <option value="16:9">16:9（横屏）</option>
                  <option value="1:1">1:1</option>
                  <option value="4:5">4:5</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">状态</label>
                <select
                  className="form-select"
                  value={status}
                  onChange={(e) => setStatus(e.target.value as ProjectStatus)}
                >
                  <option value="active">进行中</option>
                  <option value="review">审核中</option>
                  <option value="completed">已完成</option>
                  <option value="draft">草稿</option>
                  <option value="archived">已归档</option>
                </select>
              </div>
            </div>

            <div className="form-actions">
              <button className="btn btn-primary" type="submit" disabled={submitting}>
                {submitting && <span className="spinner" />}
                {submitting ? "创建中..." : "创建项目"}
              </button>
            </div>
          </form>
        )}

        {loading ? (
          <div className="gen-empty">
            <span className="spinner spinner-dark" />
            <p>正在加载项目...</p>
          </div>
        ) : projects.length === 0 ? (
          <div className="gen-empty">
            <div className="gen-empty-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z" />
              </svg>
            </div>
            <p>暂无项目</p>
          </div>
        ) : (
          <section className="card-grid">
            {projects.map((project) => (
              <ProjectCard key={project.project_id} project={project} />
            ))}
          </section>
        )}
      </div>
    </AppShell>
  );
}
