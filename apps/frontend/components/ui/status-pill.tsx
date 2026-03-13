type StatusPillProps = {
  status: string;
};

const toneMap: Record<string, string> = {
  draft: "tone-processing",
  queued: "tone-review",
  processing: "tone-processing",
  waiting_review: "tone-review",
  review: "tone-review",
  completed: "tone-complete",
  failed: "tone-risk",
  risk: "tone-risk",
  active: "tone-processing",
  archived: "tone-review",
};

export function StatusPill({ status }: StatusPillProps) {
  const tone = toneMap[status] ?? "tone-processing";
  const labelMap: Record<string, string> = {
    draft: "草稿",
    queued: "排队中",
    processing: "处理中",
    waiting_review: "待审核",
    review: "审核中",
    completed: "已完成",
    failed: "失败",
    risk: "风险",
    active: "进行中",
    archived: "已归档",
  };
  const label = labelMap[status] ?? status;

  return <span className={`status-pill ${tone}`}>{label}</span>;
}
