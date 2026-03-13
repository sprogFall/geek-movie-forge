import { MetricCardModel } from "@/types/console";

type MetricCardProps = {
  metric: MetricCardModel;
};

export function MetricCard({ metric }: MetricCardProps) {
  return (
    <article className="metric-card">
      <span>{metric.label}</span>
      <strong>{metric.value}</strong>
      <small>{metric.footnote}</small>
    </article>
  );
}
