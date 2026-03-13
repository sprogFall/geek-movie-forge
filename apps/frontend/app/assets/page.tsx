import { AppShell } from "@/components/shell/app-shell";
import { AssetBrowser } from "@/components/assets/asset-browser";

export default function AssetsPage() {
  return (
    <AppShell
      eyebrow="Library"
      title="Assets"
      description="Browse and filter all generated and manually uploaded media assets."
    >
      <AssetBrowser />
    </AppShell>
  );
}
