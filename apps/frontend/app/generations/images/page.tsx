import { AppShell } from "@/components/shell/app-shell";
import { ImageGenForm } from "@/components/generations/image-gen-form";

export default function ImageGenerationPage() {
  return (
    <AppShell
      eyebrow="生成"
      title="图片生成"
      description="使用已配置的 AI 模型供应商，根据提示词生成图片。"
    >
      <ImageGenForm />
    </AppShell>
  );
}
