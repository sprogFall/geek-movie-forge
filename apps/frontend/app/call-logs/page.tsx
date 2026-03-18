import { AppShell } from "@/components/shell/app-shell";
import { CallLogList } from "@/components/call-logs/call-log-list";

export default function CallLogsPage() {
  return (
    <AppShell
      eyebrow="资源库"
      title="调用日志"
      description="查看 AI 供应商调用记录、错误详情与每次调用的 Token 消耗。"
    >
      <CallLogList />
    </AppShell>
  );
}
