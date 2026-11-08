import { WorkflowNode, WorkflowEdge } from "./types";

// Generously spaced nodes matching the clean horizontal pipeline and sub-agent pods
export const DEFAULT_WORKFLOW_NODES: WorkflowNode[] = [
  // Top Main Orchestration Line with generous spacing
  {
    id: "node-telegram-trigger",
    name: "Telegram Trigger",
    label: "Telegram Trigger",
    subtitle: "updates: message",
    category: "trigger",
    iconName: "Send",
    x: 80,
    y: 150,
    width: 200,
    height: 76,
    status: "idle",
    outputs: [{ id: "out-main", label: "", type: "main" }],
    freeTierInfo: {
      tierName: "Telegram Bot API",
      quotaLimit: "Unlimited (Free long-polling / webhook)",
      whyChosen: "Push notifications, inline keyboards, zero hosting cost",
      apiKeyName: "TELEGRAM_BOT_TOKEN",
      isConfigured: true
    }
  },
  {
    id: "node-switch-type",
    name: "Switch",
    label: "Switch",
    subtitle: "mode: Rules",
    category: "routing",
    iconName: "GitFork",
    x: 390,
    y: 150,
    width: 190,
    height: 76,
    status: "idle",
    inputs: [{ id: "in-main", label: "", type: "main" }],
    outputs: [
      { id: "out-voice", label: "Voice", type: "main" },
      { id: "out-text", label: "Text", type: "main" }
    ]
  },
  {
    id: "node-download-voice",
    name: "Download Voice File",
    label: "Download Voice File",
    subtitle: "get: file",
    category: "tool",
    iconName: "DownloadCloud",
    x: 700,
    y: 40,
    width: 200,
    height: 76,
    status: "idle",
    inputs: [{ id: "in-main", label: "", type: "main" }],
    outputs: [{ id: "out-main", label: "", type: "main" }]
  },
  {
    id: "node-transcribe-audio",
    name: "Transcribe Audio",
    label: "Transcribe Audio",
    subtitle: "Whisper / Gemini Vision",
    category: "tool",
    iconName: "Mic",
    x: 1020,
    y: 40,
    width: 200,
    height: 76,
    status: "idle",
    inputs: [{ id: "in-main", label: "", type: "main" }],
    outputs: [{ id: "out-main", label: "", type: "main" }]
  },
  {
    id: "node-set-text",
    name: "Set 'Text'",
    label: "Set 'Text'",
    subtitle: "manual payload",
    category: "routing",
    iconName: "FileText",
    x: 700,
    y: 260,
    width: 200,
    height: 76,
    status: "idle",
    inputs: [{ id: "in-main", label: "", type: "main" }],
    outputs: [{ id: "out-main", label: "", type: "main" }]
  },
  {
    id: "node-input-prep",
    name: "Input",
    label: "Input",
    subtitle: "manual JSON",
    category: "routing",
    iconName: "FileSpreadsheet",
    x: 1340,
    y: 150,
    width: 190,
    height: 76,
    status: "idle",
    inputs: [{ id: "in-main", label: "", type: "main" }],
    outputs: [{ id: "out-main", label: "", type: "main" }]
  },
  // Central Orchestrator: AI Agent
  {
    id: "node-ai-agent",
    name: "AI Agent",
    label: "AI Agent",
    subtitle: "Content Factory Manager",
    category: "agent",
    iconName: "Bot",
    x: 1650,
    y: 136,
    width: 240,
    height: 104,
    status: "idle",
    inputs: [{ id: "in-main", label: "", type: "main" }],
    outputs: [
      { id: "out-success", label: "Success", type: "success" },
      { id: "out-error", label: "Error", type: "error" }
    ],
    subPins: {
      model: true,
      think: true,
      memory: true,
      tools: true
    },
    freeTierInfo: {
      tierName: "gemini-3.6-flash (Primary LLM)",
      quotaLimit: "15 RPM, 1,500 RPD, 1M tokens/min",
      whyChosen: "Fastest, cheapest, structured JSON schema output, 1M context",
      apiKeyName: "GEMINI_API_KEY",
      isConfigured: true
    }
  },
  // Output paths from AI Agent
  {
    id: "node-clean-up",
    name: "Clean Up",
    label: "Clean Up",
    subtitle: "format schema",
    category: "routing",
    iconName: "Code",
    x: 2010,
    y: 50,
    width: 190,
    height: 76,
    status: "idle",
    inputs: [{ id: "in-main", label: "", type: "main" }],
    outputs: [{ id: "out-main", label: "", type: "main" }]
  },
  {
    id: "node-append-vault",
    name: "Append to SQLite Vault",
    label: "Append row in sheet",
    subtitle: "vault.db (13 models)",
    category: "memory",
    iconName: "Database",
    x: 2320,
    y: 50,
    width: 200,
    height: 76,
    status: "idle",
    inputs: [{ id: "in-main", label: "", type: "main" }],
    outputs: [{ id: "out-main", label: "", type: "main" }],
    freeTierInfo: {
      tierName: "SQLite 3 / PostgreSQL",
      quotaLimit: "Unlimited local storage",
      whyChosen: "Zero config, file-based, local async CRUD operations",
      apiKeyName: "DATABASE_URL",
      isConfigured: true
    }
  },
  {
    id: "node-telegram-response",
    name: "Telegram Response",
    label: "Response",
    subtitle: "sendmessage: message",
    category: "output",
    iconName: "Send",
    x: 2640,
    y: 50,
    width: 200,
    height: 76,
    status: "idle",
    inputs: [{ id: "in-main", label: "", type: "main" }]
  },
  {
    id: "node-error-handler",
    name: "Error Message",
    label: "Error Message",
    subtitle: "sendmessage: alert",
    category: "output",
    iconName: "AlertTriangle",
    x: 2010,
    y: 230,
    width: 200,
    height: 76,
    status: "idle",
    inputs: [{ id: "in-main", label: "", type: "main" }]
  },
  // Model & Memory sub-nodes connected under AI Agent
  {
    id: "node-model-gemini-flash",
    name: "gemini-3.6-flash",
    label: "gemini-3.6-flash",
    subtitle: "Chat Model (15 RPM)",
    category: "model",
    iconName: "Cpu",
    x: 1320,
    y: 340,
    width: 190,
    height: 74,
    status: "idle",
    freeTierInfo: {
      tierName: "Google AI Studio",
      quotaLimit: "15 RPM, 1,500 RPD, 1.5M tokens/day",
      whyChosen: "Only provider with free tier + vision + JSON schema without credit card",
      apiKeyName: "GEMINI_API_KEY",
      isConfigured: true,
      docUrl: "https://aistudio.google.com/apikey"
    }
  },
  {
    id: "node-think-prompt",
    name: "Think Reasoning",
    label: "Think",
    subtitle: "Director System Prompt",
    category: "agent",
    iconName: "Brain",
    x: 1570,
    y: 340,
    width: 180,
    height: 74,
    status: "idle"
  },
  {
    id: "node-vault-memory",
    name: "Simple Memory",
    label: "Simple Memory",
    subtitle: "Window Buffer & Vault",
    category: "memory",
    iconName: "Database",
    x: 1810,
    y: 340,
    width: 180,
    height: 74,
    status: "idle"
  },

  // Sub-Agent Pod 1: Research & Trends (Researcher)
  {
    id: "node-subagent-research",
    name: "Research Agent",
    label: "Research Agent",
    subtitle: "Web & Trend Intel",
    category: "subagent",
    iconName: "Compass",
    x: 1500,
    y: 480,
    width: 200,
    height: 76,
    status: "idle",
    subPins: { model: true, tools: true }
  },
  {
    id: "node-tool-youtube",
    name: "YouTube Data API v3",
    label: "YouTube Videos",
    subtitle: "search: trends (10k units)",
    category: "tool",
    iconName: "Video",
    x: 1420,
    y: 610,
    width: 190,
    height: 76,
    status: "idle",
    freeTierInfo: {
      tierName: "YouTube Data API v3",
      quotaLimit: "10,000 units/day (~500 searches)",
      whyChosen: "Only reliable source for real YouTube trend & view count data",
      apiKeyName: "YOUTUBE_API_KEY",
      isConfigured: true
    }
  },
  {
    id: "node-tool-tavily",
    name: "Tavily Search",
    label: "Tavily Search",
    subtitle: "query: search (1k/mo)",
    category: "tool",
    iconName: "Search",
    x: 1640,
    y: 610,
    width: 190,
    height: 76,
    status: "idle",
    freeTierInfo: {
      tierName: "Tavily Search API",
      quotaLimit: "1,000 requests/month",
      whyChosen: "Built for AI agents, returns clean markdown & citations",
      apiKeyName: "TAVILY_API_KEY",
      isConfigured: true
    }
  },
  {
    id: "node-tool-firecrawl",
    name: "Firecrawl / Jina Reader",
    label: "Jina Reader",
    subtitle: "URL -> markdown (Free)",
    category: "tool",
    iconName: "FileCode",
    x: 1860,
    y: 610,
    width: 190,
    height: 76,
    status: "idle",
    freeTierInfo: {
      tierName: "Jina Reader & Firecrawl",
      quotaLimit: "Unlimited (Jina) / 500 cr (Firecrawl)",
      whyChosen: "Zero-cost URL extraction for research depth",
      apiKeyName: "NONE",
      isConfigured: true
    }
  },

  // Sub-Agent Pod 2: Scriptwriter Agent
  {
    id: "node-subagent-script",
    name: "Scriptwriter Agent",
    label: "Scriptwriter Agent",
    subtitle: "3-Act Retention Loops",
    category: "subagent",
    iconName: "PenTool",
    x: 2180,
    y: 480,
    width: 200,
    height: 76,
    status: "idle",
    subPins: { model: true, tools: true }
  },
  {
    id: "node-tool-hook-vault",
    name: "Hook Formulas Vault",
    label: "Hook Vault",
    subtitle: "top viral templates",
    category: "tool",
    iconName: "Bookmark",
    x: 2100,
    y: 610,
    width: 190,
    height: 76,
    status: "idle"
  },
  {
    id: "node-tool-character-bible",
    name: "Character Bible",
    label: "Character Persona",
    subtitle: "visual & voice specs",
    category: "tool",
    iconName: "UserCheck",
    x: 2320,
    y: 610,
    width: 190,
    height: 76,
    status: "idle"
  },

  // Sub-Agent Pod 3: Art & Style (Art Director & Style Analyst)
  {
    id: "node-subagent-art",
    name: "Art & Style Agent",
    label: "Art & Style Agent",
    subtitle: "Visual DNA & Storyboard",
    category: "subagent",
    iconName: "Palette",
    x: 80,
    y: 480,
    width: 200,
    height: 76,
    status: "idle",
    subPins: { model: true, tools: true }
  },
  {
    id: "node-model-gemini-37",
    name: "gemini-3.7-flash",
    label: "gemini-3.7-flash",
    subtitle: "Complex reasoning (10 RPM)",
    category: "model",
    iconName: "Sparkles",
    x: 60,
    y: 610,
    width: 190,
    height: 76,
    status: "idle",
    freeTierInfo: {
      tierName: "gemini-3.7-flash",
      quotaLimit: "10 RPM, 1,000 RPD",
      whyChosen: "High creative reasoning for prompt packs & aesthetic palettes",
      apiKeyName: "GEMINI_API_KEY",
      isConfigured: true
    }
  },
  {
    id: "node-tool-pexels",
    name: "Pexels Stock API",
    label: "Pexels API",
    subtitle: "20k/mo stock vertical clips",
    category: "tool",
    iconName: "Image",
    x: 280,
    y: 610,
    width: 190,
    height: 76,
    status: "idle",
    freeTierInfo: {
      tierName: "Pexels API",
      quotaLimit: "200 req/hr, 20,000/month",
      whyChosen: "High quality, royalty-free, commercial use allowed, no watermarks",
      apiKeyName: "PEXELS_API_KEY",
      isConfigured: true,
      docUrl: "https://www.pexels.com/api/"
    }
  },
  {
    id: "node-tool-veo-prompts",
    name: "Veo 3.1 Prompt Pack",
    label: "Veo / Flow Pack",
    subtitle: "4K cinematic prompts ($20/mo)",
    category: "tool",
    iconName: "Clapperboard",
    x: 500,
    y: 610,
    width: 190,
    height: 76,
    status: "idle",
    freeTierInfo: {
      tierName: "Google Veo / Flow (Manual)",
      quotaLimit: "$20/mo Gemini Pro browser access",
      whyChosen: "Browser-only manual generation. Art Director exports prompt packs.",
      apiKeyName: "MANUAL",
      isConfigured: true
    }
  },

  // Sub-Agent Pod 4: Video Assembly (Video Editor)
  {
    id: "node-subagent-video",
    name: "Video Editor Agent",
    label: "Video Editor Agent",
    subtitle: "Assembly & Burn Captions",
    category: "subagent",
    iconName: "Film",
    x: 820,
    y: 480,
    width: 200,
    height: 76,
    status: "idle",
    subPins: { model: true, tools: true }
  },
  {
    id: "node-tool-edge-tts",
    name: "Edge-TTS (Microsoft)",
    label: "Edge-TTS (Free)",
    subtitle: "100+ voices (en-US-AriaNeural)",
    category: "tool",
    iconName: "Volume2",
    x: 740,
    y: 610,
    width: 190,
    height: 76,
    status: "idle",
    freeTierInfo: {
      tierName: "Edge-TTS (Microsoft)",
      quotaLimit: "100% FREE (No API key, no limits)",
      whyChosen: "High quality neural TTS with zero cost used by major creators",
      apiKeyName: "NONE",
      isConfigured: true
    }
  },
  {
    id: "node-tool-ffmpeg",
    name: "FFmpeg Assembler",
    label: "FFmpeg (Local)",
    subtitle: "1080x1920 60FPS encode",
    category: "tool",
    iconName: "Layers",
    x: 960,
    y: 610,
    width: 190,
    height: 76,
    status: "idle",
    freeTierInfo: {
      tierName: "FFmpeg Local Binary",
      quotaLimit: "FREE (Local hardware accel)",
      whyChosen: "Concatenation, filters, dynamic subtitles, loudness normalization",
      apiKeyName: "LOCAL",
      isConfigured: true
    }
  },
  {
    id: "node-model-gemini-vision",
    name: "gemini-2.5-pro",
    label: "gemini-2.5-pro",
    subtitle: "Vision Frame Review (5 RPM)",
    category: "model",
    iconName: "Eye",
    x: 1180,
    y: 610,
    width: 190,
    height: 76,
    status: "idle",
    freeTierInfo: {
      tierName: "gemini-2.5-pro Vision",
      quotaLimit: "5 RPM, 100 RPD",
      whyChosen: "Best vision understanding for inspecting video frames & safety zones",
      apiKeyName: "GEMINI_API_KEY",
      isConfigured: true
    }
  },

  // Sub-Agent Pod 5: Quality Control & HITL (QC1 & QC2)
  {
    id: "node-subagent-qc",
    name: "Quality Control Agent",
    label: "Quality Control",
    subtitle: "Audit & HITL Gate",
    category: "subagent",
    iconName: "ShieldCheck",
    x: 740,
    y: 750,
    width: 200,
    height: 76,
    status: "idle",
    subPins: { model: true, tools: true }
  },
  {
    id: "node-tool-qc-audit",
    name: "Originality & Loudness Check",
    label: "QC Check",
    subtitle: "-14 LUFS, safe-zones",
    category: "tool",
    iconName: "CheckCircle",
    x: 630,
    y: 880,
    width: 190,
    height: 76,
    status: "idle"
  },
  {
    id: "node-tool-telegram-hitl",
    name: "Telegram HITL Gate",
    label: "Telegram HITL",
    subtitle: "inline /approve /reject",
    category: "tool",
    iconName: "Send",
    x: 850,
    y: 880,
    width: 190,
    height: 76,
    status: "idle"
  },

  // Sub-Agent Pod 6: Social Distribution (Poster)
  {
    id: "node-subagent-post",
    name: "Poster Agent",
    label: "Poster Agent",
    subtitle: "Social Distribution",
    category: "subagent",
    iconName: "Share2",
    x: 1260,
    y: 750,
    width: 200,
    height: 76,
    status: "idle"
  },
  {
    id: "node-tool-postiz",
    name: "Postiz Self-Hosted",
    label: "Postiz API",
    subtitle: "TikTok, Reels, Shorts",
    category: "tool",
    iconName: "Globe",
    x: 1260,
    y: 880,
    width: 200,
    height: 76,
    status: "idle",
    freeTierInfo: {
      tierName: "Postiz (Self-Hosted)",
      quotaLimit: "100% FREE Open-Source",
      whyChosen: "Only free multi-platform social scheduler with full API",
      apiKeyName: "POSTIZ_API_KEY",
      isConfigured: true
    }
  },

  // Sub-Agent Pod 7: Performance Analytics (Analyst)
  {
    id: "node-subagent-analyst",
    name: "Analyst Agent",
    label: "Analyst Agent",
    subtitle: "Retention & Loopback",
    category: "subagent",
    iconName: "TrendingUp",
    x: 1680,
    y: 750,
    width: 200,
    height: 76,
    status: "idle"
  },
  {
    id: "node-tool-feedback-loop",
    name: "Algorithmic Feedback Loop",
    label: "Feedback Loop",
    subtitle: "update hook formulas",
    category: "tool",
    iconName: "Repeat",
    x: 1680,
    y: 880,
    width: 200,
    height: 76,
    status: "idle"
  },

  // Sub-Agent Pod 8: Soundtrack & VFX
  {
    id: "node-subagent-soundtrack",
    name: "Soundtrack Agent",
    label: "Soundtrack Agent",
    subtitle: "AI Music & Ducking",
    category: "subagent",
    iconName: "Music",
    x: 350,
    y: 750,
    width: 200,
    height: 76,
    status: "idle",
    subPins: { model: true, tools: true }
  },
  {
    id: "node-tool-suno",
    name: "Suno API",
    label: "Suno API",
    subtitle: "Generate music",
    category: "tool",
    iconName: "Headphones",
    x: 350,
    y: 880,
    width: 200,
    height: 76,
    status: "idle"
  },
  {
    id: "node-tool-vfx",
    name: "FFmpeg VFX",
    label: "Hook Overlays",
    subtitle: "Zoom, glitch, camera shake",
    category: "tool",
    iconName: "MonitorPlay",
    x: 960,
    y: 730,
    width: 190,
    height: 76,
    status: "idle"
  }
];

export const DEFAULT_WORKFLOW_EDGES: WorkflowEdge[] = [
  // Main flow line
  { id: "e1", fromNode: "node-telegram-trigger", toNode: "node-switch-type", type: "main" },
  { id: "e2", fromNode: "node-switch-type", toNode: "node-download-voice", type: "main", label: "Voice" },
  { id: "e3", fromNode: "node-switch-type", toNode: "node-set-text", type: "main", label: "Text" },
  { id: "e4", fromNode: "node-download-voice", toNode: "node-transcribe-audio", type: "main" },
  { id: "e5", fromNode: "node-transcribe-audio", toNode: "node-input-prep", type: "main" },
  { id: "e6", fromNode: "node-set-text", toNode: "node-input-prep", type: "main" },
  { id: "e7", fromNode: "node-input-prep", toNode: "node-ai-agent", type: "main" },
  // AI Agent outputs
  { id: "e8", fromNode: "node-ai-agent", toNode: "node-clean-up", type: "main", label: "Success" },
  { id: "e9", fromNode: "node-clean-up", toNode: "node-append-vault", type: "main" },
  { id: "e10", fromNode: "node-append-vault", toNode: "node-telegram-response", type: "main" },
  { id: "e11", fromNode: "node-ai-agent", toNode: "node-error-handler", type: "main", label: "Error" },

  // Curved sub-pin connections from AI Agent bottom
  { id: "e-sub-model", fromNode: "node-ai-agent", toNode: "node-model-gemini-flash", type: "subpin" },
  { id: "e-sub-think", fromNode: "node-ai-agent", toNode: "node-think-prompt", type: "subpin" },
  { id: "e-sub-mem", fromNode: "node-ai-agent", toNode: "node-vault-memory", type: "subpin" },
  { id: "e-sub-research", fromNode: "node-ai-agent", toNode: "node-subagent-research", type: "subpin" },
  { id: "e-sub-script", fromNode: "node-ai-agent", toNode: "node-subagent-script", type: "subpin" },
  { id: "e-sub-art", fromNode: "node-ai-agent", toNode: "node-subagent-art", type: "subpin" },
  { id: "e-sub-video", fromNode: "node-ai-agent", toNode: "node-subagent-video", type: "subpin" },
  { id: "e-sub-qc", fromNode: "node-ai-agent", toNode: "node-subagent-qc", type: "subpin" },
  { id: "e-sub-post", fromNode: "node-ai-agent", toNode: "node-subagent-post", type: "subpin" },
  { id: "e-sub-analyst", fromNode: "node-ai-agent", toNode: "node-subagent-analyst", type: "subpin" },

  // Research Agent tools
  { id: "e-res-yt", fromNode: "node-subagent-research", toNode: "node-tool-youtube", type: "dashed" },
  { id: "e-res-tav", fromNode: "node-subagent-research", toNode: "node-tool-tavily", type: "dashed" },
  { id: "e-res-fire", fromNode: "node-subagent-research", toNode: "node-tool-firecrawl", type: "dashed" },

  // Script Agent tools
  { id: "e-scr-vault", fromNode: "node-subagent-script", toNode: "node-tool-hook-vault", type: "dashed" },
  { id: "e-scr-char", fromNode: "node-subagent-script", toNode: "node-tool-character-bible", type: "dashed" },

  // Art Agent tools
  { id: "e-art-model", fromNode: "node-subagent-art", toNode: "node-model-gemini-37", type: "dashed" },
  { id: "e-art-pex", fromNode: "node-subagent-art", toNode: "node-tool-pexels", type: "dashed" },
  { id: "e-art-veo", fromNode: "node-subagent-art", toNode: "node-tool-veo-prompts", type: "dashed" },

  // Video Agent tools
  { id: "e-vid-tts", fromNode: "node-subagent-video", toNode: "node-tool-edge-tts", type: "dashed" },
  { id: "e-vid-ff", fromNode: "node-subagent-video", toNode: "node-tool-ffmpeg", type: "dashed" },
  { id: "e-vid-vis", fromNode: "node-subagent-video", toNode: "node-model-gemini-vision", type: "dashed" },
  { id: "e-vid-vfx", fromNode: "node-subagent-video", toNode: "node-tool-vfx", type: "dashed" },

  // QC Agent tools
  { id: "e-qc-audit", fromNode: "node-subagent-qc", toNode: "node-tool-qc-audit", type: "dashed" },
  { id: "e-qc-tg", fromNode: "node-subagent-qc", toNode: "node-tool-telegram-hitl", type: "dashed" },

  // Poster Agent tools
  { id: "e-post-postiz", fromNode: "node-subagent-post", toNode: "node-tool-postiz", type: "dashed" },

  // Analyst Agent tools
  { id: "e-ana-loop", fromNode: "node-subagent-analyst", toNode: "node-tool-feedback-loop", type: "dashed" },
  
  // Soundtrack Agent tools
  { id: "e-sub-sound", fromNode: "node-ai-agent", toNode: "node-subagent-soundtrack", type: "subpin" },
  { id: "e-snd-suno", fromNode: "node-subagent-soundtrack", toNode: "node-tool-suno", type: "dashed" }
];
