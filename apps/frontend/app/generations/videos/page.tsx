import { AppShell } from "@/components/shell/app-shell";
import { VideoGenForm } from "@/components/generations/video-gen-form";

export default function VideoGenerationPage() {
  return (
    <AppShell
      eyebrow="生成"
      title="视频生成"
      description="支持单视频直出、多段脚本规划，以及异步提交后在记录面板中持续查看生成进度。"
    >
      <VideoGenForm />
    </AppShell>
  );
}
