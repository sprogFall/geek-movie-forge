type StatusPillProps = {
  status: string;
};

const toneMap: Record<string, string> = {
  processing: "tone-processing",
  review: "tone-review",
  completed: "tone-complete",
  risk: "tone-risk",
};

export function StatusPill({ status }: StatusPillProps) {
  const tone = toneMap[status] ?? "tone-processing";

  return <span className={`status-pill ${tone}`}>{status}</span>;
}
