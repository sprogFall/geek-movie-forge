import { AppShell } from "@/components/shell/app-shell";
import { ProviderManager } from "@/components/providers/provider-manager";

export default function ProvidersPage() {
  return (
    <AppShell
      eyebrow="Library"
      title="Providers"
      description="Configure AI model providers and manage API connections."
    >
      <ProviderManager />
    </AppShell>
  );
}
