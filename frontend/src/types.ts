export type PipelineStage = 
  | "IDEA" 
  | "RESEARCH" 
  | "SCRIPT" 
  | "QC1" 
  | "STYLE" 
  | "ART" 
  | "VIDEO" 
  | "QC2" 
  | "POST" 
  | "ANALYZE";

export type JobStatus = 
  | "PENDING" 
  | "IN_PROGRESS" 
  | "AWAITING_APPROVAL" 
  | "AWAITING_PREMIUM" 
  | "COMPLETED" 
  | "FAILED";

export interface StageRecord {
  id: number;
  stage: PipelineStage;
  output: Record<string, any>;
  timestamp: string;
}

export interface AssetRecord {
  id: number;
  type: "SCRIPT" | "AUDIO" | "VIDEO" | "IMAGE";
  path: string;
  description: string;
}

export interface ApprovalRecord {
  id: number;
  stage: string;
  decision: "APPROVED" | "REJECTED";
  timestamp: string;
  notes?: string;
}

export interface CostRecord {
  id: number;
  agent_name: string;
  tokens: number;
  usd_estimate: number;
  timestamp: string;
}

export interface JobAnalytics {
  views: number;
  likes: number;
  comments: number;
  shares: number;
  retention_rate: number;
  revenue: number;
}

export interface Job {
  id: number;
  niche: string;
  status: JobStatus;
  current_stage: PipelineStage;
  config: {
    format?: string;
    target_duration?: number;
    platforms?: string[];
    premium?: boolean;
    premium_asset_uploaded?: boolean;
    [key: string]: any;
  };
  created_at: string;
  stages: StageRecord[];
  assets: AssetRecord[];
  approvals: ApprovalRecord[];
  costs: CostRecord[];
  analytics?: JobAnalytics;
}

export interface VaultData {
  metrics: {
    totalViews: number;
    totalSpent: number;
    totalTokens: number;
    totalRevenue: number;
    dailyBudget: number;
    activeJobsCount: number;
    completedJobsCount: number;
  };
  styleGuides: Array<{
    niche: string;
    archetype: string;
    primaryColor: string;
    accentColor: string;
    typography: string;
    cutFrequency: string;
    music: string;
  }>;
  characterBibles: Array<{
    niche: string;
    characterName: string;
    persona: string;
    visualDescription: string;
  }>;
  hookFormulas: Array<{
    formula: string;
    score: number;
    count: number;
  }>;
  logs: Array<{
    id: number;
    time: string;
    message: string;
  }>;
}

export interface CodeFile {
  name: string;
  path: string;
  desc: string;
  content: string;
  exists: boolean;
}

export type N8nNodeCategory = 
  | "trigger" 
  | "routing" 
  | "agent" 
  | "subagent" 
  | "tool" 
  | "model" 
  | "memory" 
  | "output";

export interface FreeTierLimitInfo {
  tierName: string;
  quotaLimit: string;
  whyChosen: string;
  apiKeyName: string;
  isConfigured: boolean;
  docUrl?: string;
}

export interface WorkflowNode {
  id: string;
  name: string;
  label: string;
  subtitle: string;
  category: N8nNodeCategory;
  iconName: string;
  x: number;
  y: number;
  width?: number;
  height?: number;
  status: "idle" | "running" | "success" | "error" | "waiting";
  inputs?: Array<{ id: string; label: string; type: "main" | "model" | "memory" | "tool" }>;
  outputs?: Array<{ id: string; label: string; type: "main" | "true" | "false" | "success" | "error" }>;
  subPins?: {
    model?: boolean;
    think?: boolean;
    memory?: boolean;
    tools?: boolean;
  };
  freeTierInfo?: FreeTierLimitInfo;
  defaultParams?: Record<string, any>;
  lastOutput?: Record<string, any>;
}

export interface WorkflowEdge {
  id: string;
  fromNode: string;
  fromPort?: string;
  toNode: string;
  toPort?: string;
  type?: "main" | "dashed" | "subpin";
  animated?: boolean;
  status?: "active" | "idle" | "success";
  label?: string;
}

export interface WorkflowExecutionStep {
  nodeId: string;
  nodeName: string;
  status: "success" | "error" | "running" | "skipped";
  durationMs: number;
  inputData?: any;
  outputData?: any;
  error?: string;
}

export interface WorkflowExecution {
  id: string;
  workflowName: string;
  status: "SUCCESS" | "RUNNING" | "WAITING" | "ERROR";
  triggerType: "TELEGRAM_WEBHOOK" | "MANUAL_TEST" | "CRON_SCHEDULER";
  startedAt: string;
  durationMs: number;
  niche: string;
  nodesCount: number;
  steps: WorkflowExecutionStep[];
}

export interface ColorSpec {
  hex: string;
  usage_pct: number;
  note: string;
}

export interface TextStyleSpec {
  font: string;
  size: string;
  animation: string;
  safe_zone: string;
}

export interface VisualDNA {
  color_palette: ColorSpec[];
  composition_rules: string[];
  lighting_style: string;
  camera_angles: string[];
  editing_pace: string;
  text_style: TextStyleSpec;
  b_roll_preferences: string[];
  audio_signature: string;
}

export interface HookFormula {
  formula: string;
  avg_retention_3s: number;
}

export interface PlatformPerformance {
  avg_views: number;
  avg_retention: number;
  best_posting_window: string;
}

export interface NicheProfile {
  profile_id: string;
  name: string;
  description: string;
  visual_dna: VisualDNA;
  hook_formulas: HookFormula[];
  character_archetypes: { name: string; traits: string[] }[];
  platform_performance: Record<string, PlatformPerformance>;
  source: "mock" | "live";
}

export interface VisualStrategy {
  strategy_id: string;
  profile_id: string;
  topic: string;
  scene_overrides: { scene: string; override: string; color_emphasis: string }[];
  asset_strategy: Record<string, string>;
  source: "mock" | "live";
}

export interface ShotPlatformSpecs {
  aspect_ratio: string;
  safe_zone: string;
  within_hook_window: boolean;
}

export interface Shot {
  id: string;
  index: number;
  start_seconds: number;
  end_seconds: number;
  purpose: "hook" | "value" | "demo" | "cta" | string;
  visual_description: string;
  assets_needed: string[];
  audio_cues: string[];
  retention_risk: number;
  prompts: Record<string, string>;
  platform_specs: ShotPlatformSpecs | Record<string, never>;
}

export interface CharacterPack {
  id: string;
  name: string;
  archetype: string;
  turnaround_prompts: Record<string, string>;
  expression_prompts: Record<string, string>;
  outfit_variants: string[];
  lora_training_data: Record<string, unknown>;
  seed_recommendations: number[];
  source: "mock" | "live";
}

export interface PlatformSpecs {
  aspect_ratio: string;
  max_duration_s: number;
  safe_zone: string;
  hook_window_s: number;
  caption_style: string;
  hashtag_strategy: string;
  audio_specs: string;
}

export const MODEL_LABELS: Record<string, string> = {
  midjourney: "Midjourney",
  dalle3: "DALL·E 3",
  stable_diffusion: "Stable Diffusion",
  veo2: "Veo 2",
  runway_gen3: "Runway Gen-3",
  kling: "Kling",
  sora: "Sora",
  luma_dream: "Luma Dream Machine",
};

export const ALL_MODELS = Object.keys(MODEL_LABELS);

export const API_KEY_LABELS: Record<string, string> = {
  GEMINI_API_KEY: "Gemini API Key",
  YOUTUBE_API_KEY: "YouTube Data API Key",
  TAVILY_API_KEY: "Tavily API Key",
  PEXELS_API_KEY: "Pexels API Key",
  SERPAPI_KEY: "SerpAPI Key (optional)",
  FIRECRAWL_API_KEY: "Firecrawl API Key (optional)",
};

export interface KeyStatus {
  configured: boolean;
  masked: string;
}

export interface SettingsStatus {
  mock_forced: boolean;
  keys: Record<string, KeyStatus>;
}
