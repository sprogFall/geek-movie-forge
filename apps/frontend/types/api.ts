export type ModelCapability = "text" | "image" | "video";
export type AssetType = "image" | "video" | "text";
export type AssetOrigin = "manual" | "generated";
export type TaskStatus =
  | "draft"
  | "queued"
  | "processing"
  | "waiting_review"
  | "completed"
  | "failed";

/* ── Auth ── */

export type UserResponse = {
  user_id: string;
  username: string;
  created_at: string;
};

export type TokenResponse = {
  access_token: string;
  token_type: string;
  user: UserResponse;
};

/* ── Provider ── */

export type ModelEntry = {
  model: string;
  capabilities: ModelCapability[];
  label: string | null;
};

export type RouteConfig = {
  path: string;
  timeout_seconds: number;
};

export type ProviderRoutes = {
  text?: RouteConfig;
  image?: RouteConfig;
  video?: RouteConfig;
};

export type ProviderResponse = {
  provider_id: string;
  name: string;
  base_url: string;
  api_key_masked: string;
  adapter_type: string;
  models: ModelEntry[];
  routes: ProviderRoutes;
  created_at: string;
  updated_at: string;
};

export type ProviderListResponse = {
  items: ProviderResponse[];
};

/* ── Asset ── */

export type AssetResponse = {
  asset_id: string;
  asset_type: AssetType;
  category: string;
  name: string;
  origin: AssetOrigin;
  content_url: string | null;
  content_text: string | null;
  content_base64: string | null;
  mime_type: string | null;
  tags: string[];
  metadata: Record<string, unknown>;
  provider_id: string | null;
  model: string | null;
  created_at: string;
};

export type AssetListResponse = {
  items: AssetResponse[];
};

/* ── Generation ── */

export type MediaOutput = {
  index: number;
  url: string | null;
  base64_data: string | null;
  mime_type: string | null;
  text: string | null;
  cover_image_url: string | null;
  duration_seconds: number | null;
  metadata: Record<string, unknown>;
};

export type MediaGenerationResponse = {
  generation_id: string;
  capability: "image" | "video";
  provider_id: string;
  model: string;
  resolved_prompt: string;
  provider_request_id: string | null;
  outputs: MediaOutput[];
  saved_assets: AssetResponse[];
};

export type TextGenerationResponse = {
  generation_id: string;
  capability: "text";
  provider_id: string;
  model: string;
  task_type: string;
  source_text: string;
  resolved_prompt: string | null;
  provider_request_id: string | null;
  output_text: string;
  saved_assets: AssetResponse[];
};

export type AssetSaveOptions = {
  enabled: boolean;
  category?: string;
  name_prefix?: string;
  tags?: string[];
};

/* 鈹€鈹€ Projects 鈹€鈹€ */

export type ProjectStatus = "draft" | "active" | "review" | "completed" | "archived";

export type ProjectCreateRequest = {
  title: string;
  summary: string;
  platform: string;
  aspect_ratio: string;
  status?: ProjectStatus;
};

export type ProjectResponse = {
  project_id: string;
  title: string;
  summary: string;
  platform: string;
  aspect_ratio: string;
  status: ProjectStatus;
  created_at: string;
  updated_at: string;
};

export type ProjectListResponse = {
  items: ProjectResponse[];
};

/* 鈹€鈹€ Tasks 鈹€鈹€ */

export type TaskCreateRequest = {
  project_id: string;
  title: string;
  source_text: string;
  platform: string;
};

export type TaskResponse = {
  task_id: string;
  project_id: string;
  title: string;
  source_text: string;
  platform: string;
  status: TaskStatus;
  created_at: string;
};

export type TaskListResponse = {
  items: TaskResponse[];
};

/* -- Call Logs -- */

export type CallLogStatus = "success" | "error";

export type CallLogResponse = {
  log_id: string;
  provider_id: string;
  provider_name: string;
  model: string;
  capability: string;
  request_body_summary: string;
  response_status: CallLogStatus;
  error_detail: string | null;
  duration_ms: number;
  created_at: string;
};

export type CallLogListResponse = {
  items: CallLogResponse[];
};
