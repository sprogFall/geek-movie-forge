export type MetricCardModel = {
  label: string;
  value: string;
  footnote: string;
};

export type ProjectSummary = {
  id: string;
  title: string;
  summary: string;
  status: string;
  platform: string;
  aspectRatio: string;
  owner: string;
  revisionLabel: string;
  lastTouched: string;
};

export type TaskSummary = {
  id: string;
  title: string;
  summary: string;
  status: string;
  queue: string;
  provider: string;
  project: string;
};
