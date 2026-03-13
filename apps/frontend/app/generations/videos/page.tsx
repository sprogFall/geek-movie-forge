import { AppShell } from "@/components/shell/app-shell";
import { VideoGenForm } from "@/components/generations/video-gen-form";

export default function VideoGenerationPage() {
  return (
    <AppShell
      eyebrow="生成"
      title="视频生成"
      description="根据提示词生成视频片段，可选填参考图片。"
    >
      <VideoGenForm />
    </AppShell>
  );
}
