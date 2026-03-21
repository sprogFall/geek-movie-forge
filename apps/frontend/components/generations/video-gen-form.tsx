"use client";

import { useEffect, useRef, useState } from "react";
import {
  createAsset,
  generateMultiVideos,
  regenerateMultiVideoSegment,
  generateVideos,
  listAssets,
  listProviders,
  planMultiVideos,
} from "@/lib/api";
import { formatElapsed, useElapsedMs } from "@/lib/elapsed";
import type {
  AssetResponse,
  MediaGenerationResponse,
  MultiVideoGenerationResponse,
  MultiVideoPlanResponse,
  MultiVideoSegmentGenerationResult,
  ProviderResponse,
  VideoSegmentPlan,
} from "@/types/api";

type GenerationMode = "single" | "multi";

type PreviewState = {
  src: string;
  poster?: string | null;
  title: string;
} | null;

type SegmentAssetSaveState = {
  saving: boolean;
  error: string;
  savedAssets: AssetResponse[];
};

const LAST_VIDEO_PROVIDER_KEY = "gmf_last_provider:video";
const LAST_PLAN_PROVIDER_KEY = "gmf_last_provider:video-plan";

export function VideoGenForm() {
  const [providers, setProviders] = useState<ProviderResponse[]>([]);
  const [providerId, setProviderId] = useState(() => {
    if (typeof window === "undefined") return "";
    return localStorage.getItem(LAST_VIDEO_PROVIDER_KEY) ?? "";
  });
  const [model, setModel] = useState("");
  const [planProviderId, setPlanProviderId] = useState(() => {
    if (typeof window === "undefined") return "";
    return localStorage.getItem(LAST_PLAN_PROVIDER_KEY) ?? "";
  });
  const [planModel, setPlanModel] = useState("");
  const [mode, setMode] = useState<GenerationMode>("single");
  const [prompt, setPrompt] = useState("");
  const [count, setCount] = useState(1);
  const [imageMaterialUrls, setImageMaterialUrls] = useState("");
  const [imageMaterialAssetIds, setImageMaterialAssetIds] = useState<string[]>([]);
  const [scenePromptTextInput, setScenePromptTextInput] = useState("");
  const [scenePromptAssetIds, setScenePromptAssetIds] = useState<string[]>([]);
  const [imageAssets, setImageAssets] = useState<AssetResponse[]>([]);
  const [textAssets, setTextAssets] = useState<AssetResponse[]>([]);
  const [copyNotice, setCopyNotice] = useState("");
  const copyTimerRef = useRef<number | null>(null);
  const [assetPickerOpen, setAssetPickerOpen] = useState<"image" | "text" | null>(null);
  const [assetPickerLoading, setAssetPickerLoading] = useState(false);
  const [assetPickerError, setAssetPickerError] = useState("");
  const [uploadingRefs, setUploadingRefs] = useState(false);
  const [totalDurationSeconds, setTotalDurationSeconds] = useState(30);
  const [segmentDurationSeconds, setSegmentDurationSeconds] = useState(10);
  const [loading, setLoading] = useState(false);
  const [planning, setPlanning] = useState(false);
  const [batchLoading, setBatchLoading] = useState(false);
  const [segmentRefreshing, setSegmentRefreshing] = useState<Record<number, boolean>>({});
  const [error, setError] = useState("");
  const [result, setResult] = useState<MediaGenerationResponse | null>(null);
  const [plan, setPlan] = useState<MultiVideoPlanResponse | null>(null);
  const [batchResult, setBatchResult] = useState<MultiVideoGenerationResponse | null>(null);
  const [loaded, setLoaded] = useState(false);

  const [saveCategory, setSaveCategory] = useState("生成");
  const [savingAssets, setSavingAssets] = useState(false);
  const [saveError, setSaveError] = useState("");
  const [savedAssets, setSavedAssets] = useState<AssetResponse[]>([]);
  const [segmentAssetStates, setSegmentAssetStates] = useState<
    Record<number, SegmentAssetSaveState>
  >({});

  const [preview, setPreview] = useState<PreviewState>(null);
  const [activeSegmentIndex, setActiveSegmentIndex] = useState<number | null>(null);

  const busy = loading || planning || batchLoading;
  const elapsedMs = useElapsedMs(busy);

  useEffect(() => {
    void loadProviders();
  }, []);

  useEffect(() => {
    return () => {
      if (copyTimerRef.current != null) {
        window.clearTimeout(copyTimerRef.current);
      }
    };
  }, []);

  async function loadProviders() {
    if (loaded) return;
    try {
      const data = await listProviders();
      setProviders(data.items);
      setLoaded(true);
    } catch {
      setError("加载供应商失败");
    }
  }

  const videoProviders = providers.filter((p) =>
    p.models.some((m) => m.capabilities.includes("video"))
  );
  const textProviders = providers.filter((p) =>
    p.models.some((m) => m.capabilities.includes("text"))
  );

  const selectedVideoProvider = videoProviders.find((p) => p.provider_id === providerId);
  const videoModels =
    selectedVideoProvider?.models.filter((m) => m.capabilities.includes("video")) ?? [];
  const textModels =
    textProviders
      .find((provider) => provider.provider_id === planProviderId)
      ?.models.filter((m) => m.capabilities.includes("text")) ?? [];
  const maxCount = selectedVideoProvider?.adapter_type === "volcengine_ark" ? 1 : 10;

  const selectedImageAssets = imageAssets.filter((a) => imageMaterialAssetIds.includes(a.asset_id));
  const selectedTextAssets = textAssets.filter((a) => scenePromptAssetIds.includes(a.asset_id));
  const promptValue = prompt.trim();
  const manualScenePromptTexts = scenePromptTextInput
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
  const imageMaterialUrlList = imageMaterialUrls
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
  const hasPrompt = promptValue.length > 0;
  const hasScenePromptMaterials =
    scenePromptAssetIds.length > 0 || manualScenePromptTexts.length > 0;
  const hasTextGuidance = hasPrompt || hasScenePromptMaterials;
  const hasVisualReferences =
    imageMaterialAssetIds.length > 0 || imageMaterialUrlList.length > 0;
  const plannedSegments = plan?.segments ?? [];

  const activeSegment =
    batchResult?.segments.find((segment) => segment.segment_index === activeSegmentIndex) ?? null;

  useEffect(() => {
    if (videoProviders.length === 0) return;
    const nextProviderId =
      videoProviders.find((p) => p.provider_id === providerId)?.provider_id ??
      videoProviders.find((p) => p.is_builtin && p.adapter_type === "volcengine_ark")
        ?.provider_id ??
      videoProviders[0]?.provider_id ??
      "";
    const nextProvider = videoProviders.find((p) => p.provider_id === nextProviderId);
    const nextModel =
      nextProvider?.models.find((m) => m.capabilities.includes("video"))?.model ?? "";
    setProviderId(nextProviderId);
    if (!model || !nextProvider?.models.some((item) => item.model === model)) {
      setModel(nextModel);
    }
  }, [videoProviders, providerId, model]);

  useEffect(() => {
    if (textProviders.length === 0) return;
    const nextProviderId =
      textProviders.find((p) => p.provider_id === planProviderId)?.provider_id ??
      textProviders[0]?.provider_id ??
      "";
    const nextProvider = textProviders.find((p) => p.provider_id === nextProviderId);
    const nextModel =
      nextProvider?.models.find((m) => m.capabilities.includes("text"))?.model ?? "";
    setPlanProviderId(nextProviderId);
    if (!planModel || !nextProvider?.models.some((item) => item.model === planModel)) {
      setPlanModel(nextModel);
    }
  }, [textProviders, planProviderId, planModel]);

  async function openAssetPicker(kind: "image" | "text") {
    setAssetPickerOpen(kind);
    setAssetPickerError("");
    const assets = kind === "image" ? imageAssets : textAssets;
    if (assets.length > 0) return;
    setAssetPickerLoading(true);
    try {
      const data = await listAssets({ asset_type: kind });
      if (kind === "image") {
        setImageAssets(data.items);
      } else {
        setTextAssets(data.items);
      }
    } catch (err) {
      setAssetPickerError(err instanceof Error ? err.message : "加载素材失败");
    } finally {
      setAssetPickerLoading(false);
    }
  }

  function toggleImageAsset(assetId: string) {
    setImageMaterialAssetIds((prev) =>
      prev.includes(assetId) ? prev.filter((id) => id !== assetId) : [...prev, assetId]
    );
  }

  function toggleScenePromptAsset(assetId: string) {
    setScenePromptAssetIds((prev) =>
      prev.includes(assetId) ? prev.filter((id) => id !== assetId) : [...prev, assetId]
    );
  }

  async function handleUploadRefs(files: FileList | null) {
    if (!files || files.length === 0) return;
    setUploadingRefs(true);
    setError("");
    try {
      const items = Array.from(files);
      const uploaded = await Promise.all(
        items.map(async (file) => {
          const base64 = await new Promise<string>((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => {
              const value = String(reader.result ?? "");
              const comma = value.indexOf(",");
              if (comma === -1) return reject(new Error("无法读取图片内容"));
              resolve(value.slice(comma + 1));
            };
            reader.onerror = () => reject(new Error("无法读取图片内容"));
            reader.readAsDataURL(file);
          });
          return createAsset({
            asset_type: "image",
            category: "reference",
            name: file.name || "uploaded-reference",
            content_base64: base64,
            mime_type: file.type || "image/png",
            tags: ["reference"],
            metadata: { uploaded_for: "video_generation" },
          });
        })
      );
      setImageAssets((prev) => [...uploaded, ...prev]);
      setImageMaterialAssetIds((prev) => {
        const next = new Set(prev);
        for (const asset of uploaded) next.add(asset.asset_id);
        return Array.from(next);
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "上传失败");
    } finally {
      setUploadingRefs(false);
    }
  }

  function appendTextGuidance(body: Record<string, unknown>) {
    if (promptValue) {
      body.prompt = promptValue;
    }
    if (scenePromptAssetIds.length > 0) {
      body.scene_prompt_asset_ids = scenePromptAssetIds;
    }
    if (manualScenePromptTexts.length > 0) {
      body.scene_prompt_texts = manualScenePromptTexts;
    }
    return body;
  }

  function buildCommonVideoPayload() {
    const body: Record<string, unknown> = {
      provider_id: providerId,
      model,
    };
    if (selectedVideoProvider?.adapter_type === "volcengine_ark") {
      body.options = { generate_audio: true };
    }
    appendTextGuidance(body);
    if (imageMaterialAssetIds.length > 0) {
      body.image_material_asset_ids = imageMaterialAssetIds;
    }
    if (imageMaterialUrlList.length > 0) {
      body.image_material_urls = imageMaterialUrlList;
    }
    return body;
  }

  async function handleSingleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!hasTextGuidance && !hasVisualReferences) {
      setError("请输入提示词，或选择/补充文本素材、参考图片后再生成视频");
      return;
    }
    setLoading(true);
    setError("");
    setResult(null);
    setSaveError("");
    setSavedAssets([]);
    try {
      const body = buildCommonVideoPayload();
      body.count = count;
      const response = await generateVideos(body);
      setResult(response);
      setPlan(null);
      setBatchResult(null);
      localStorage.setItem(LAST_VIDEO_PROVIDER_KEY, providerId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "生成失败");
    } finally {
      setLoading(false);
    }
  }

  async function handlePlanSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!hasTextGuidance) {
      setError("请输入提示词，或选择/补充文本素材后再生成切分方案");
      return;
    }
    setPlanning(true);
    setError("");
    setPlan(null);
    setBatchResult(null);
    try {
      const response = await planMultiVideos(
        appendTextGuidance({
          provider_id: planProviderId,
          model: planModel,
          total_duration_seconds: totalDurationSeconds,
          segment_duration_seconds: segmentDurationSeconds,
        })
      );
      setPlan(response);
      localStorage.setItem(LAST_PLAN_PROVIDER_KEY, planProviderId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "生成切分方案失败");
    } finally {
      setPlanning(false);
    }
  }

  async function handleGenerateMultiVideo() {
    if (!plan) return;
    setBatchLoading(true);
    setError("");
    setSegmentAssetStates({});
    try {
      const response = await generateMultiVideos({
        ...buildCommonVideoPayload(),
        segments: plan.segments,
      });
      setBatchResult(response);
      setResult(null);
      localStorage.setItem(LAST_VIDEO_PROVIDER_KEY, providerId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "批量视频生成失败");
    } finally {
      setBatchLoading(false);
    }
  }

  async function handleRegenerateSegment(segment: MultiVideoSegmentGenerationResult) {
    setSegmentRefreshing((prev) => ({ ...prev, [segment.segment_index]: true }));
    setError("");
    try {
      const previousSegment =
        batchResult?.segments.find((item) => item.segment_index === segment.segment_index - 1) ?? null;
      const previousOutput = previousSegment?.generation?.outputs[0] ?? null;
      const previousLastFrameUrl = getLastFrameUrl(previousOutput);
      const response = await regenerateMultiVideoSegment({
        ...buildCommonVideoPayload(),
        segment: {
          segment_index: segment.segment_index,
          title: segment.title,
          duration_seconds: segment.duration_seconds,
          visual_prompt: segment.visual_prompt,
          narration_text: segment.narration_text,
          use_previous_segment_last_frame: segment.use_previous_segment_last_frame ?? false,
        },
        previous_segment_last_frame_url:
          segment.use_previous_segment_last_frame ? previousLastFrameUrl : null,
      });
      setBatchResult((prev) =>
        prev
          ? {
              ...prev,
              segments: prev.segments.map((item) =>
                item.segment_index === response.segment_index ? response : item
              ),
            }
          : prev
      );
      setActiveSegmentIndex(segment.segment_index);
    } catch (err) {
      setError(err instanceof Error ? err.message : "重生成失败");
    } finally {
      setSegmentRefreshing((prev) => ({ ...prev, [segment.segment_index]: false }));
    }
  }

  async function handleSaveToAssets() {
    if (!result) return;
    if (savedAssets.length > 0) return;
    const categoryValue = saveCategory.trim() || "生成";

    setSavingAssets(true);
    setSaveError("");
    try {
      const assets = await Promise.all(
        result.outputs.map((output, index) => {
          const srcUrl = output.url ?? null;
          const base64 = output.base64_data ?? null;
          if (!srcUrl && !base64) {
            throw new Error("生成结果缺少可保存的内容");
          }
          return createAsset(
            {
              asset_type: "video",
              category: categoryValue,
              name: `video-result-${index + 1}`,
              content_url: srcUrl,
              content_base64: base64,
              mime_type: output.mime_type ?? "video/mp4",
              metadata: output.metadata ?? {},
              provider_id: result.provider_id,
              model: result.model,
              tags: [],
            },
            { origin: "generated" }
          );
        })
      );
      setSavedAssets(assets);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "保存失败");
    } finally {
      setSavingAssets(false);
    }
  }

  async function handleSaveSegmentToAssets(segment: MultiVideoSegmentGenerationResult) {
    if (!segment.generation) return;
    const generation = segment.generation;
    const categoryValue = saveCategory.trim() || "生成";
    setSegmentAssetStates((prev) => ({
      ...prev,
      [segment.segment_index]: { saving: true, error: "", savedAssets: prev[segment.segment_index]?.savedAssets ?? [] },
    }));
    try {
      const assets = await Promise.all(
        generation.outputs.map((output, index) =>
          createAsset(
            {
              asset_type: "video",
              category: categoryValue,
              name: `segment-${segment.segment_index}-${index + 1}`,
              content_url: output.url,
              content_base64: output.base64_data,
              mime_type: output.mime_type ?? "video/mp4",
              metadata: {
                ...(output.metadata ?? {}),
                segment_index: segment.segment_index,
                segment_title: segment.title,
                narration_text: segment.narration_text,
                visual_prompt: segment.visual_prompt,
              },
              provider_id: generation.provider_id,
              model: generation.model,
              tags: ["multi-video"],
            },
            { origin: "generated" }
          )
        )
      );
      setSegmentAssetStates((prev) => ({
        ...prev,
        [segment.segment_index]: { saving: false, error: "", savedAssets: assets },
      }));
    } catch (err) {
      setSegmentAssetStates((prev) => ({
        ...prev,
        [segment.segment_index]: {
          saving: false,
          error: err instanceof Error ? err.message : "保存失败",
          savedAssets: prev[segment.segment_index]?.savedAssets ?? [],
        },
      }));
    }
  }

  async function handleDownloadOutput(
    output: { url: string | null; base64_data: string | null; mime_type: string | null },
    filename: string
  ) {
    if (output.base64_data) {
      const blob = base64ToBlob(output.base64_data, output.mime_type ?? "video/mp4");
      const objectUrl = URL.createObjectURL(blob);
      triggerDownload(objectUrl, filename);
      window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
      return;
    }
    if (!output.url) return;
    try {
      const response = await fetch(output.url);
      const blob = await response.blob();
      const objectUrl = URL.createObjectURL(blob);
      triggerDownload(objectUrl, filename);
      window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
    } catch {
      triggerDownload(output.url, filename);
    }
  }

  function handleModeSwitch(nextMode: GenerationMode) {
    setMode(nextMode);
    setError("");
    setSaveError("");
  }

  function toggleSegmentBridge(segmentIndex: number) {
    setPlan((prev) =>
      prev
        ? {
            ...prev,
            segments: prev.segments.map((segment) =>
              segment.segment_index === segmentIndex
                ? {
                    ...segment,
                    use_previous_segment_last_frame: !segment.use_previous_segment_last_frame,
                  }
                : segment
            ),
          }
        : prev
    );
  }

  function getSegmentBridgeLabel(segment: VideoSegmentPlan) {
    return segment.use_previous_segment_last_frame ? "已衔接首尾帧" : "衔接首尾帧";
  }

  function renderSelectedTextAssets() {
    if (selectedTextAssets.length === 0) return null;
    return (
      <div className="selected-text-list">
        {selectedTextAssets.map((asset) => (
          <article key={asset.asset_id} className="selected-text-card">
            <div className="selected-text-card-head">
              <strong>{asset.name}</strong>
              <button
                className="btn btn-secondary btn-sm"
                type="button"
                onClick={() => toggleScenePromptAsset(asset.asset_id)}
              >
                移除
              </button>
            </div>
            <p>{asset.content_text ?? ""}</p>
          </article>
        ))}
      </div>
    );
  }

  return (
    <div className="gen-layout gen-layout-video">
      <form
        className="panel form-stack gen-sidebar-panel"
        onSubmit={mode === "single" ? handleSingleSubmit : handlePlanSubmit}
      >
        <div className="mode-switch">
          <button
            className={`mode-switch-btn${mode === "single" ? " is-active" : ""}`}
            type="button"
            onClick={() => handleModeSwitch("single")}
          >
            单视频
          </button>
          <button
            className={`mode-switch-btn${mode === "multi" ? " is-active" : ""}`}
            type="button"
            onClick={() => handleModeSwitch("multi")}
          >
            多视频
          </button>
        </div>

        <div className="form-group">
          <label className="form-label">视频供应商</label>
          <select
            className="form-select"
            value={providerId}
            onFocus={loadProviders}
            onChange={(e) => {
              setProviderId(e.target.value);
              setModel("");
            }}
            required
          >
            <option value="">请选择供应商...</option>
            {videoProviders.map((provider) => (
              <option key={provider.provider_id} value={provider.provider_id}>
                {provider.name}
              </option>
            ))}
          </select>
        </div>

        <div className="form-row">
          <div className="form-group">
            <label className="form-label">视频模型</label>
            <select
              className="form-select"
              value={model}
              onChange={(e) => setModel(e.target.value)}
              required
              disabled={!providerId}
            >
              <option value="">请选择模型...</option>
              {videoModels.map((item) => (
                <option key={item.model} value={item.model}>
                  {item.label ?? item.model}
                </option>
              ))}
            </select>
          </div>

          {mode === "single" ? (
            <div className="form-group">
              <label className="form-label">数量</label>
              <input
                className="form-input"
                type="number"
                min={1}
                max={maxCount}
                value={count}
                onChange={(e) =>
                  setCount(Math.min(maxCount, Math.max(1, Number(e.target.value) || 1)))
                }
              />
            </div>
          ) : (
            <div className="form-group">
              <label className="form-label">规划文本模型</label>
              <select
                className="form-select"
                value={planProviderId}
                onChange={(e) => {
                  setPlanProviderId(e.target.value);
                  setPlanModel("");
                }}
                required
              >
                <option value="">请选择供应商...</option>
                {textProviders.map((provider) => (
                  <option key={provider.provider_id} value={provider.provider_id}>
                    {provider.name}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>

        {mode === "multi" && (
          <div className="form-row">
            <div className="form-group">
              <label className="form-label">规划模型</label>
              <select
                className="form-select"
                value={planModel}
                onChange={(e) => setPlanModel(e.target.value)}
                required
                disabled={!planProviderId}
              >
                <option value="">请选择模型...</option>
                {textModels.map((item) => (
                  <option key={item.model} value={item.model}>
                    {item.label ?? item.model}
                  </option>
                ))}
              </select>
            </div>
            <div className="form-row form-row-tight">
              <div className="form-group">
                <label className="form-label">总时长</label>
                <input
                  className="form-input"
                  type="number"
                  min={5}
                  max={600}
                  value={totalDurationSeconds}
                  onChange={(e) => setTotalDurationSeconds(Math.max(5, Number(e.target.value) || 5))}
                />
              </div>
              <div className="form-group">
                <label className="form-label">单段时长</label>
                <input
                  className="form-input"
                  type="number"
                  min={5}
                  max={120}
                  value={segmentDurationSeconds}
                  onChange={(e) =>
                    setSegmentDurationSeconds(Math.max(5, Number(e.target.value) || 5))
                  }
                />
              </div>
            </div>
          </div>
        )}

        <div className="form-group">
          <label className="form-label">提示词与文本素材</label>
          <span className="form-hint">
            {mode === "single"
              ? "在同一个入口里组合主提示词和文本素材。你可以只写提示词、只选文本素材，或两者配合。"
              : "主提示词和文本素材会一起参与切分规划与后续批量生成，不再强制必须单独填写提示词。"}
          </span>
          <div className="video-brief-panel">
            <div className="video-brief-summary" aria-live="polite">
              <span className={`video-brief-chip${hasPrompt ? " is-active" : ""}`}>
                {hasPrompt ? "主提示词已填写" : "主提示词可选"}
              </span>
              <span
                className={`video-brief-chip${manualScenePromptTexts.length > 0 ? " is-active" : ""}`}
              >
                {manualScenePromptTexts.length > 0
                  ? `手动补充 ${manualScenePromptTexts.length} 条`
                  : "可补充剧情线索"}
              </span>
              <span
                className={`video-brief-chip${scenePromptAssetIds.length > 0 ? " is-active" : ""}`}
              >
                {scenePromptAssetIds.length > 0
                  ? `已选素材 ${scenePromptAssetIds.length} 条`
                  : "可选文本素材"}
              </span>
            </div>

            <div className="video-brief-block">
              <div className="video-brief-head">
                <label className="form-label" htmlFor="video-prompt-input">
                  主提示词
                </label>
                <span className="form-hint">
                  {mode === "single"
                    ? "先写核心画面、风格和情绪；没有也可以直接用下方文本素材驱动。"
                    : "用于定义整体创意方向；留空时会优先根据文本素材规划分镜。"}
                </span>
              </div>
              <textarea
                id="video-prompt-input"
                className="form-textarea"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="例如：赛博朋克城市追逐，镜头节奏紧张，结尾反转。"
                rows={4}
              />
            </div>

            <div className="video-brief-block">
              <div className="video-brief-head">
                <label className="form-label" htmlFor="video-scene-prompt-input">
                  文本素材补充
                </label>
                <span className="form-hint">
                  从素材库挑选分镜参考，或逐行补充剧情/镜头说明；会与主提示词一起参与生成。
                </span>
              </div>
              <div className="form-actions video-brief-actions">
                <button
                  className="btn btn-sm btn-secondary"
                  type="button"
                  onClick={() => void openAssetPicker("text")}
                >
                  从文本素材库选择
                </button>
                <span style={{ color: "var(--muted)", fontSize: "0.88rem" }}>
                  已选 {scenePromptAssetIds.length} 条素材
                </span>
                {scenePromptAssetIds.length > 0 && (
                  <button
                    className="btn btn-sm btn-secondary"
                    type="button"
                    onClick={() => setScenePromptAssetIds([])}
                  >
                    清空文本素材
                  </button>
                )}
              </div>
              {renderSelectedTextAssets()}
              <textarea
                id="video-scene-prompt-input"
                className="form-textarea"
                value={scenePromptTextInput}
                onChange={(e) => setScenePromptTextInput(e.target.value)}
                placeholder="补充剧情、角色状态、镜头氛围。每行一条。"
                rows={4}
              />
            </div>
          </div>
        </div>

        <div className="form-group">
          <label className="form-label">参考图片</label>
          <span className="form-hint">支持 URL / 素材库选择 / 本地上传（可选）</span>
          <div className="form-actions" style={{ paddingTop: 0, flexWrap: "wrap" }}>
            <button
              className="btn btn-sm btn-secondary"
              type="button"
              onClick={() => void openAssetPicker("image")}
              disabled={uploadingRefs}
            >
              从素材库选择
            </button>
            <label
              className="btn btn-sm btn-secondary"
              style={{ position: "relative", overflow: "hidden" }}
            >
              {uploadingRefs ? "上传中..." : "上传图片"}
              <input
                type="file"
                accept="image/*"
                multiple
                onChange={(e) => void handleUploadRefs(e.target.files)}
                style={{ position: "absolute", inset: 0, opacity: 0, cursor: "pointer" }}
                disabled={uploadingRefs}
              />
            </label>
            <span style={{ color: "var(--muted)", fontSize: "0.88rem" }}>
              已选 {imageMaterialAssetIds.length} 张
            </span>
            {imageMaterialAssetIds.length > 0 && (
              <button
                className="btn btn-sm btn-secondary"
                type="button"
                onClick={() => setImageMaterialAssetIds([])}
                disabled={uploadingRefs}
              >
                清空图片
              </button>
            )}
          </div>

          <textarea
            className="form-textarea"
            value={imageMaterialUrls}
            onChange={(e) => setImageMaterialUrls(e.target.value)}
            placeholder="https://example.com/ref1.jpg&#10;https://example.com/ref2.jpg"
            rows={3}
          />

          {selectedImageAssets.length > 0 && (
            <div className="asset-gallery" style={{ marginTop: 12 }}>
              {selectedImageAssets.slice(0, 6).map((asset) => {
                const src = asset.content_url
                  ? asset.content_url
                  : asset.content_base64
                    ? `data:${asset.mime_type ?? "image/png"};base64,${asset.content_base64}`
                    : null;
                return (
                  <article
                    key={asset.asset_id}
                    className="asset-card"
                    style={{ cursor: "pointer" }}
                    onClick={() => toggleImageAsset(asset.asset_id)}
                    title="点击取消选择"
                  >
                    {src ? <img className="asset-thumb" src={src} alt={asset.name} /> : null}
                    <div className="asset-info">
                      <h4 style={{ fontSize: "0.95rem" }}>{asset.name}</h4>
                      <div className="asset-info-meta">
                        <span className="tag-pill">已选</span>
                        <span className="tag-pill">{asset.category}</span>
                      </div>
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </div>

        <div className="form-actions">
          <button className="btn btn-primary" type="submit" disabled={busy}>
            {busy && <span className="spinner" />}
            {mode === "single"
              ? loading
                ? "生成中..."
                : "生成视频"
              : planning
                ? "规划中..."
                : "生成切分方案"}
          </button>
          {mode === "multi" && plan && (
            <button
              className="btn btn-secondary"
              type="button"
              onClick={() => void handleGenerateMultiVideo()}
              disabled={busy}
            >
              {batchLoading && <span className="spinner spinner-dark" />}
              {batchLoading ? "批量生成中..." : "确认并批量生成"}
            </button>
          )}
        </div>
      </form>

      <div className="gen-results gen-results-scroll">
        {error && <div className="error-banner">{error}</div>}

        <div className="panel form-stack">
          <div className="form-row">
            <div className="form-group">
              <label className="form-label">保存分类</label>
              <input
                className="form-input"
                type="text"
                value={saveCategory}
                onChange={(e) => setSaveCategory(e.target.value)}
                placeholder="例如：场景片段"
              />
            </div>
            <div className="form-group">
              <label className="form-label">处理状态</label>
              <div className="info-banner" style={{ minHeight: 48 }}>
                {busy ? `处理中，已用时 ${formatElapsed(elapsedMs)}` : "等待开始生成"}
              </div>
            </div>
          </div>
          {mode === "single" && result && (
            <div className="form-actions" style={{ paddingTop: 0 }}>
              <button
                className="btn btn-secondary"
                type="button"
                onClick={handleSaveToAssets}
                disabled={savingAssets || savedAssets.length > 0}
              >
                {savingAssets && <span className="spinner spinner-dark" />}
                {savedAssets.length > 0 ? "已加入素材库" : "加入素材库"}
              </button>
              {savedAssets.length > 0 && (
                <span style={{ color: "var(--muted)", fontSize: "0.88rem" }}>
                  已保存 {savedAssets.length} 个
                </span>
              )}
            </div>
          )}
          {saveError && <div className="error-banner">{saveError}</div>}
        </div>

        {mode === "single" && result && (
          <>
            <div className="info-banner">
              已生成 {result.outputs.length} 段视频 · {result.resolved_prompt.slice(0, 80)}
              {result.resolved_prompt.length > 80 ? "..." : ""}
            </div>
            <div className="gen-output-grid">
              {result.outputs.map((output) => (
                <div key={output.index} className="gen-output-card">
                  {output.url && (
                    <video src={output.url} controls poster={output.cover_image_url ?? undefined} />
                  )}
                  <div className="gen-output-meta">
                    <div className="gen-output-meta-row">
                      <small>
                        视频 {output.index + 1}
                        {output.duration_seconds != null &&
                          ` · ${output.duration_seconds.toFixed(1)}s`}
                      </small>
                    </div>
                    <div className="form-actions" style={{ paddingTop: 10, flexWrap: "wrap" }}>
                      {output.url && (
                        <button
                          className="btn btn-secondary btn-sm"
                          type="button"
                          onClick={() =>
                            setPreview({
                              src: output.url!,
                              poster: output.cover_image_url,
                              title: `生成视频 ${output.index + 1}`,
                            })
                          }
                        >
                          预览
                        </button>
                      )}
                      <button
                        className="btn btn-secondary btn-sm"
                        type="button"
                        onClick={() => void handleDownloadOutput(output, `video-${output.index + 1}.mp4`)}
                      >
                        下载
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}

        {mode === "multi" && plan && (
          <section className="panel form-stack">
            <div className="info-banner">
              切分方案已生成 · 共 {plan.segment_count} 段 · 规划 Token
              {plan.usage?.total_tokens != null ? ` ${plan.usage.total_tokens}` : " 暂无"}
            </div>
            <div className="segment-plan-list">
              {plannedSegments.map((segment, index) => (
                <div key={segment.segment_index} className="segment-plan-flow">
                  <article className="segment-plan-card">
                    <div className="segment-plan-card-head">
                      <strong>
                        第 {segment.segment_index} 段 · {segment.title}
                      </strong>
                      <span className="tag-pill">{segment.duration_seconds}s</span>
                    </div>
                    <p className="segment-plan-copy">{segment.visual_prompt}</p>
                    <p className="segment-plan-copy is-script">{segment.narration_text}</p>
                  </article>
                  {index < plannedSegments.length - 1 && (
                    <div className="segment-bridge-toggle-wrap">
                      <button
                        className={`segment-bridge-toggle${
                          plannedSegments[index + 1]?.use_previous_segment_last_frame ? " is-active" : ""
                        }`}
                        type="button"
                        onClick={() => toggleSegmentBridge(plannedSegments[index + 1].segment_index)}
                      >
                        <span className="segment-bridge-toggle-line" aria-hidden="true" />
                        <span className="segment-bridge-toggle-copy">
                          第 {segment.segment_index} 段尾帧 → 第 {plannedSegments[index + 1].segment_index} 段首帧
                        </span>
                        <span className="segment-bridge-toggle-state">
                          {getSegmentBridgeLabel(plannedSegments[index + 1])}
                        </span>
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </section>
        )}

        {mode === "multi" && batchResult && (
          <>
            <div className="info-banner">
              批量生成完成 · 成功{" "}
              {batchResult.segments.filter((item) => item.status === "success").length} 段 · 失败{" "}
              {batchResult.segments.filter((item) => item.status === "error").length} 段
            </div>
            <div className="segment-plan-list">
              {batchResult.segments.map((segment) => {
                const firstOutput = segment.generation?.outputs[0] ?? null;
                const saveState = segmentAssetStates[segment.segment_index];
                const refreshing = !!segmentRefreshing[segment.segment_index];
                return (
                  <article key={segment.segment_index} className="segment-plan-card">
                    <div className="segment-plan-card-head">
                      <strong>
                        第 {segment.segment_index} 段 · {segment.title}
                      </strong>
                      <span className={`tag-pill${segment.status === "error" ? " tag-pill-danger" : ""}`}>
                        {segment.status === "success" ? "已生成" : "失败"}
                      </span>
                    </div>
                    {firstOutput?.url ? (
                      <video
                        className="segment-video-thumb"
                        src={firstOutput.url}
                        controls
                        poster={firstOutput.cover_image_url ?? undefined}
                      />
                    ) : (
                      <div className="segment-video-empty">
                        {segment.error_detail ? "该分段生成失败" : "等待视频输出"}
                      </div>
                    )}
                    <p className="segment-plan-copy">{segment.visual_prompt}</p>
                    <p className="segment-plan-copy is-script">{segment.narration_text}</p>
                    {segment.error_detail && <div className="error-banner">{segment.error_detail}</div>}
                    <div className="form-actions" style={{ paddingTop: 0, flexWrap: "wrap" }}>
                      <button
                        className="btn btn-secondary btn-sm"
                        type="button"
                        onClick={() => setActiveSegmentIndex(segment.segment_index)}
                      >
                        详情
                      </button>
                      <button
                        className="btn btn-secondary btn-sm"
                        type="button"
                        onClick={() => void handleRegenerateSegment(segment)}
                        disabled={refreshing}
                      >
                        {refreshing ? "重生成中..." : "重生成"}
                      </button>
                      {firstOutput && (
                        <button
                          className="btn btn-secondary btn-sm"
                          type="button"
                          onClick={() =>
                            void handleDownloadOutput(
                              firstOutput,
                              `segment-${segment.segment_index}.mp4`
                            )
                          }
                        >
                          下载
                        </button>
                      )}
                      {segment.generation && (
                        <button
                          className="btn btn-secondary btn-sm"
                          type="button"
                          onClick={() => void handleSaveSegmentToAssets(segment)}
                          disabled={saveState?.saving || (saveState?.savedAssets.length ?? 0) > 0}
                        >
                          {saveState?.saving
                            ? "保存中..."
                            : (saveState?.savedAssets.length ?? 0) > 0
                              ? "已存素材库"
                              : "存入素材库"}
                        </button>
                      )}
                    </div>
                    {saveState?.error && <div className="error-banner">{saveState.error}</div>}
                  </article>
                );
              })}
            </div>
          </>
        )}

        {((mode === "single" && !result && !error) ||
          (mode === "multi" && !plan && !batchResult && !error)) && (
          <div className="gen-empty-shell">
            <div className="gen-empty">
              <div className="gen-empty-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <polygon points="5 3 19 12 5 21 5 3" />
                </svg>
              </div>
              <p>{mode === "single" ? "生成结果会显示在这里" : "切分方案和分段视频会显示在这里"}</p>
            </div>

            {busy && (
              <div className="gen-empty-overlay" role="status" aria-live="polite">
                <span className="spinner spinner-dark" />
                <div className="gen-empty-overlay-text">
                  <strong>{mode === "single" ? "生成中..." : "处理中..."}</strong>
                  <span>已用时 {formatElapsed(elapsedMs)}</span>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {preview && (
        <div className="dialog-overlay" role="dialog" aria-modal="true" onClick={() => setPreview(null)}>
          <div className="dialog-panel media-preview-panel" onClick={(e) => e.stopPropagation()}>
            <div className="media-preview-header">
              <h2>{preview.title}</h2>
              <button className="btn btn-secondary btn-sm" type="button" onClick={() => setPreview(null)}>
                关闭
              </button>
            </div>
            <video
              className="media-preview-video"
              src={preview.src}
              controls
              poster={preview.poster ?? undefined}
            />
          </div>
        </div>
      )}

      {activeSegment && (
        <div
          className="dialog-overlay"
          role="dialog"
          aria-modal="true"
          onClick={() => setActiveSegmentIndex(null)}
        >
          <div className="dialog-panel asset-detail-panel" onClick={(e) => e.stopPropagation()}>
            <div className="media-preview-header">
              <h2 style={{ margin: 0 }}>
                第 {activeSegment.segment_index} 段 · {activeSegment.title}
              </h2>
              <button
                className="btn btn-secondary btn-sm"
                type="button"
                onClick={() => setActiveSegmentIndex(null)}
              >
                关闭
              </button>
            </div>

            {activeSegment.generation?.outputs[0]?.url ? (
              <video
                className="media-preview-video"
                src={activeSegment.generation.outputs[0].url!}
                controls
                poster={activeSegment.generation.outputs[0].cover_image_url ?? undefined}
              />
            ) : (
              <div className="segment-video-empty" style={{ marginTop: 16 }}>
                暂无视频输出
              </div>
            )}

            <div className="panel form-stack" style={{ marginTop: 18 }}>
              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">文案脚本</label>
                  <div className="gen-text-output">{activeSegment.narration_text}</div>
                </div>
                <div className="form-group">
                  <label className="form-label">画面提示</label>
                  <div className="gen-text-output">{activeSegment.visual_prompt}</div>
                </div>
              </div>
              <div className="form-group">
                <label className="form-label">实际生成提示词</label>
                <div className="gen-text-output">{activeSegment.resolved_prompt}</div>
              </div>
              {activeSegment.error_detail && <div className="error-banner">{activeSegment.error_detail}</div>}
              <div className="form-actions" style={{ paddingTop: 0, flexWrap: "wrap" }}>
                <button
                  className="btn btn-secondary"
                  type="button"
                  onClick={() => void handleRegenerateSegment(activeSegment)}
                  disabled={!!segmentRefreshing[activeSegment.segment_index]}
                >
                  {segmentRefreshing[activeSegment.segment_index] ? "重生成中..." : "重生成"}
                </button>
                {activeSegment.generation?.outputs[0] && (
                  <>
                    <button
                      className="btn btn-secondary"
                      type="button"
                      onClick={() =>
                        void handleDownloadOutput(
                          activeSegment.generation!.outputs[0],
                          `segment-${activeSegment.segment_index}.mp4`
                        )
                      }
                    >
                      保存到本地
                    </button>
                    <button
                      className="btn btn-secondary"
                      type="button"
                      onClick={() => void handleSaveSegmentToAssets(activeSegment)}
                      disabled={
                        segmentAssetStates[activeSegment.segment_index]?.saving ||
                        (segmentAssetStates[activeSegment.segment_index]?.savedAssets.length ?? 0) > 0
                      }
                    >
                      {segmentAssetStates[activeSegment.segment_index]?.saving
                        ? "保存中..."
                        : (segmentAssetStates[activeSegment.segment_index]?.savedAssets.length ?? 0) > 0
                          ? "已存素材库"
                          : "存入素材库"}
                    </button>
                  </>
                )}
              </div>
              {segmentAssetStates[activeSegment.segment_index]?.error && (
                <div className="error-banner">
                  {segmentAssetStates[activeSegment.segment_index]?.error}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {assetPickerOpen && (
        <div
          className="dialog-overlay"
          role="dialog"
          aria-modal="true"
          onClick={() => setAssetPickerOpen(null)}
        >
          <div className="dialog-panel asset-detail-panel" onClick={(e) => e.stopPropagation()}>
            <div className="media-preview-header">
              <h2 style={{ margin: 0 }}>
                {assetPickerOpen === "image" ? "选择参考图片" : "选择文本素材"}
              </h2>
              <button
                className="btn btn-secondary btn-sm"
                type="button"
                onClick={() => setAssetPickerOpen(null)}
              >
                关闭
              </button>
            </div>

            {assetPickerError && <div className="error-banner" style={{ marginTop: 16 }}>{assetPickerError}</div>}

            {assetPickerLoading ? (
              <div className="gen-empty">
                <span className="spinner spinner-dark" />
                <p>正在加载素材...</p>
              </div>
            ) : assetPickerOpen === "image" ? (
              imageAssets.length === 0 ? (
                <div className="gen-empty">
                  <p>素材库中还没有图片素材</p>
                </div>
              ) : (
                <div className="asset-gallery asset-picker-grid" style={{ marginTop: 16 }}>
                  {imageAssets.map((asset) => {
                    const src = asset.content_url
                      ? asset.content_url
                      : asset.content_base64
                        ? `data:${asset.mime_type ?? "image/png"};base64,${asset.content_base64}`
                        : null;
                    const selected = imageMaterialAssetIds.includes(asset.asset_id);
                    return (
                      <article
                        key={asset.asset_id}
                        className={`asset-card${selected ? " is-selected" : ""}`}
                        onClick={() => toggleImageAsset(asset.asset_id)}
                      >
                        {src ? <img className="asset-thumb" src={src} alt={asset.name} /> : null}
                        <div className="asset-info">
                          <h4>{asset.name}</h4>
                          <div className="asset-info-meta">
                            <span className="tag-pill">{selected ? "已选" : "点击选择"}</span>
                            {asset.category && <span className="tag-pill">{asset.category}</span>}
                          </div>
                        </div>
                      </article>
                    );
                  })}
                </div>
              )
            ) : textAssets.length === 0 ? (
              <div className="gen-empty">
                <p>素材库中还没有文本素材</p>
              </div>
            ) : (
              <div className="asset-gallery asset-picker-grid" style={{ marginTop: 16 }}>
                {textAssets.map((asset) => {
                  const selected = scenePromptAssetIds.includes(asset.asset_id);
                  return (
                    <article
                      key={asset.asset_id}
                      className={`asset-card text-asset-card${selected ? " is-selected" : ""}`}
                      onClick={() => toggleScenePromptAsset(asset.asset_id)}
                    >
                      <div className="asset-text-thumb asset-text-thumb-lg">
                        {(asset.content_text ?? "").slice(0, 180)}
                        {(asset.content_text ?? "").length > 180 ? "..." : ""}
                      </div>
                      <div className="asset-info">
                        <h4>{asset.name}</h4>
                        <div className="asset-info-meta">
                          <span className="tag-pill">{selected ? "已选" : "点击选择"}</span>
                          {asset.category && <span className="tag-pill">{asset.category}</span>}
                        </div>
                      </div>
                    </article>
                  );
                })}
              </div>
            )}

            <div className="form-actions" style={{ marginTop: 16 }}>
              <button className="btn btn-primary" type="button" onClick={() => setAssetPickerOpen(null)}>
                {assetPickerOpen === "image"
                  ? `确认（已选 ${imageMaterialAssetIds.length} 张）`
                  : `确认（已选 ${scenePromptAssetIds.length} 条）`}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function base64ToBlob(base64: string, mimeType: string) {
  const binary = window.atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }
  return new Blob([bytes], { type: mimeType });
}

function triggerDownload(url: string, filename: string) {
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.target = "_blank";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

function getLastFrameUrl(
  output:
    | {
        cover_image_url: string | null;
        metadata: Record<string, unknown>;
      }
    | null
) {
  if (!output) return null;
  const metadata = output.metadata ?? {};
  const metadataLastFrame =
    typeof metadata.last_frame_url === "string"
      ? metadata.last_frame_url
      : typeof metadata.end_frame_url === "string"
        ? metadata.end_frame_url
        : typeof metadata.tail_frame_url === "string"
          ? metadata.tail_frame_url
          : null;
  return metadataLastFrame ?? output.cover_image_url ?? null;
}
