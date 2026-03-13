import { AppShell } from "@/components/shell/app-shell";
import { TextGenForm } from "@/components/generations/text-gen-form";

export default function TextGenerationPage() {
  return (
    <AppShell
      eyebrow="Generation"
      title="Text generation"
      description="Generate scripts, captions and copy from source material."
    >
      <TextGenForm />
    </AppShell>
  );
}
