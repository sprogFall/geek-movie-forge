import { MetricCard } from "@/components/dashboard/metric-card";
import { ProjectCard } from "@/components/projects/project-card";
import { AppShell } from "@/components/shell/app-shell";
import { TaskCard } from "@/components/tasks/task-card";
import { metrics, projects, tasks } from "@/lib/mock-data";

export default function HomePage() {
  return (
    <AppShell
      eyebrow="Overview"
      title="Production console"
      description="Monitor active jobs, inspect projects and keep the video pipeline moving from script to publish."
    >
      <section className="stack-lg">
        <div className="metric-grid">
          {metrics.map((metric) => (
            <MetricCard key={metric.label} metric={metric} />
          ))}
        </div>

        <div className="content-grid">
          <section className="panel stack-md">
            <div className="section-heading">
              <div>
                <p className="eyebrow">High priority</p>
                <h2>Active tasks</h2>
              </div>
            </div>
            <div className="stack-sm">
              {tasks.slice(0, 3).map((task) => (
                <TaskCard key={task.id} task={task} />
              ))}
            </div>
          </section>

          <section className="panel stack-md">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Recently touched</p>
                <h2>Projects</h2>
              </div>
            </div>
            <div className="stack-sm">
              {projects.slice(0, 2).map((project) => (
                <ProjectCard key={project.id} project={project} compact />
              ))}
            </div>
          </section>
        </div>
      </section>
    </AppShell>
  );
}
