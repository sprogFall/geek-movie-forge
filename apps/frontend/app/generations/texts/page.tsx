import { AppShell } from "@/components/shell/app-shell";
import { TextGenForm } from "@/components/generations/text-gen-form";

export default function TextGenerationPage() {
  return (
    <AppShell
      eyebrow="生成"
      title="文本生成"
      description="根据素材生成脚本、字幕与文案等文本内容。"
    >
      <TextGenForm />
    </AppShell>
  );
}
