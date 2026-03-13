import { AppShell } from "@/components/shell/app-shell";
import { AssetBrowser } from "@/components/assets/asset-browser";

export default function AssetsPage() {
  return (
    <AppShell
      eyebrow="资源库"
      title="素材"
      description="浏览与筛选所有生成的素材，以及手动上传的媒体内容。"
    >
      <AssetBrowser />
    </AppShell>
  );
}
