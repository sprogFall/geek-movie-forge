import { AppShell } from "@/components/shell/app-shell";
import { ImageGenForm } from "@/components/generations/image-gen-form";

export default function ImageGenerationPage() {
  return (
    <AppShell
      eyebrow="Generation"
      title="Image generation"
      description="Generate images from text prompts using configured AI providers."
    >
      <ImageGenForm />
    </AppShell>
  );
}
