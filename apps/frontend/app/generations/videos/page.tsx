import { AppShell } from "@/components/shell/app-shell";
import { VideoGenForm } from "@/components/generations/video-gen-form";

export default function VideoGenerationPage() {
  return (
    <AppShell
      eyebrow="生成"
      title="视频生成"
      description="支持单视频直出，也支持先规划多段脚本后并行生成多条视频。"
    >
      <VideoGenForm />
    </AppShell>
  );
}
