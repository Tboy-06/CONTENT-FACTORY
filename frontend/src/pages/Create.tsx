import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Zap,
  ListPlus,
  Loader2,
  Film,
  CheckCircle2,
  ArrowRight,
  Trash2,
  AlertCircle,
  Upload,
  Image as ImageIcon,
  X,
  Sparkles,
  ShieldAlert,
  Smile,
  Flame,
  Clapperboard,
  Cpu,
  Download,
  SlidersHorizontal
} from 'lucide-react';
import { Button, Card, Badge } from '../components/ui';
import {
  useCreateInstantJob,
  useBrainstormHooks,
  useJobs,
  useDeleteJob,
  useClearAllJobs,
  useUploadAnchor,
  useSpend,
  api
} from '../api/client';
import DirectorChatDrawer from '../components/DirectorChatDrawer';

const stylePresets = [
  { id: 'Dark Documentary', label: 'Dark Documentary', desc: 'Moody lighting, anamorphic lens, 35mm grain' },
  { id: 'Vintage 35mm', label: 'Vintage 35mm', desc: 'Warm Kodak Portra tones, subtle film halation' },
  { id: 'Cyberpunk Neo-Noir', label: 'Cyberpunk Neo-Noir', desc: 'Rain-slicked dark atmosphere, neon cyan rim' },
  { id: 'Minimalist Studio', label: 'Minimalist Studio', desc: 'Clean neutral backdrop, high-key editorial' }
];

const voices = [
  { id: 'en-US-AriaNeural', label: 'Aria (Female, Clear & Polished)' },
  { id: 'en-US-ChristopherNeural', label: 'Christopher (Male, Deep Storytelling)' },
  { id: 'en-US-GuyNeural', label: 'Guy (Male, Conversational)' },
  { id: 'en-US-AndrewNeural', label: 'Andrew (Male, Warm & Authoritative)' }
];

const genres = [
  { id: 'auto', label: 'Auto Detect', Icon: Cpu, desc: 'Auto-detect genre physics from topic', cpm: 'Dynamic pacing' },
  { id: 'crime_doc', label: 'Crime / Doc', Icon: ShieldAlert, desc: 'Forensic canvas, 18-24 cuts/min, radio voice filter', cpm: '18-24 cuts/min' },
  { id: 'comedy_skit', label: 'Comedy / Skit', Icon: Smile, desc: '25-35 cuts/min, 1.35x snap-zooms, 0.3s dead air', cpm: '25-35 cuts/min' },
  { id: 'action_hype', label: 'Action / Hype', Icon: Flame, desc: '40-55 cuts/min, handheld camera-shake, slam titles', cpm: '40-55 cuts/min' },
  { id: 'movie_cinema', label: 'Movie / Cinema', Icon: Clapperboard, desc: '12-18 cuts/min, 2.35:1 letterbox, 35mm scope', cpm: '12-18 cuts/min' },
  { id: 'viral_edu', label: 'Viral Edu', Icon: Zap, desc: '28-38 cuts/min, stat counters & workflow cards', cpm: '28-38 cuts/min' }
];

const pipelineSteps = [
  { id: 1, name: 'Writing Script', stage: 'SCRIPT' },
  { id: 2, name: 'Generating Voice & Subs', stage: 'AUDIO' },
  { id: 3, name: 'Rendering Visual Plates', stage: 'PLATES' },
  { id: 4, name: 'FFmpeg Video Render', stage: 'FFMPEG' }
];

export default function Create() {
  const navigate = useNavigate();
  const [topic, setTopic] = useState('');
  const [genre, setGenre] = useState('auto');
  const [stylePreset, setStylePreset] = useState('Dark Documentary');
  const [voice, setVoice] = useState('en-US-AriaNeural');
  const [aspectRatio, setAspectRatio] = useState('9:16');
  const [duration, setDuration] = useState('45s');
  const [anchorFile, setAnchorFile] = useState<File | null>(null);
  const [anchorPreview, setAnchorPreview] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [activeStepIndex, setActiveStepIndex] = useState(0);
  const [suggestedHooks, setSuggestedHooks] = useState<string[]>([]);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [isDirectorChatOpen, setIsDirectorChatOpen] = useState(false);

  const { data: recentJobs = [] } = useJobs();
  const { data: liveSpend } = useSpend();
  const instantMutation = useCreateInstantJob();
  const brainstormMutation = useBrainstormHooks();
  const deleteJobMutation = useDeleteJob();
  const clearAllMutation = useClearAllJobs();
  const uploadAnchorMutation = useUploadAnchor();

  const selectedGenreObj = genres.find((g) => g.id === genre) || genres[0];
  const spentAmount = typeof liveSpend === 'number' ? liveSpend : 0;

  const handleBrainstorm = async () => {
    const query = topic.trim() || 'Stoic Mindset';
    try {
      const hooks = await brainstormMutation.mutateAsync(query);
      setSuggestedHooks(hooks);
    } catch (e) {
      console.error(e);
    }
  };

  const handleGenerate = async (targetTopic?: string) => {
    const finalTopic = (targetTopic || topic).trim();
    if (!finalTopic || isGenerating) return;

    setIsGenerating(true);
    setErrorMsg(null);
    setActiveStepIndex(0);

    const stageMap: Record<string, number> = {
      SCRIPT: 0,
      AUDIO: 1,
      PLATES: 2,
      FFMPEG: 3,
      QC1: 4
    };

    try {
      const res = await instantMutation.mutateAsync({
        topic: finalTopic,
        voice,
        style_preset: stylePreset,
        aspect_ratio: aspectRatio,
        duration,
        genre
      });

      const jobId = res.id;

      if (anchorFile) {
        try {
          await uploadAnchorMutation.mutateAsync({ jobId, file: anchorFile });
        } catch (uploadErr) {
          console.warn('Could not attach visual anchor:', uploadErr);
        }
      }

      const startTime = Date.now();

      const interval = setInterval(async () => {
        try {
          const jobs = await api.get('/api/jobs');
          const currentJob = jobs.find((j: any) => j.id === jobId);

          if (currentJob) {
            if (currentJob.current_stage && currentJob.current_stage in stageMap) {
              setActiveStepIndex(stageMap[currentJob.current_stage]);
            }

            const hasVideo = currentJob.assets?.some((a: any) => a.type === 'VIDEO' || a.type === 'video');

            if ((currentJob.current_stage === 'QC1' || currentJob.status === 'COMPLETED') && hasVideo) {
              clearInterval(interval);
              setActiveStepIndex(4);
              setTimeout(() => navigate(`/qc1/${jobId}`), 400);
            } else if (currentJob.status === 'FAILED') {
              clearInterval(interval);
              setIsGenerating(false);
              setErrorMsg(
                currentJob.current_stage
                  ? `Pipeline failed at stage: ${currentJob.current_stage}`
                  : 'Generation encountered an error. Please try again.'
              );
            }
          }
        } catch {
          // ignore transient poll errors
        }

        if (Date.now() - startTime > 360000) {
          clearInterval(interval);
          setIsGenerating(false);
          setErrorMsg('Generation timed out. Check Pipeline tab for background progress.');
        }
      }, 1000);
    } catch (e: any) {
      console.error(e);
      setIsGenerating(false);
      setErrorMsg(e?.message || 'Failed to start video generation.');
    }
  };

  return (
    <div className="animate-in fade-in min-h-full flex flex-col pb-12 space-y-5 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex justify-between items-center flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-[var(--tx)]">Video Launchpad</h1>
          <p className="text-xs text-[var(--mu)] mt-0.5">
            Zero-cost documentary & vertical short assembly engine (Edge-TTS + FFmpeg + Pillow + Beat Cache).
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="success">Zero API Cost</Badge>
          <Button
            onClick={() => setIsDirectorChatOpen(true)}
            className="flex items-center gap-1.5 text-xs font-semibold !py-2 !px-3.5 bg-amber-500 hover:bg-amber-400 text-slate-950 border-amber-400 shadow-sm rounded-xl transition-all"
            title="Open AI Director Command Studio to clone styles or analyze videos"
          >
            <Sparkles size={14} className="text-slate-950" />
            <span>AI Director Studio</span>
          </Button>
        </div>
      </div>

      {/* Unified 3-Zone Studio Telemetry Strip */}
      <div className="glass-panel p-4 grid grid-cols-1 md:grid-cols-3 gap-4 md:gap-0 md:divide-x divide-[var(--ln-subtle)]">
        <div className="md:pr-5">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-[var(--mu)]">
            Selected Editing Physics
          </div>
          <div className="mt-1 flex items-baseline gap-2">
            <span className="text-lg font-bold text-[var(--tx)]">{selectedGenreObj.label}</span>
            <span className="text-[11px] font-mono font-semibold text-blue-600 dark:text-blue-400">
              {selectedGenreObj.cpm}
            </span>
          </div>
          <div className="text-[11px] text-[var(--mu)] truncate mt-0.5">{selectedGenreObj.desc}</div>
        </div>

        <div className="md:px-5">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-[var(--mu)]">
            Output Target & Grade
          </div>
          <div className="mt-1 flex items-baseline gap-2">
            <span className="text-lg font-bold text-[var(--tx)]">
              {aspectRatio} · {duration}
            </span>
            <Badge variant="info">{stylePreset}</Badge>
          </div>
          <div className="text-[11px] text-[var(--mu)] mt-0.5">
            Voice: {voice.split('-')[2]?.replace('Neural', '') || 'Aria'} Neural (-14 LUFS)
          </div>
        </div>

        <div className="md:pl-5 flex items-center justify-between gap-3">
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-wider text-[var(--mu)]">
              Session Spend & Library
            </div>
            <div className="mt-1 flex items-baseline gap-2">
              <span className="text-lg font-bold font-mono text-emerald-600 dark:text-emerald-400">
                ${spentAmount.toFixed(2)}
              </span>
              <span className="text-xs font-medium text-[var(--mu)]">
                ({recentJobs.length} {recentJobs.length === 1 ? 'project' : 'projects'})
              </span>
            </div>
            <div className="text-[11px] text-[var(--mu)] mt-0.5">Beat-Level SHA-256 Cache Active</div>
          </div>
          <div className="w-10 h-10 rounded-xl bg-blue-600/15 border border-blue-500/30 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0">
            <SlidersHorizontal size={18} />
          </div>
        </div>
      </div>

      {/* Main Frosted Launchpad Card */}
      <Card className="!p-6 space-y-6">
        {/* 1. Topic Input Box & Viral Hook Generator */}
        <div className="space-y-2">
          <label className="text-xs font-bold uppercase tracking-wider text-[var(--tx)]">
            1. Topic or Investigation Idea
          </label>
          <div className="flex flex-col sm:flex-row gap-2.5">
            <input
              type="text"
              placeholder='e.g. "CIA Project Azorian" or "3 psychological tricks people use on you"'
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleGenerate()}
              disabled={isGenerating}
              className="glass-input flex-1 px-4 py-3 text-sm"
            />
            <Button
              variant="secondary"
              onClick={handleBrainstorm}
              disabled={brainstormMutation.isPending || isGenerating}
              className="whitespace-nowrap !py-3 !px-4 text-xs font-semibold"
            >
              {brainstormMutation.isPending ? (
                <Loader2 size={14} className="animate-spin text-blue-500" />
              ) : (
                <ListPlus size={14} className="text-blue-600 dark:text-blue-400" />
              )}
              <span>Generate 3 Hooks</span>
            </Button>
          </div>

          {/* Suggested Hook Angles */}
          {suggestedHooks.length > 0 && (
            <div className="space-y-1.5 pt-1">
              <span className="text-[11px] font-medium text-[var(--mu)]">
                Select a generated hook to launch immediately:
              </span>
              <div className="grid grid-cols-1 gap-2">
                {suggestedHooks.map((hook, i) => (
                  <button
                    key={i}
                    onClick={() => {
                      setTopic(hook);
                      handleGenerate(hook);
                    }}
                    disabled={isGenerating}
                    className="glass-subcard text-left text-xs p-3 flex items-center justify-between group cursor-pointer"
                  >
                    <span className="font-medium text-[var(--tx)]">"{hook}"</span>
                    <ArrowRight
                      size={14}
                      className="text-blue-600 dark:text-blue-400 opacity-60 group-hover:opacity-100 group-hover:translate-x-0.5 transition-all shrink-0 ml-2"
                    />
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* 2. Genre Editing Physics Pill Selector */}
        <div className="space-y-2.5 pt-1">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <label className="text-xs font-bold uppercase tracking-wider text-[var(--tx)]">
              2. Genre Editing Physics
            </label>
            <span className="text-[11px] text-amber-700 dark:text-amber-400 font-mono font-medium">
              {selectedGenreObj.desc}
            </span>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5">
            {genres.map((g) => {
              const active = genre === g.id;
              const GenreIcon = g.Icon;
              return (
                <button
                  key={g.id}
                  type="button"
                  onClick={() => setGenre(g.id)}
                  disabled={isGenerating}
                  className={`px-3 py-2.5 rounded-xl border text-xs font-semibold flex items-center gap-2 transition-all cursor-pointer ${
                    active
                      ? 'bg-blue-600 border-blue-500 text-white shadow-md shadow-blue-600/25'
                      : 'bg-[var(--gl2)] border-[var(--input-border)] text-[var(--mu)] hover:text-[var(--tx)] hover:border-blue-500/45'
                  }`}
                >
                  <GenreIcon size={14} className="shrink-0" />
                  <span className="truncate">{g.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* 3-6. Style Preset, Voice, Format & Duration Controls */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
          <div className="space-y-1.5">
            <label className="text-xs font-bold uppercase tracking-wider text-[var(--tx)]">
              3. Visual Aesthetic Preset
            </label>
            <select
              value={stylePreset}
              onChange={(e) => setStylePreset(e.target.value)}
              disabled={isGenerating}
              className="glass-input w-full px-3.5 py-2.5 text-xs cursor-pointer"
            >
              {stylePresets.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.label} - {p.desc}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-bold uppercase tracking-wider text-[var(--tx)]">
              4. Voice Narration (Edge-TTS)
            </label>
            <select
              value={voice}
              onChange={(e) => setVoice(e.target.value)}
              disabled={isGenerating}
              className="glass-input w-full px-3.5 py-2.5 text-xs cursor-pointer"
            >
              {voices.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.label}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-bold uppercase tracking-wider text-[var(--tx)]">
              5. Format & Ratio
            </label>
            <select
              value={aspectRatio}
              onChange={(e) => setAspectRatio(e.target.value)}
              disabled={isGenerating}
              className="glass-input w-full px-3.5 py-2.5 text-xs cursor-pointer"
            >
              <option value="9:16">9:16 Vertical (Shorts, Reels, TikTok)</option>
              <option value="16:9">16:9 Horizontal (YouTube Channel, Video Essay)</option>
            </select>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-bold uppercase tracking-wider text-[var(--tx)]">
              6. Target Duration
            </label>
            <select
              value={duration}
              onChange={(e) => setDuration(e.target.value)}
              disabled={isGenerating}
              className="glass-input w-full px-3.5 py-2.5 text-xs cursor-pointer"
            >
              <option value="45s">45 Seconds (High-Tempo Short)</option>
              <option value="60s">60 Seconds (Full Short)</option>
              <option value="3m">3 Minutes (Standard Documentary Essay)</option>
              <option value="5m">5 Minutes (Deep Investigation)</option>
            </select>
          </div>

          {/* 7. Custom Visual Anchor (Optional Style Reference) */}
          <div className="col-span-full space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold uppercase tracking-wider text-[var(--tx)] flex items-center gap-1.5">
                <ImageIcon size={13} className="text-blue-600 dark:text-blue-400" />
                <span>7. Visual Anchor / Reference Image (Optional)</span>
              </label>
              {anchorFile && (
                <Badge variant="success">Anchor Attached</Badge>
              )}
            </div>

            {anchorPreview ? (
              <div className="glass-subcard p-2.5 flex items-center justify-between border-blue-500/40">
                <div className="flex items-center gap-3">
                  <img
                    src={anchorPreview}
                    alt="Anchor preview"
                    className="w-12 h-12 rounded-lg object-cover border border-[var(--input-border)]"
                  />
                  <div>
                    <div className="text-xs font-semibold text-[var(--tx)] truncate max-w-[240px]">
                      {anchorFile?.name}
                    </div>
                    <div className="text-[11px] text-[var(--mu)] font-mono">
                      {anchorFile?.size ? (anchorFile.size / 1024).toFixed(0) : 0} KB · Style Reference
                    </div>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setAnchorFile(null);
                    setAnchorPreview(null);
                  }}
                  className="p-1.5 rounded-lg text-[var(--mu)] hover:text-red-500 hover:bg-red-500/10 transition-colors cursor-pointer"
                  title="Remove visual anchor"
                >
                  <X size={15} />
                </button>
              </div>
            ) : (
              <label className="cursor-pointer border border-dashed border-[var(--input-border)] hover:border-blue-500/70 rounded-xl p-3.5 bg-[var(--input-bg)] hover:bg-[var(--gl2)] transition-all flex items-center justify-center gap-2.5 text-[var(--mu)] hover:text-[var(--tx)]">
                <Upload size={14} className="text-blue-600 dark:text-blue-400" />
                <span className="text-xs font-medium">
                  Upload style reference image (.png, .jpg) to anchor scene plates
                </span>
                <input
                  type="file"
                  accept="image/png,image/jpeg,image/webp"
                  className="hidden"
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    if (f) {
                      setAnchorFile(f);
                      setAnchorPreview(URL.createObjectURL(f));
                    }
                  }}
                />
              </label>
            )}
          </div>
        </div>

        {/* Launch Action Button */}
        <div className="pt-1">
          <Button
            onClick={() => handleGenerate()}
            disabled={!topic.trim() || isGenerating}
            className="w-full !py-3.5 text-sm font-bold flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl shadow-lg shadow-blue-600/25 transition-all"
          >
            {isGenerating ? <Loader2 size={18} className="animate-spin" /> : <Zap size={18} />}
            <span>
              {isGenerating
                ? 'Assembling Documentary Pipeline...'
                : `Generate ${aspectRatio === '16:9' ? '16:9 Widescreen Documentary' : '9:16 Vertical Short'} (${duration})`}
            </span>
          </Button>
        </div>

        {/* Live 4-Step Status Bar */}
        {isGenerating && (
          <div className="pt-4 space-y-3 border-t border-[var(--ln-subtle)]">
            <div className="flex items-center justify-between text-xs font-semibold text-[var(--tx)]">
              <span>Assembly Pipeline Progress</span>
              <span className="font-mono text-blue-600 dark:text-blue-400">
                Step {Math.min(activeStepIndex + 1, 4)} of 4
              </span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
              {pipelineSteps.map((step, idx) => {
                const isPast = idx < activeStepIndex;
                const isCurrent = idx === activeStepIndex;
                return (
                  <div
                    key={step.id}
                    className={`p-3 rounded-xl border text-xs flex flex-col justify-between transition-all ${
                      isPast
                        ? 'bg-emerald-500/15 border-emerald-500/40 text-emerald-700 dark:text-emerald-300'
                        : isCurrent
                        ? 'bg-blue-600/15 border-blue-500 text-[var(--tx)] shadow-sm animate-pulse'
                        : 'bg-[var(--gl2)] border-[var(--ln-subtle)] text-[var(--mu)]'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-mono text-[10px] font-bold">0{step.id}</span>
                      {isPast ? (
                        <CheckCircle2 size={13} className="text-emerald-600 dark:text-emerald-400" />
                      ) : isCurrent ? (
                        <Loader2 size={13} className="animate-spin text-blue-600 dark:text-blue-400" />
                      ) : null}
                    </div>
                    <span className="font-semibold text-[11px] leading-tight">{step.name}</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Error Alert */}
        {errorMsg && (
          <div className="p-3.5 bg-red-500/12 border border-red-500/40 rounded-xl flex items-center justify-between text-xs text-red-700 dark:text-red-300">
            <div className="flex items-center gap-2">
              <AlertCircle size={16} className="text-red-600 dark:text-red-400 shrink-0" />
              <span className="font-medium">{errorMsg}</span>
            </div>
            <button
              onClick={() => setErrorMsg(null)}
              className="text-red-600 dark:text-red-300 hover:opacity-75 ml-2 text-base font-bold cursor-pointer"
            >
              &times;
            </button>
          </div>
        )}
      </Card>

      {/* Recent Video Projects Quick Access */}
      {recentJobs.length > 0 && (
        <div className="space-y-3 pt-1">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-[var(--tx)]">Recent Videos Ready for Review</h2>
            <div className="flex items-center gap-3">
              <span className="text-xs font-mono text-[var(--mu)]">{recentJobs.length} Projects Total</span>
              <button
                onClick={() => {
                  if (confirm('Clear all recent jobs?')) {
                    clearAllMutation.mutate();
                  }
                }}
                disabled={clearAllMutation.isPending}
                className="text-[11px] font-semibold text-[var(--mu)] hover:text-red-600 dark:hover:text-red-400 flex items-center gap-1 transition-colors cursor-pointer"
                title="Clear all job history"
              >
                <Trash2 size={12} />
                <span>Clear All</span>
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {recentJobs.slice(0, 9).map((j: any) => {
              const videoAsset = j.assets?.find((a: any) => a.type === 'VIDEO' || a.type === 'video');
              const hasVideo = !!videoAsset;
              return (
                <div
                  key={j.id}
                  onClick={() => navigate(`/qc1/${j.id}`)}
                  className="glass-subcard p-3.5 cursor-pointer flex items-center justify-between group relative hover:-translate-y-0.5"
                >
                  <div className="flex items-center gap-3 truncate pr-2">
                    <div className="w-9 h-9 rounded-xl bg-blue-600/15 text-blue-600 dark:text-blue-400 border border-blue-500/25 flex items-center justify-center shrink-0">
                      <Film size={16} />
                    </div>
                    <div className="truncate">
                      <div className="text-xs font-bold text-[var(--tx)] group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors truncate">
                        {j.niche}
                      </div>
                      <div className="text-[10px] text-[var(--mu)] font-mono mt-0.5">
                        Job #{j.id} · {j.current_stage || j.status}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-1.5 shrink-0">
                    <Badge variant={hasVideo ? 'success' : j.status === 'FAILED' ? 'danger' : 'warning'}>
                      {hasVideo ? (j.config?.format || '9:16') : j.status === 'FAILED' ? 'Failed' : 'Pending'}
                    </Badge>
                    {hasVideo && (
                      <a
                        href={`/api/jobs/${j.id}/export`}
                        onClick={(e) => e.stopPropagation()}
                        className="p-1.5 rounded-lg text-[var(--mu)] hover:text-blue-600 dark:hover:text-blue-400 hover:bg-blue-500/10 transition-colors"
                        title="Download Publish-Ready .ZIP Pack"
                      >
                        <Download size={13} />
                      </a>
                    )}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        deleteJobMutation.mutate(j.id);
                      }}
                      className="opacity-0 group-hover:opacity-100 p-1.5 text-[var(--mu)] hover:text-red-500 transition-all rounded-lg hover:bg-red-500/10 cursor-pointer"
                      title="Delete this project"
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* AI Director Command Studio Drawer */}
      <DirectorChatDrawer isOpen={isDirectorChatOpen} onClose={() => setIsDirectorChatOpen(false)} />
    </div>
  );
}
