import { StatusPill } from "@/components/ui/status-pill";
import type { TaskResponse } from "@/types/api";

type TaskCardProps = {
  task: TaskResponse;
};

export function TaskCard({ task }: TaskCardProps) {
  const summary =
    task.source_text.length > 120 ? `${task.source_text.slice(0, 120)}...` : task.source_text;
  const createdAtLabel = task.created_at
    ? new Date(task.created_at).toLocaleString("zh-CN")
    : "";

  return (
    <article className="task-card">
      <div className="task-card-header">
        <div>
          <h3>{task.title}</h3>
          <p>{summary}</p>
        </div>
        <StatusPill status={task.status} />
      </div>

      <div className="meta-row">
        <span className="meta-pill">项目：{task.project_id}</span>
        <span className="meta-pill">平台：{task.platform}</span>
        {createdAtLabel ? <span className="meta-pill">创建：{createdAtLabel}</span> : null}
      </div>
    </article>
  );
}
