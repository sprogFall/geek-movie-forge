"use client";

import { useEffect, useState } from "react";

import { MetricCard } from "@/components/dashboard/metric-card";
import { ProjectCard } from "@/components/projects/project-card";
import { AppShell } from "@/components/shell/app-shell";
import { TaskCard } from "@/components/tasks/task-card";
import { listAssets, listProjects, listProviders, listTasks } from "@/lib/api";
import type { AssetResponse, ProjectResponse, ProviderResponse, TaskResponse } from "@/types/api";
import type { MetricCardModel } from "@/types/console";

function buildMetrics(
  projects: ProjectResponse[],
  tasks: TaskResponse[],
  assets: AssetResponse[],
  providers: ProviderResponse[]
): MetricCardModel[] {
  const projectActive = projects.filter((p) => p.status === "active").length;
  const taskDraft = tasks.filter((t) => t.status === "draft").length;
  const assetGenerated = assets.filter((a) => a.origin === "generated").length;
  const modelCount = providers.reduce((acc, p) => acc + p.models.length, 0);

  return [
    {
      label: "项目数",
      value: String(projects.length),
      footnote: `进行中 ${projectActive}`,
    },
    {
      label: "任务数",
      value: String(tasks.length),
      footnote: `草稿 ${taskDraft}`,
    },
    {
      label: "素材数",
      value: String(assets.length),
      footnote: `生成 ${assetGenerated}`,
    },
    {
      label: "供应商",
      value: String(providers.length),
      footnote: `模型 ${modelCount}`,
    },
  ];
}

export default function HomePage() {
  const [metrics, setMetrics] = useState<MetricCardModel[]>([]);
  const [tasks, setTasks] = useState<TaskResponse[]>([]);
  const [projects, setProjects] = useState<ProjectResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      const results = await Promise.allSettled([
        listTasks(),
        listProjects(),
        listAssets(),
        listProviders(),
      ]);

      const extract = <T,>(r: PromiseSettledResult<{ items?: T[] }>): T[] =>
        r.status === "fulfilled" ? r.value.items ?? [] : [];
      const nextTasks = extract<TaskResponse>(results[0] as PromiseSettledResult<{ items?: TaskResponse[] }>);
      const nextProjects = extract<ProjectResponse>(results[1] as PromiseSettledResult<{ items?: ProjectResponse[] }>);
      const nextAssets = extract<AssetResponse>(results[2] as PromiseSettledResult<{ items?: AssetResponse[] }>);
      const nextProviders = extract<ProviderResponse>(results[3] as PromiseSettledResult<{ items?: ProviderResponse[] }>);

      setTasks(nextTasks);
      setProjects(nextProjects);
      setMetrics(buildMetrics(nextProjects, nextTasks, nextAssets, nextProviders));

      const anyFailed = results.some((r) => r.status === "rejected");
      if (anyFailed) setError("部分数据加载失败，显示可能不完整");
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  const recentTasks = [...tasks]
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 3);
  const recentProjects = [...projects]
    .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
    .slice(0, 2);

  return (
    <AppShell
      eyebrow="总览"
      title="制作控制台"
      description="查看项目与任务概览，保持制作流水线从脚本到发布顺畅推进。"
    >
      <section className="stack-lg">
        {error && <div className="error-banner">{error}</div>}

        <div className="metric-grid">
          {metrics.map((metric) => (
            <MetricCard key={metric.label} metric={metric} />
          ))}
        </div>

        {loading ? (
          <div className="gen-empty">
            <span className="spinner spinner-dark" />
            <p>正在加载数据...</p>
          </div>
        ) : (
          <div className="content-grid">
            <section className="panel stack-md">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">重点</p>
                  <h2>最近任务</h2>
                </div>
              </div>
              <div className="stack-sm">
                {recentTasks.length === 0 ? (
                  <div className="gen-empty">
                    <p>暂无任务</p>
                  </div>
                ) : (
                  recentTasks.map((task) => <TaskCard key={task.task_id} task={task} />)
                )}
              </div>
            </section>

            <section className="panel stack-md">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">近期</p>
                  <h2>项目</h2>
                </div>
              </div>
              <div className="stack-sm">
                {recentProjects.length === 0 ? (
                  <div className="gen-empty">
                    <p>暂无项目</p>
                  </div>
                ) : (
                  recentProjects.map((project) => (
                    <ProjectCard key={project.project_id} project={project} compact />
                  ))
                )}
              </div>
            </section>
          </div>
        )}
      </section>
    </AppShell>
  );
}
