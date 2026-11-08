# CONTENT-FACTORY: Multi-Agent AI Content Automation Pipeline

## 1. Executive Summary
**CONTENT-FACTORY** is an autonomous multi-agent production studio engineered to automate the complete lifecycle of viral short-form content (TikTok, Instagram Reels, YouTube Shorts). Orchestrated by an executive **Manager Agent** with **Human-in-the-Loop (HITL)** governance via Telegram, the pipeline coordinates 9 specialized AI agents across 10 deterministic stages from strategic ideation to automated distribution and algorithmic post-mortem analytics.

---

## 2. Architecture: 4 Phases, 9 Agents, 10 Stages

```
[Phase 1: Brain]
IDEA (Manager) ──> RESEARCH (Researcher) ──> SCRIPT (Scriptwriter)
                                                    │
                                             [APPROVAL GATE 1]
                                                    ▼
[Phase 2: Creative]
QC1 (Quality Control) ──> STYLE (Style Analyst) ──> ART (Art Director) ──> VIDEO (Video Editor)
                                                                                  │
                                                                           [APPROVAL GATE 2]
                                                                                  ▼
[Phase 3: Distribution]                                                  QC2 (Quality Control)
POST (Poster via Postiz)                                                          │
      │                                                                    [APPROVAL GATE 3]
      ▼                                                                           ▼
[Phase 4: Intelligence]                                                    Ready to Post
ANALYZE (Analyst) ──> Updates Style Guides & Hook Formulas
```

### 10 Pipeline Stages:
1. **IDEA**: Goal formulation, target audience profiling, retention benchmark definition.
2. **RESEARCH**: YouTube Data API search + Tavily/SerpAPI trend extraction and virality scoring.
3. **SCRIPT**: High-retention 3-second hook, 3-act tension loop, CTA, multi-platform variants.
4. **QC1**: Text-level quality check, policy compliance, originality verification.
5. **STYLE**: Multimodal visual DNA extraction (Gemini Vision), color palette, typography pacing.
6. **ART**: Veo 3.1 & Nano-Banana prompt packs, shot lists, character bibles, scene storyboards.
7. **VIDEO**: FFmpeg audio/video assembly, Edge-TTS narration, dynamic ASS captions, pacing optimization. Supports escalation to `AWAITING_PREMIUM` for high-end rendering.
8. **QC2**: Audio-visual sync verification, loudness calibration (-14 LUFS), TikTok safe-zone auditing.
9. **POST**: Automated publishing/scheduling to TikTok, IG Reels, and YT Shorts via Postiz API.
10. **ANALYZE**: Algorithmic performance tracking, retention curve analysis, creator reward computation, feedback loop updates to Hook Formulas and Style Guides.

---

## 3. Human-In-The-Loop (HITL) Telegram Interface
The Telegram bot acts as the primary executive remote control with 14 commands:
- `/goal <niche>`: Spawn new content production job
- `/status`: Real-time pipeline status of all active jobs
- `/pending`: List jobs awaiting approval or premium escalation
- `/approve <id>`: Approve current stage and resume pipeline
- `/reject <id> <reason>`: Reject and request revision
- `/variants <id>`: Generate alternative hook and script variants
- `/preview <id>`: Inspect generated media, scripts, and storyboards
- `/premium <id>`: Enable premium video generation mode
- `/upload_premium <id>`: Attach custom Veo/Flow video render
- `/post <id>`: Immediate social media distribution
- `/analyze <id>`: Fetch viral retention metrics and engagement
- `/cost`: Real-time token usage, API spend, and daily budget limits
- `/report`: Daily executive operations summary
- `/help`: Command documentation and usage guide

---

## 4. Vault Database Layer
13 specialized models backed by SQLAlchemy 2.0 Async:
- **Jobs**: Pipeline execution instance state.
- **JobStages**: Historical execution logs and outputs per stage.
- **Assets**: Structured media registry (Scripts, Audio, Video, Storyboards).
- **Approvals**: Audit trail of human decisions.
- **Analytics**: Real-time impressions, retention, likes, comments, shares.
- **Costs**: Per-agent token consumption and USD ledger.
- **StyleGuides**: Niche-specific visual DNA, color codes, cut frequencies.
- **CharacterBibles**: Persistent characters, voice personas, and wardrobe styles.
- **HookFormulas**: High-performing viral hooks ranked by virality score.
- **RevenueStreams**: Monitized earnings from creator reward programs.
- **RetentionCurves**: Granular second-by-second audience watch-time data.
- **SkillManifests**: Pluggable agent capabilities and tool parameter configs.
- **Logs**: Centralized system event and error trace logs.
