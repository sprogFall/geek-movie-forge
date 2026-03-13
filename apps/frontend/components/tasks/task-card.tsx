import { StatusPill } from "@/components/ui/status-pill";
import { TaskSummary } from "@/types/console";

type TaskCardProps = {
  task: TaskSummary;
};

export function TaskCard({ task }: TaskCardProps) {
  return (
    <article className="task-card">
      <div className="task-card-header">
        <div>
          <h3>{task.title}</h3>
          <p>{task.summary}</p>
        </div>
        <StatusPill status={task.status} />
      </div>

      <div className="meta-row">
        <span className="meta-pill">{task.queue}</span>
        <span className="meta-pill">{task.provider}</span>
        <span className="meta-pill">{task.project}</span>
      </div>
    </article>
  );
}
