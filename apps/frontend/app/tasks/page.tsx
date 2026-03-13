import { AppShell } from "@/components/shell/app-shell";
import { TaskCard } from "@/components/tasks/task-card";
import { tasks } from "@/lib/mock-data";

export default function TasksPage() {
  return (
    <AppShell
      eyebrow="Tasks"
      title="Execution queue"
      description="See which scene, render and voice jobs need attention before they become delivery risks."
    >
      <section className="stack-sm">
        {tasks.map((task) => (
          <TaskCard key={task.id} task={task} />
        ))}
      </section>
    </AppShell>
  );
}
