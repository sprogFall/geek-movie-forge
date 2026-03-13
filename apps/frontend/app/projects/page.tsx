import { ProjectCard } from "@/components/projects/project-card";
import { AppShell } from "@/components/shell/app-shell";
import { projects } from "@/lib/mock-data";

export default function ProjectsPage() {
  return (
    <AppShell
      eyebrow="Projects"
      title="Project pipeline"
      description="Track story packages, revision pressure and publishing readiness across every workspace."
    >
      <section className="card-grid">
        {projects.map((project) => (
          <ProjectCard key={project.id} project={project} />
        ))}
      </section>
    </AppShell>
  );
}
