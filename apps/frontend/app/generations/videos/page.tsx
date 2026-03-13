import { AppShell } from "@/components/shell/app-shell";
import { VideoGenForm } from "@/components/generations/video-gen-form";

export default function VideoGenerationPage() {
  return (
    <AppShell
      eyebrow="Generation"
      title="Video generation"
      description="Generate video clips from prompts and optional reference images."
    >
      <VideoGenForm />
    </AppShell>
  );
}
