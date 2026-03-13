import { MetricCardModel, ProjectSummary, TaskSummary } from "@/types/console";

export const metrics: MetricCardModel[] = [
  { label: "Live projects", value: "12", footnote: "3 waiting for review" },
  { label: "Queued jobs", value: "41", footnote: "image and render dominant" },
  { label: "Average cycle", value: "27m", footnote: "from brief to delivery" },
  { label: "Recovery alerts", value: "2", footnote: "watchdog candidates" },
];

export const projects: ProjectSummary[] = [
  {
    id: "proj-mars-echo",
    title: "Mars Echo teaser",
    summary: "Sci-fi narration package with bilingual subtitles and platform-specific exports.",
    status: "review",
    platform: "Douyin",
    aspectRatio: "9:16",
    owner: "Content Ops",
    revisionLabel: "Revision 4",
    lastTouched: "12 min ago",
  },
  {
    id: "proj-neon-fable",
    title: "Neon Fable recap",
    summary: "Fast-cut recap designed for Xiaohongshu and Reels with bright caption language.",
    status: "processing",
    platform: "Xiaohongshu",
    aspectRatio: "4:5",
    owner: "Growth Studio",
    revisionLabel: "Revision 2",
    lastTouched: "34 min ago",
  },
  {
    id: "proj-citadel-signal",
    title: "Citadel Signal promo",
    summary: "Dialog-driven promo spot with voice cloning and three trailer variants.",
    status: "completed",
    platform: "Instagram Reels",
    aspectRatio: "9:16",
    owner: "Brand Team",
    revisionLabel: "Approved master",
    lastTouched: "2 h ago",
  },
];

export const tasks: TaskSummary[] = [
  {
    id: "task-img-001",
    title: "Storyboard keyframe batch",
    summary: "Waiting on image provider callbacks for scenes 04-08.",
    status: "processing",
    queue: "queue:image",
    provider: "image-alpha",
    project: "Mars Echo teaser",
  },
  {
    id: "task-rnd-002",
    title: "Final vertical render",
    summary: "Primary composition completed, export package entering QA review.",
    status: "review",
    queue: "queue:render",
    provider: "remotion",
    project: "Neon Fable recap",
  },
  {
    id: "task-tts-003",
    title: "Voice pack synthesis",
    summary: "Background mix normalization failed once and needs retry policy review.",
    status: "risk",
    queue: "queue:voice",
    provider: "voice-beta",
    project: "Citadel Signal promo",
  },
  {
    id: "task-pub-004",
    title: "Publishing callback",
    summary: "All assets landed successfully and webhook callback is complete.",
    status: "completed",
    queue: "queue:publish",
    provider: "n8n",
    project: "Mars Echo teaser",
  },
];
