import { StatusPill } from "@/components/ui/status-pill";
import type { ProjectResponse } from "@/types/api";

type ProjectCardProps = {
  project: ProjectResponse;
  compact?: boolean;
};

export function ProjectCard({ project, compact = false }: ProjectCardProps) {
  const updatedAtLabel = project.updated_at
    ? new Date(project.updated_at).toLocaleString("zh-CN")
    : "";

  return (
    <article className="project-card">
      <div className="project-card-header">
        <div>
          <h3>{project.title}</h3>
          <p>{project.summary}</p>
        </div>
        <StatusPill status={project.status} />
      </div>

      <div className="meta-row">
        <span className="meta-pill">平台：{project.platform}</span>
        <span className="meta-pill">比例：{project.aspect_ratio}</span>
        {updatedAtLabel ? <span className="meta-pill">更新：{updatedAtLabel}</span> : null}
      </div>

      {!compact ? (
        <div className="meta-row">
          <span className="meta-pill">项目ID：{project.project_id}</span>
        </div>
      ) : null}
    </article>
  );
}
