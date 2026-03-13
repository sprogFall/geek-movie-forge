import { StatusPill } from "@/components/ui/status-pill";
import { ProjectSummary } from "@/types/console";

type ProjectCardProps = {
  project: ProjectSummary;
  compact?: boolean;
};

export function ProjectCard({ project, compact = false }: ProjectCardProps) {
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
        <span className="meta-pill">{project.platform}</span>
        <span className="meta-pill">{project.aspectRatio}</span>
        <span className="meta-pill">{project.lastTouched}</span>
      </div>

      {!compact ? (
        <div className="meta-row">
          <span className="meta-pill">{project.owner}</span>
          <span className="meta-pill">{project.revisionLabel}</span>
        </div>
      ) : null}
    </article>
  );
}
