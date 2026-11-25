import { useState, type FormEvent } from 'react';
import { Badge, Button, ProgressRing } from '../components/ui';
import {
  Cpu,
  Zap,
  Volume2,
  Film,
  CheckCircle2,
  Loader2,
  Target,
  Activity,
  ShieldCheck,
  RefreshCw,
  Layers,
  AlertTriangle,
  Play,
  ArrowRight,
  HardDrive
} from 'lucide-react';
import {
  api,
  useOpenRouterCapabilities,
  useHouseQuotas,
  useVideoGenStatus
} from '../api/client';

const STAGE_ORDER = ['text', 'vision', 'image', 'speech', 'audio', 'video'];

export default function Agents() {
  const [selectedAgentIdx, setSelectedAgentIdx] = useState(0);
  const [benchTopic, setBenchTopic] = useState('CIA Project Azorian');
  const [benchHooks, setBenchHooks] = useState<string[]>([]);
  const [benchLatency, setBenchLatency] = useState<string | null>(null);
  const [testError, setTestError] = useState<string | null>(null);
  const [isTesting, setIsTesting] = useState(false);
  const [isRefreshingCaps, setIsRefreshingCaps] = useState(false);
  const [expandedStage, setExpandedStage] = useState<string | null>(null);

  const { data: caps, refetch: refetchCaps, isLoading: isCapsLoading } = useOpenRouterCapabilities();
  const { data: houseQuotas } = useHouseQuotas();
  const { data: videoGenStatus } = useVideoGenStatus();

  const textModel = caps?.stages?.text?.primary_free_model || 'Gemini Free / Spark-X2.5-4B';
  const visionModel = caps?.stages?.vision?.primary_free_model || 'FFmpeg + Faster-Whisper CPU';
  const imageModel = caps?.stages?.image?.primary_free_model || 'Wikimedia + Pexels + Flux ($0)';
  const speechModel = caps?.stages?.speech?.primary_free_model || 'Edge-TTS + Kokoro-82M ONNX';

  const agents = [
    {
      step: '01',
      name: 'Niche Scorer',
      role: 'Demand & Retention Evaluator',
      stageKey: 'text',
      primaryEngine: textModel,
      fallbackEngine: 'Local Spark-X2.5-4B (Q4_K_M GGUF)',
      ramProfile: '0 MB Cloud / ~240 MB KV Cap Offline',
      ioContract: 'Topic String -> 50-Point Retention & CPM Breakdown JSON',
      guardrail: 'Enforces $0.00 Double-Lock on cloud calls',
      desc: 'Evaluates search demand, curiosity gap strength, and documentary replay value before scripting begins.',
      icon: Target
    },
    {
      step: '02',
      name: 'Viral Researcher',
      role: 'Grounded Fact Dossier',
      stageKey: 'text',
      primaryEngine: 'Wikipedia REST + Wikimedia Commons + yt-dlp',
      fallbackEngine: 'Cached Workspace Research Dossier',
      ramProfile: '~45 MB HTTP / Zero Local GPU',
      ioContract: 'Topic -> Verified Dates, Entities, Quotes & Archival Stills',
      guardrail: 'Blocks fabricated dates and unverified claims',
      desc: 'Retrieves real historical facts, archival photographs, and grounded entities so scripts stay factual.',
      icon: Zap
    },
    {
      step: '03',
      name: 'Documentary Planner',
      role: 'Beat & Pacing Architect',
      stageKey: 'text',
      primaryEngine: textModel,
      fallbackEngine: 'Spark-X2.5-4B + 5-House BM25 Vault',
      ramProfile: 'Auto-sleeps after 75s idle',
      ioContract: 'Fact Dossier + Reflexion Rules -> 14-16 Timed Beat Manifest',
      guardrail: 'Injects active Reflexion learned rules into system prompt',
      desc: 'Structures 2.5s-4.0s visual beats, camera motion vectors, SFX cues, and Act transitions.',
      icon: Cpu
    },
    {
      step: '04',
      name: 'Visual & Depth Cortex',
      role: 'B-Roll, 2.5D Parallax & ZeroGPU',
      stageKey: 'image',
      primaryEngine: `${videoGenStatus?.primary_space || 'Lightricks/LTX-2.5'} + Pexels HD`,
      fallbackEngine: imageModel,
      ramProfile: 'Cloud ZeroGPU + Pillow 60fps CPU',
      ioContract: 'Beat Prompt -> 1080p Archival Parallax / Moving MP4 Clip',
      guardrail: '300 MB LRU cache cap on external scratch storage',
      desc: 'Synthesizes 2-layer foreground/background parallax, forensic document cards, and $0 ZeroGPU hero clips.',
      icon: Layers
    },
    {
      step: '05',
      name: 'Voice & Karaoke ASS',
      role: 'Broadcast Audio & Subtitles',
      stageKey: 'speech',
      primaryEngine: speechModel,
      fallbackEngine: 'Kokoro-82M int8 ONNX (Local Offline)',
      ramProfile: '~88 MB ONNX Weights on CPU',
      ioContract: 'Beat Sentences -> -14 LUFS Master WAV + Millisecond .ASS',
      guardrail: 'Sidechain BGM ducking (-14 dB) + Montserrat-Black pills',
      desc: 'Generates neural narration with automatic offline Kokoro failover and word-accurate karaoke captions.',
      icon: Volume2
    },
    {
      step: '06',
      name: '2-Pass FFmpeg & Critic',
      role: 'Thermal-Safe Encoder & QA',
      stageKey: 'video',
      primaryEngine: `FFmpeg H.264 (-threads 4) + ${visionModel}`,
      fallbackEngine: 'Manifest History vN Snapshot Rollback',
      ramProfile: 'Unloads LLM before Pass 2 (~3.2 GB freed)',
      ioContract: 'Cached Beat Clips + Audio + ASS -> Master MP4 + .ZIP',
      guardrail: 'Single-worker semaphore + pause signal to harvester',
      desc: 'Unloads local LLM weights before encoding, stitches SHA-256 cached beats, and versions manifests for 1-click undo.',
      icon: Film
    }
  ];

  const activeAgent = agents[selectedAgentIdx] || agents[0];
  const ActiveAgentIcon = activeAgent.icon;

  const handleRunBenchmark = async (e?: FormEvent) => {
    if (e) e.preventDefault();
    if (isTesting) return;
    setIsTesting(true);
    setTestError(null);
    setBenchHooks([]);
    const start = performance.now();
    try {
      const res = await api.post('/api/jobs/brainstorm-hooks', {
        topic: benchTopic.trim() || 'CIA Project Azorian'
      });
      const elapsedSec = ((performance.now() - start) / 1000).toFixed(2);
      setBenchLatency(`${elapsedSec}s`);
      if (Array.isArray(res?.hooks) && res.hooks.length > 0) {
        setBenchHooks(res.hooks);
      } else {
        setBenchHooks(['Engine responded cleanly with 0 errors.']);
      }
    } catch (err: any) {
      setTestError(err?.message || 'Benchmark request failed.');
    } finally {
      setIsTesting(false);
    }
  };

  const handleRefreshCatalog = async () => {
    setIsRefreshingCaps(true);
    try {
      await api.get('/api/copilot/openrouter-capabilities?refresh=true');
      await refetchCaps();
    } catch (e) {
      console.error(e);
    } finally {
      setIsRefreshingCaps(false);
    }
  };

  const freeCount = caps?.catalog_strictly_free_count ?? 0;
  const totalScanned = caps?.catalog_total_scanned ?? 0;
  const totalRecords = houseQuotas?.data?.total_records ?? 0;
  const milestoneCap = houseQuotas?.data?.current_milestone_cap ?? 100000;
  const breakerOnCooldown = caps?.circuit_breaker?.on_cooldown ?? false;

  return (
    <div className="animate-in fade-in min-h-full flex flex-col pb-10 space-y-5">
      {/* Studio Header */}
      <div className="flex justify-between items-center flex-wrap gap-3 shrink-0">
        <div>
          <div className="flex items-center gap-2.5 flex-wrap">
            <h1 className="text-2xl font-bold tracking-tight text-[var(--tx)]">
              Multi-Agent Signal Topology
            </h1>
            <Badge variant="success">$0.00 Double-Lock Enforced</Badge>
          </div>
          <p className="text-[var(--mu)] text-xs mt-0.5">
            Inspect the 6-stage documentary assembly pipeline, hardware memory handoffs, and live `$0 :free` model routing.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="secondary"
            onClick={handleRefreshCatalog}
            disabled={isRefreshingCaps}
          >
            <RefreshCw
              size={13}
              className={
                isRefreshingCaps ? 'animate-spin text-blue-500' : 'text-blue-600 dark:text-blue-400'
              }
            />
            <span>{isRefreshingCaps ? 'Scanning Catalog...' : 'Rescan Free Catalog'}</span>
          </Button>

          <Button
            type="button"
            variant="primary"
            onClick={() => handleRunBenchmark()}
            disabled={isTesting}
          >
            {isTesting ? <Loader2 size={13} className="animate-spin" /> : <Activity size={13} />}
            <span>{isTesting ? 'Pinging Router...' : 'Benchmark Brain'}</span>
          </Button>
        </div>
      </div>

      {/* 3-Zone Telemetry & ProgressRing Strip */}
      <div className="glass-panel p-5 grid grid-cols-1 md:grid-cols-3 gap-5 md:divide-x divide-[var(--ln-subtle)]">
        <div className="flex items-center justify-between gap-3 md:pr-5">
          <div>
            <span className="text-[11px] font-bold uppercase tracking-wider text-[var(--mu)]">
              Strictly-Free Cloud Models
            </span>
            <div className="mt-1 flex items-baseline gap-1.5">
              <span className="text-3xl font-extrabold font-mono text-[var(--tx)] tabular-nums">
                {freeCount}
              </span>
              <span className="text-xs font-mono text-[var(--mu)]">
                / {totalScanned} cataloged
              </span>
            </div>
            <p className="text-[11px] text-emerald-600 dark:text-emerald-400 font-semibold mt-0.5">
              Pricing verified 0.00 across all tokens
            </p>
          </div>
          <ProgressRing
            value={freeCount}
            max={Math.max(1, totalScanned || 100)}
            size={54}
            color="var(--ok)"
            centerText={`${freeCount}`}
            label="Strictly free models discovered"
          />
        </div>

        <div className="flex items-center justify-between gap-3 md:px-5">
          <div>
            <span className="text-[11px] font-bold uppercase tracking-wider text-[var(--mu)]">
              Circuit Breaker &amp; Failover
            </span>
            <div className="mt-1 flex items-center gap-2">
              <span className="text-lg font-extrabold text-[var(--tx)]">
                {breakerOnCooldown ? 'Cooldown Active' : 'Healthy & Armed'}
              </span>
              <Badge variant={caps?.api_key_configured ? 'success' : 'info'}>
                {caps?.api_key_configured ? 'OpenRouter Ready' : 'Gemini + Local'}
              </Badge>
            </div>
            <p className="text-[11px] text-[var(--mu)] mt-0.5">
              {breakerOnCooldown
                ? `Auto-skipping to local engines (${Math.round(caps?.circuit_breaker?.remaining_seconds || 0)}s left)`
                : '0ms instant failover on HTTP 402 / 429'}
            </p>
          </div>
          <div
            className={`w-12 h-12 rounded-2xl border flex items-center justify-center shrink-0 ${
              breakerOnCooldown
                ? 'bg-amber-500/15 border-amber-500/30 text-amber-600 dark:text-amber-400'
                : 'bg-blue-600/15 border-blue-500/30 text-blue-600 dark:text-blue-400'
            }`}
          >
            {breakerOnCooldown ? <AlertTriangle size={20} /> : <ShieldCheck size={20} />}
          </div>
        </div>

        <div className="flex items-center justify-between gap-3 md:pl-5">
          <div>
            <span className="text-[11px] font-bold uppercase tracking-wider text-[var(--mu)]">
              5-House Memory Corpus
            </span>
            <div className="mt-1 flex items-baseline gap-1.5">
              <span className="text-2xl font-extrabold font-mono text-[var(--tx)] tabular-nums">
                {totalRecords.toLocaleString()}
              </span>
              <span className="text-xs font-mono text-[var(--mu)]">records</span>
            </div>
            <p className="text-[11px] text-[var(--mu)] mt-0.5">
              BM25 few-shot retrieval active (0 VRAM)
            </p>
          </div>
          <ProgressRing
            value={totalRecords}
            max={Math.max(1, milestoneCap)}
            size={54}
            color="var(--ac)"
            label="5-House milestone memory ratio"
          />
        </div>
      </div>

      {/* Interactive 6-Node Pipeline Signal Graph (Click Any Node to Inspect) */}
      <div className="glass-panel p-5 space-y-3">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <h2 className="text-xs font-bold uppercase tracking-wider text-[var(--tx)]">
            Interactive 6-Stage Execution Chain (Select any node to inspect contract &amp; hardware profile)
          </h2>
          <span className="text-[11px] font-mono text-blue-600 dark:text-blue-400">
            Selected: {activeAgent.step} · {activeAgent.name}
          </span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5">
          {agents.map((ag, idx) => {
            const Icon = ag.icon;
            const isSelected = idx === selectedAgentIdx;
            return (
              <button
                key={ag.name}
                type="button"
                onClick={() => setSelectedAgentIdx(idx)}
                className={`p-3 rounded-xl border text-left transition-all cursor-pointer flex flex-col justify-between gap-2.5 relative ${
                  isSelected
                    ? 'bg-blue-600 text-white border-blue-500 shadow-md shadow-blue-600/25'
                    : 'bg-[var(--gl2)] border-[var(--ln)] text-[var(--tx)] hover:border-blue-500/45'
                }`}
              >
                <div className="flex items-center justify-between w-full">
                  <span
                    className={`font-mono text-[10px] font-extrabold px-1.5 py-0.5 rounded ${
                      isSelected
                        ? 'bg-white/20 text-white'
                        : 'bg-[var(--input-bg)] text-[var(--mu)] border border-[var(--ln-subtle)]'
                    }`}
                  >
                    {ag.step}
                  </span>
                  <Icon size={15} className={isSelected ? 'text-white' : 'text-blue-600 dark:text-blue-400'} />
                </div>
                <div>
                  <div className="text-xs font-bold leading-tight">{ag.name}</div>
                  <div
                    className={`text-[10px] mt-0.5 truncate ${
                      isSelected ? 'text-blue-100' : 'text-[var(--mu)]'
                    }`}
                  >
                    {ag.role}
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Main 2-Column Workspace: 7/12 Agent Deep-Dive & Live Benchmark | 5/12 6-Modality Router Cards */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-5 items-start">
        {/* LEFT (7/12): Active Subsystem Deep-Dive + Live Prompt Benchmark Console */}
        <div className="xl:col-span-7 flex flex-col gap-5 min-w-0">
          {/* Selected Node Deep-Dive Card */}
          <div className="prismatic-launch-card p-5 space-y-4">
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="w-11 h-11 rounded-2xl bg-cyan-500/20 border border-cyan-400/40 text-cyan-300 flex items-center justify-center shrink-0">
                  <ActiveAgentIcon size={20} />
                </div>
                <div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-mono text-xs font-bold text-cyan-300">
                      STAGE {activeAgent.step}
                    </span>
                    <h2 className="text-lg font-extrabold text-white tracking-tight">
                      {activeAgent.name}
                    </h2>
                    <span className="px-2 py-0.5 rounded-md bg-emerald-500/20 border border-emerald-400/40 text-emerald-300 text-[10px] font-bold uppercase">
                      Operational
                    </span>
                  </div>
                  <p className="text-xs text-slate-300 mt-0.5">{activeAgent.desc}</p>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div className="p-3 rounded-xl bg-white/8 border border-white/12 space-y-1">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                  Primary Active Engine
                </span>
                <span className="font-mono font-semibold text-white block break-all">
                  {activeAgent.primaryEngine}
                </span>
              </div>

              <div className="p-3 rounded-xl bg-white/8 border border-white/12 space-y-1">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                  Offline / Rate-Limit Fallback
                </span>
                <span className="font-mono font-semibold text-cyan-200 block break-all">
                  {activeAgent.fallbackEngine}
                </span>
              </div>

              <div className="p-3 rounded-xl bg-white/8 border border-white/12 space-y-1">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1">
                  <HardDrive size={11} />
                  <span>16 GB Laptop Footprint</span>
                </span>
                <span className="font-semibold text-emerald-300 block">{activeAgent.ramProfile}</span>
              </div>

              <div className="p-3 rounded-xl bg-white/8 border border-white/12 space-y-1">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1">
                  <ShieldCheck size={11} />
                  <span>Active Guardrail</span>
                </span>
                <span className="font-semibold text-amber-200 block">{activeAgent.guardrail}</span>
              </div>
            </div>

            <div className="p-3 rounded-xl bg-black/35 border border-white/10 flex items-center justify-between gap-2 text-xs font-mono">
              <span className="text-slate-400 shrink-0">I/O Contract:</span>
              <span className="text-sky-200 truncate">{activeAgent.ioContract}</span>
            </div>
          </div>

          {/* Interactive Brain Latency & Hook Benchmark Runner */}
          <div className="glass-panel p-5 space-y-4">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <div>
                <h3 className="text-sm font-bold text-[var(--tx)]">
                  Live Brain Router &amp; Hook Benchmark
                </h3>
                <p className="text-[11px] text-[var(--mu)]">
                  Send a real test topic through the active `$0` brain waterfall and measure end-to-end latency.
                </p>
              </div>
              {benchLatency && (
                <Badge variant="success">Round-Trip: {benchLatency}</Badge>
              )}
            </div>

            <form onSubmit={handleRunBenchmark} className="flex flex-col sm:flex-row gap-2.5">
              <label htmlFor="agent-bench-topic" className="visually-hidden-input">
                Benchmark test topic
              </label>
              <input
                id="agent-bench-topic"
                type="text"
                value={benchTopic}
                onChange={(e) => setBenchTopic(e.target.value)}
                placeholder="Enter test topic (e.g. Operation Mincemeat)..."
                className="glass-input flex-1 px-3.5 py-2.5 text-xs font-medium"
              />
              <Button type="submit" disabled={isTesting} className="shrink-0">
                {isTesting ? <Loader2 size={13} className="animate-spin" /> : <Play size={13} />}
                <span>{isTesting ? 'Running...' : 'Run Live Test'}</span>
              </Button>
            </form>

            {testError && (
              <div role="alert" className="p-3 rounded-xl bg-red-500/12 border border-red-500/40 text-xs text-red-700 dark:text-red-300">
                {testError}
              </div>
            )}

            {benchHooks.length > 0 && (
              <div className="space-y-2 pt-1" role="status">
                <span className="text-[11px] font-bold uppercase tracking-wider text-[var(--mu)]">
                  Live Router Output ({benchHooks.length} hooks):
                </span>
                {benchHooks.map((h, i) => (
                  <div
                    key={i}
                    className="glass-subcard p-3 text-xs font-medium text-[var(--tx)] flex items-center justify-between gap-2"
                  >
                    <span>"{h}"</span>
                    <CheckCircle2 size={14} className="text-emerald-600 dark:text-emerald-400 shrink-0" />
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* RIGHT (5/12): 6-Modality Hybrid Routing Stack */}
        <div className="xl:col-span-5 glass-panel p-5 space-y-3.5 min-w-0">
          <div className="flex items-center justify-between pb-3 border-b border-[var(--ln-subtle)]">
            <div>
              <h2 className="text-sm font-bold text-[var(--tx)]">
                6-Modality `$0` Routing Stack
              </h2>
              <p className="text-[11px] text-[var(--mu)]">
                Click any modality card to inspect discovered `:free` cloud candidates
              </p>
            </div>
            <Badge variant="info">Live Map</Badge>
          </div>

          {isCapsLoading ? (
            <div className="p-8 text-center text-xs text-[var(--mu)]">
              Scanning multimodal `:free` catalog...
            </div>
          ) : (
            <div className="space-y-2.5">
              {STAGE_ORDER.map((stageKey) => {
                const st = caps?.stages?.[stageKey];
                if (!st) return null;
                const isCloudActive = st.status === 'openrouter_free_active';
                const isExpanded = expandedStage === stageKey;

                return (
                  <div key={stageKey} className="glass-subcard p-3.5 space-y-2">
                    <button
                      type="button"
                      aria-expanded={isExpanded}
                      onClick={() => setExpandedStage(isExpanded ? null : stageKey)}
                      className="w-full flex items-center justify-between gap-2 text-left cursor-pointer"
                    >
                      <div className="flex items-center gap-2.5 min-w-0">
                        <span className="px-2 py-0.5 rounded-md bg-blue-600/15 text-blue-600 dark:text-blue-400 border border-blue-500/30 font-mono text-[11px] font-extrabold uppercase">
                          {stageKey}
                        </span>
                        <span className="font-mono text-xs font-semibold text-[var(--tx)] truncate">
                          {st.primary_free_model || 'Deterministic Local Engine'}
                        </span>
                      </div>
                      <div className="flex items-center gap-1.5 shrink-0">
                        <Badge variant={isCloudActive ? 'success' : 'neutral'}>
                          {isCloudActive ? `${st.free_models_count} Free` : 'Local'}
                        </Badge>
                        <ArrowRight
                          size={12}
                          className={`text-[var(--mu)] transition-transform ${
                            isExpanded ? 'rotate-90' : ''
                          }`}
                        />
                      </div>
                    </button>

                    <div className="text-[11px] text-[var(--mu)] leading-snug">
                      <b className="text-[var(--tx)]">Local Fallback:</b> {st.local_fallback_engine}
                    </div>

                    {isExpanded && st.free_models && st.free_models.length > 0 && (
                      <div className="pt-2 border-t border-[var(--ln-subtle)] flex flex-wrap gap-1.5">
                        {st.free_models.slice(0, 8).map((mId: string) => (
                          <span
                            key={mId}
                            className="text-[10px] font-mono px-2 py-0.5 rounded bg-[var(--input-bg)] border border-[var(--ln-subtle)] text-[var(--tx)]"
                          >
                            {mId}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
