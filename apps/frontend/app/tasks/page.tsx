"use client";

import { useEffect, useState } from "react";

import { AppShell } from "@/components/shell/app-shell";
import { TaskCard } from "@/components/tasks/task-card";
import { createTask, listProjects, listTasks } from "@/lib/api";
import type { ProjectResponse, TaskResponse } from "@/types/api";

export default function TasksPage() {
  const [tasks, setTasks] = useState<TaskResponse[]>([]);
  const [projects, setProjects] = useState<ProjectResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  /* form state */
  const [projectId, setProjectId] = useState("");
  const [title, setTitle] = useState("");
  const [platform, setPlatform] = useState("douyin");
  const [sourceText, setSourceText] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function load() {
    setLoading(true);
    setError("");
    try {
      const [taskData, projectData] = await Promise.all([listTasks(), listProjects()]);
      setTasks(taskData.items);
      setProjects(projectData.items);
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
      await createTask({
        project_id: projectId,
        title,
        platform,
        source_text: sourceText,
      });
      setTitle("");
      setSourceText("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "创建任务失败");
    } finally {
      setSubmitting(false);
    }
  }

  const hasProjects = projects.length > 0;

  return (
    <AppShell
      eyebrow="任务"
      title="任务队列"
      description="创建并查看当前账号下的任务列表。"
    >
      <div className="stack-lg">
        {error && <div className="error-banner">{error}</div>}

        <form className="panel form-stack" onSubmit={handleSubmit}>
          <div className="section-heading">
            <div>
              <p className="eyebrow">新建</p>
              <h2>创建任务</h2>
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label className="form-label">所属项目</label>
              <select
                className="form-select"
                value={projectId}
                onChange={(e) => setProjectId(e.target.value)}
                required
              >
                <option value="">{hasProjects ? "请选择项目..." : "暂无项目，请先创建项目"}</option>
                {projects.map((p) => (
                  <option key={p.project_id} value={p.project_id}>
                    {p.title}
                  </option>
                ))}
              </select>
            </div>

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
          </div>

          <div className="form-group">
            <label className="form-label">任务标题</label>
            <input
              className="form-input"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="例如：生成第 1 版脚本"
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label">源文本/素材</label>
            <textarea
              className="form-textarea"
              value={sourceText}
              onChange={(e) => setSourceText(e.target.value)}
              placeholder="粘贴素材或说明，例如：剧情概要、镜头清单、风格要求等..."
              rows={4}
              required
            />
          </div>

          <div className="form-actions">
            <button
              className="btn btn-primary"
              type="submit"
              disabled={submitting || !hasProjects}
              title={!hasProjects ? "请先创建项目" : undefined}
            >
              {submitting && <span className="spinner" />}
              {submitting ? "创建中..." : "创建任务"}
            </button>
          </div>
        </form>

        {loading ? (
          <div className="gen-empty">
            <span className="spinner spinner-dark" />
            <p>正在加载任务...</p>
          </div>
        ) : tasks.length === 0 ? (
          <div className="gen-empty">
            <div className="gen-empty-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M9 11l3 3L22 4" />
                <path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11" />
              </svg>
            </div>
            <p>暂无任务</p>
          </div>
        ) : (
          <section className="stack-sm">
            {tasks.map((task) => (
              <TaskCard key={task.task_id} task={task} />
            ))}
          </section>
        )}
      </div>
    </AppShell>
  );
}
