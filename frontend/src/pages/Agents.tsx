import { useState } from 'react';
import { Badge, Button } from '../components/ui';
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
  AlertTriangle
} from 'lucide-react';
import { api, useOpenRouterCapabilities, useHouseQuotas } from '../api/client';

const STAGE_ORDER = ['text', 'vision', 'image', 'speech', 'audio', 'video'];

export default function Agents() {
  const [testResult, setTestResult] = useState<string | null>(null);
  const [testError, setTestError] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [isRefreshingCaps, setIsRefreshingCaps] = useState(false);

  const { data: caps, refetch: refetchCaps, isLoading: isCapsLoading } = useOpenRouterCapabilities();
  const { data: houseQuotas } = useHouseQuotas();

  const textModel = caps?.stages?.text?.primary_free_model || 'Spark-X2.5-4B (Local)';
  const visionModel = caps?.stages?.vision?.primary_free_model || 'FFmpeg + Whisper Local';
  const imageModel = caps?.stages?.image?.primary_free_model || 'Pollinations Flux ($0)';
  const speechModel = caps?.stages?.speech?.primary_free_model || 'Edge-TTS Neural ($0)';

  const agents = [
    {
      name: 'Niche Scorer',
      role: 'Evaluator',
      model: textModel,
      desc: 'Scores volume, competition, CPM, and evergreen potential with quantitative analysis.',
      icon: Target
    },
    {
      name: 'Viral Researcher',
      role: 'Fact Dossier & Hooks',
      model: textModel,
      desc: 'Retrieves real web/Wikipedia evidence dossiers and builds retention hooks without fabricated claims.',
      icon: Zap
    },
    {
      name: 'Documentary Scriptwriter',
      role: 'Planner',
      model: textModel,
      desc: 'Structures pacing beats, visual cues, and sound effects with Reflexion learned rules injected.',
      icon: Cpu
    },
    {
      name: 'Art Director & Vision',
      role: 'Visual Plates',
      model: `${imageModel} + Pillow`,
      desc: 'Composes archival typography plates, forensic cards, and AI imagery with 35mm film grades.',
      icon: Film
    },
    {
      name: 'Voice & Subtitle Engine',
      role: 'Audio & Captions',
      model: `${speechModel} + ASS`,
      desc: 'Renders neural voiceover normalized to -14 LUFS with millisecond karaoke captions.',
      icon: Volume2
    },
    {
      name: 'Video Assembler & Critic',
      role: 'Renderer & QA',
      model: `FFmpeg H.264 + ${visionModel}`,
      desc: 'Compiles 9:16 & 16:9 timelines using SHA-256 beat caching and single-worker CPU thermal lock.',
      icon: Film
    }
  ];

  const handleTestBrain = async () => {
    setIsTesting(true);
    setTestResult(null);
    setTestError(false);
    const start = Date.now();
    try {
      const res = await api.post('/api/jobs/brainstorm-hooks', { topic: 'AI Content Systems' });
      const elapsed = ((Date.now() - start) / 1000).toFixed(2);
      if (res?.hooks && res.hooks.length > 0) {
        setTestResult(`Success (${elapsed}s): "${res.hooks[0]}"`);
      } else {
        setTestResult(`Operational (${elapsed}s)`);
      }
    } catch (e: any) {
      setTestError(true);
      setTestResult(`Test failed: ${e.message}`);
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

  const totalRecords = houseQuotas?.data?.total_records;
  const targetTotal = houseQuotas?.data?.target_total;
  const breakerOnCooldown = caps?.circuit_breaker?.on_cooldown ?? false;

  return (
    <div className="animate-in fade-in min-h-full flex flex-col pb-8 space-y-5">
      {/* Header */}
      <div className="flex justify-between items-center flex-wrap gap-3 shrink-0">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-[var(--tx)]">
            Production Engines & Agents
          </h1>
          <div className="text-[var(--mu)] text-xs mt-0.5">
            Live OpenRouter strictly-free ($0.00) discovery map, local fallback routing, and subsystem telemetry.
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            onClick={handleRefreshCatalog}
            disabled={isRefreshingCaps}
          >
            <RefreshCw size={13} className={isRefreshingCaps ? 'animate-spin text-blue-500' : 'text-blue-600 dark:text-blue-400'} />
            <span>{isRefreshingCaps ? 'Scanning...' : 'Refresh Free Catalog'}</span>
          </Button>

          <Button
            variant="primary"
            onClick={handleTestBrain}
            disabled={isTesting}
          >
            {isTesting ? <Loader2 size={13} className="animate-spin" /> : <Activity size={13} />}
            <span>{isTesting ? 'Testing Latency...' : 'Test Engine Latency'}</span>
          </Button>
        </div>
      </div>

      {/* Unified 3-Zone Engine Telemetry Strip */}
      <div className="glass-panel p-4 grid grid-cols-1 md:grid-cols-3 gap-4 md:gap-0 md:divide-x divide-[var(--ln-subtle)]">
        <div className="md:pr-5 flex items-center justify-between">
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-wider text-[var(--mu)]">
              OpenRouter $0 Free Catalog
            </div>
            <div className="mt-1 flex items-baseline gap-2">
              <span className="text-2xl font-bold font-mono text-[var(--tx)]">
                {caps?.catalog_strictly_free_count ?? 0}
              </span>
              <span className="text-xs text-[var(--mu)] font-mono">
                / {caps?.catalog_total_scanned ?? 0} scanned
              </span>
            </div>
            <div className="text-[11px] text-emerald-600 dark:text-emerald-400 font-medium mt-0.5">
              {caps?.strict_zero_cost_lock ? '$0.00 Double-Lock Enforced' : 'Checking lock...'}
            </div>
          </div>
          <div className="w-9 h-9 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-600 dark:text-emerald-400 flex items-center justify-center">
            <ShieldCheck size={17} />
          </div>
        </div>

        <div className="md:px-5 flex items-center justify-between">
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-wider text-[var(--mu)]">
              Router & Circuit Breaker
            </div>
            <div className="mt-1 flex items-center gap-2">
              <span className="text-lg font-bold text-[var(--tx)]">
                {breakerOnCooldown ? 'Cooldown Active' : 'Healthy & Ready'}
              </span>
              <Badge variant={caps?.api_key_configured ? 'success' : 'warning'}>
                {caps?.api_key_configured ? 'API Key Loaded' : 'Local Only'}
              </Badge>
            </div>
            <div className="text-[11px] text-[var(--mu)] mt-0.5">
              {breakerOnCooldown
                ? `Resuming in ${Math.round(caps?.circuit_breaker?.remaining_seconds || 0)}s`
                : 'Auto-failover to Spark-X2.5-4B Local'}
            </div>
          </div>
          <div
            className={`w-9 h-9 rounded-xl border flex items-center justify-center ${
              breakerOnCooldown
                ? 'bg-amber-500/15 border-amber-500/30 text-amber-600 dark:text-amber-400'
                : 'bg-blue-600/15 border-blue-500/30 text-blue-600 dark:text-blue-400'
            }`}
          >
            {breakerOnCooldown ? <AlertTriangle size={17} /> : <Cpu size={17} />}
          </div>
        </div>

        <div className="md:pl-5 flex items-center justify-between">
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-wider text-[var(--mu)]">
              5-House Training Brain
            </div>
            <div className="mt-1 flex items-baseline gap-1.5">
              <span className="text-2xl font-bold font-mono text-[var(--tx)]">
                {totalRecords !== undefined ? totalRecords.toLocaleString() : '--'}
              </span>
              <span className="text-xs font-mono text-[var(--mu)]">
                / {targetTotal !== undefined ? targetTotal.toLocaleString() : '--'}
              </span>
            </div>
            <div className="text-[11px] text-[var(--mu)] mt-0.5">
              Harvester Key Burn: {caps?.harvester_openrouter_enabled ? 'Enabled' : 'Disabled (HF Direct)'}
            </div>
          </div>
          <div className="w-9 h-9 rounded-xl bg-amber-500/15 border border-amber-500/30 text-amber-600 dark:text-amber-400 flex items-center justify-center">
            <Layers size={17} />
          </div>
        </div>
      </div>

      {/* Latency Test Feedback Banner */}
      {testResult && (
        <div
          className={`p-3.5 rounded-xl border text-xs flex items-center gap-2 font-medium ${
            testError
              ? 'bg-red-500/12 border-red-500/40 text-red-700 dark:text-red-300'
              : 'bg-emerald-500/12 border-emerald-500/40 text-emerald-700 dark:text-emerald-300'
          }`}
        >
          {testError ? (
            <AlertTriangle size={14} className="shrink-0" />
          ) : (
            <CheckCircle2 size={14} className="shrink-0" />
          )}
          <span>
            <b>Engine Response:</b> {testResult}
          </span>
        </div>
      )}

      {/* Live 6-Stage Hybrid Routing Matrix */}
      <div className="glass-panel !p-0 overflow-hidden">
        <div className="px-5 py-3.5 border-b border-[var(--ln-subtle)] flex items-center justify-between flex-wrap gap-2">
          <div>
            <h2 className="text-sm font-bold text-[var(--tx)]">6-Stage Hybrid Model Routing Matrix</h2>
            <p className="text-[11px] text-[var(--mu)]">
              Live OpenRouter `:free` catalog discovery mapped against deterministic local workstation engines.
            </p>
          </div>
          <Badge variant="info">Live Telemetry</Badge>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-xs border-collapse">
            <thead className="bg-[var(--table-head)]">
              <tr>
                <th className="p-3 text-left text-[11px] font-semibold uppercase tracking-wider text-[var(--mu)] border-b border-[var(--ln-subtle)]">
                  Stage
                </th>
                <th className="p-3 text-left text-[11px] font-semibold uppercase tracking-wider text-[var(--mu)] border-b border-[var(--ln-subtle)]">
                  Routing Mode
                </th>
                <th className="p-3 text-left text-[11px] font-semibold uppercase tracking-wider text-[var(--mu)] border-b border-[var(--ln-subtle)]">
                  Primary $0 Cloud Model
                </th>
                <th className="p-3 text-left text-[11px] font-semibold uppercase tracking-wider text-[var(--mu)] border-b border-[var(--ln-subtle)]">
                  Local Fallback Engine
                </th>
              </tr>
            </thead>
            <tbody>
              {isCapsLoading ? (
                <tr>
                  <td colSpan={4} className="p-6 text-center text-[var(--mu)]">
                    Scanning live OpenRouter `:free` capabilities...
                  </td>
                </tr>
              ) : (
                STAGE_ORDER.map((stageKey) => {
                  const st = caps?.stages?.[stageKey];
                  if (!st) return null;
                  const isCloudActive = st.status === 'openrouter_free_active';

                  return (
                    <tr
                      key={stageKey}
                      className="border-b border-[var(--ln-subtle)] hover:bg-[var(--row-hover)] transition-colors"
                    >
                      <td className="p-3 font-bold uppercase tracking-wider text-[var(--tx)]">
                        {stageKey}
                      </td>
                      <td className="p-3">
                        <Badge variant={isCloudActive ? 'success' : 'neutral'}>
                          {isCloudActive
                            ? `${st.free_models_count} Free Cloud`
                            : 'Local Only'}
                        </Badge>
                      </td>
                      <td className="p-3 font-mono text-[11px] text-[var(--tx)]">
                        {st.primary_free_model || 'Auto-skip to local'}
                      </td>
                      <td className="p-3 text-[11px] text-[var(--mu)]">
                        {st.local_fallback_engine}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Grid of 6 Core Production Agents */}
      <div>
        <h2 className="text-sm font-bold text-[var(--tx)] mb-3">Core Production Subsystems</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {agents.map((agent) => {
            const Icon = agent.icon;
            return (
              <div
                key={agent.name}
                className="glass-panel p-5 flex flex-col justify-between gap-4 hover:border-blue-500/45 transition-all"
              >
                <div>
                  <div className="flex justify-between items-start mb-2.5">
                    <div className="flex items-center gap-3">
                      <div className="p-2.5 rounded-xl bg-blue-600/15 text-blue-600 dark:text-blue-400 border border-blue-500/25">
                        <Icon size={17} />
                      </div>
                      <div>
                        <b className="font-bold text-sm text-[var(--tx)] block">{agent.name}</b>
                        <span className="text-[11px] text-[var(--mu)]">{agent.role}</span>
                      </div>
                    </div>
                    <Badge variant="success">Operational</Badge>
                  </div>

                  <p className="text-xs text-[var(--mu)] mt-2 leading-relaxed">{agent.desc}</p>
                </div>

                <div className="pt-3 border-t border-[var(--ln-subtle)] flex justify-between items-center gap-2 text-xs">
                  <span className="text-[var(--mu)] shrink-0">Active Engine:</span>
                  <span className="font-mono text-[11px] text-[var(--tx)] font-semibold truncate">
                    {agent.model}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
