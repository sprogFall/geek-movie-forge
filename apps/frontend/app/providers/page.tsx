import { AppShell } from "@/components/shell/app-shell";
import { ProviderManager } from "@/components/providers/provider-manager";

export default function ProvidersPage() {
  return (
    <AppShell
      eyebrow="资源库"
      title="供应商"
      description="配置 AI 模型供应商并管理 API 连接。"
    >
      <ProviderManager />
    </AppShell>
  );
}
