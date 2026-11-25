import { useState, useRef } from 'react';
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
  ShieldAlert,
  Smile,
  Flame,
  Clapperboard,
  Cpu,
  Download,
  Mic,
  Monitor,
  Smartphone,
  Copy,
  Check,
  Palette,
  Layers
} from 'lucide-react';
import { Button, Badge, ConfirmDialog } from '../components/ui';
import {
  useCreateInstantJob,
  useBrainstormHooks,
  useJobs,
  useDeleteJob,
  useClearAllJobs,
  useUploadAnchor,
  useSpend,
  useVideoGenStatus,
  api
} from '../api/client';
import DirectorChatDrawer from '../components/DirectorChatDrawer';

const stylePresets = [
  {
    id: 'Dark Documentary',
    label: 'Dark Documentary',
    desc: 'Anamorphic shadows, cold cobalt contrast, 35mm grain',
    swatch: 'from-slate-950 via-blue-950 to-slate-900 border-sky-400/40',
    monitorBg: 'radial-gradient(120% 90% at 80% 15%, rgba(56,189,248,0.28) 0%, transparent 55%), linear-gradient(160deg, #050b16 0%, #0f1f38 55%, #070d19 100%)'
  },
  {
    id: 'Vintage 35mm',
    label: 'Vintage 35mm',
    desc: 'Warm Kodak Portra halation, archival amber highlights',
    swatch: 'from-stone-900 via-amber-900 to-stone-950 border-amber-400/45',
    monitorBg: 'radial-gradient(110% 90% at 80% 20%, rgba(251,191,36,0.32) 0%, transparent 58%), linear-gradient(160deg, #1c140d 0%, #422611 55%, #17110b 100%)'
  },
  {
    id: 'Cyberpunk Neo-Noir',
    label: 'Teal Split Noir',
    desc: 'Rain-slicked cyan rim lighting, deep obsidian blacks',
    swatch: 'from-slate-950 via-teal-900 to-cyan-950 border-teal-400/45',
    monitorBg: 'radial-gradient(115% 90% at 85% 15%, rgba(20,184,166,0.35) 0%, transparent 58%), linear-gradient(160deg, #04131a 0%, #0d3b46 55%, #051017 100%)'
  },
  {
    id: 'Minimalist Studio',
    label: 'Clean Editorial',
    desc: 'Neutral studio key light, crisp daylight contrast',
    swatch: 'from-slate-700 via-slate-600 to-slate-800 border-slate-300/50',
    monitorBg: 'radial-gradient(120% 90% at 75% 15%, rgba(226,232,240,0.28) 0%, transparent 60%), linear-gradient(160deg, #1e293b 0%, #334155 55%, #0f172a 100%)'
  }
];

const voices = [
  {
    id: 'en-US-AndrewMultilingualNeural',
    shortLabel: 'Andrew Multilingual',
    badge: 'Trailer Male',
    desc: 'Warm broadcast narrator (-14 LUFS)'
  },
  {
    id: 'en-US-AvaMultilingualNeural',
    shortLabel: 'Ava Multilingual',
    badge: 'Doc Female',
    desc: 'Expressive investigative storyteller'
  },
  {
    id: 'en-US-BrianMultilingualNeural',
    shortLabel: 'Brian Multilingual',
    badge: 'Editorial Male',
    desc: 'Crisp high-tempo explainer delivery'
  },
  {
    id: 'am_michael',
    shortLabel: 'Kokoro-82M Michael',
    badge: '100% Offline CPU',
    desc: 'Local int8 ONNX weights (0 network needed)'
  }
];

const genres = [
  {
    id: 'auto',
    label: 'Auto Detect',
    Icon: Cpu,
    desc: 'Matches cut cadence & color treatment to topic',
    cpm: 'Dynamic'
  },
  {
    id: 'crime_doc',
    label: 'Crime / Doc',
    Icon: ShieldAlert,
    desc: 'Forensic dossiers, redacted highlights & radio EQ',
    cpm: '18-24 cpm'
  },
  {
    id: 'viral_edu',
    label: 'Viral Edu',
    Icon: Zap,
    desc: 'Verified stat counters, workflow cards & focus zoom',
    cpm: '28-38 cpm'
  },
  {
    id: 'movie_cinema',
    label: 'Movie / Cinema',
    Icon: Clapperboard,
    desc: '2.35:1 letterbox bars, 35mm grain & slow push-in',
    cpm: '12-18 cpm'
  },
  {
    id: 'action_hype',
    label: 'Action / Hype',
    Icon: Flame,
    desc: 'Rapid impact cuts, kinetic shake & bold slam titles',
    cpm: '40-55 cpm'
  },
  {
    id: 'comedy_skit',
    label: 'Comedy / Skit',
    Icon: Smile,
    desc: '1.35x punch-ins with tight 0.3s dead-air trimming',
    cpm: '25-35 cpm'
  }
];

const durations = [
  { id: '45s', label: '45s', sub: 'Fast Short' },
  { id: '60s', label: '60s', sub: 'Full Short' },
  { id: '3m', label: '3m', sub: 'Essay' },
  { id: '5m', label: '5m', sub: 'Deep Dive' }
];

const quickStarters = [
  'CIA Project Azorian',
  'The 1971 D.B. Cooper Hijacking',
  'Operation Mincemeat Declassified',
  'Why Planes Avoid Tibet'
];

const pipelineSteps = [
  { id: 1, name: 'Research & Script', stage: 'SCRIPT' },
  { id: 2, name: 'Voice & Karaoke ASS', stage: 'AUDIO' },
  { id: 3, name: 'Archival & AI Plates', stage: 'PLATES' },
  { id: 4, name: 'FFmpeg Pass 2 Render', stage: 'FFMPEG' }
];

export default function Create() {
  const navigate = useNavigate();
  const topicInputRef = useRef<HTMLInputElement | null>(null);

  const [topic, setTopic] = useState('');
  const [topicError, setTopicError] = useState<string | null>(null);
  const [topicTouched, setTopicTouched] = useState(false);
  const [genre, setGenre] = useState('auto');
  const [stylePreset, setStylePreset] = useState('Dark Documentary');
  const [voice, setVoice] = useState('en-US-AndrewMultilingualNeural');
  const [aspectRatio, setAspectRatio] = useState('9:16');
  const [duration, setDuration] = useState('45s');
  const [anchorFile, setAnchorFile] = useState<File | null>(null);
  const [anchorPreview, setAnchorPreview] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [activeStepIndex, setActiveStepIndex] = useState(0);
  const [suggestedHooks, setSuggestedHooks] = useState<string[]>([]);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [isDirectorChatOpen, setIsDirectorChatOpen] = useState(false);
  const [isConfirmClearOpen, setIsConfirmClearOpen] = useState(false);
  const [flowCopied, setFlowCopied] = useState(false);

  const { data: recentJobs = [] } = useJobs();
  const { data: liveSpend } = useSpend();
  const { data: videoGenStatus } = useVideoGenStatus();
  const instantMutation = useCreateInstantJob();
  const brainstormMutation = useBrainstormHooks();
  const deleteJobMutation = useDeleteJob();
  const clearAllMutation = useClearAllJobs();
  const uploadAnchorMutation = useUploadAnchor();

  const selectedGenreObj = genres.find((g) => g.id === genre) || genres[0];
  const selectedStyleObj = stylePresets.find((s) => s.id === stylePreset) || stylePresets[0];
  const selectedVoiceObj = voices.find((v) => v.id === voice) || voices[0];
  const spentAmount = typeof liveSpend === 'number' ? liveSpend : 0;

  const handleBrainstorm = async () => {
    const query = topic.trim() || 'Declassified Cold War Operations';
    try {
      const hooks = await brainstormMutation.mutateAsync(query);
      setSuggestedHooks(hooks);
    } catch (e) {
      console.error(e);
    }
  };

  const handleGenerate = async (targetTopic?: string) => {
    if (isGenerating) return;
    const finalTopic = (targetTopic ?? topic).trim();
    if (!finalTopic) {
      setTopicTouched(true);
      setTopicError('Enter a documentary topic, historical event, or hook before launching.');
      topicInputRef.current?.focus();
      return;
    }

    setTopicError(null);
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
    <div className="animate-in fade-in min-h-full flex flex-col pb-10 space-y-5">
      {/* Studio Command Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <div className="flex items-center gap-2.5 flex-wrap">
            <h1 className="text-2xl font-bold tracking-tight text-[var(--tx)]">Production Deck</h1>
            <Badge variant="success">$0 Strictly Free</Badge>
            <Badge variant="info">2-Pass SHA-256 Engine</Badge>
          </div>
          <p className="text-xs text-[var(--mu)] mt-0.5">
            Grounded Wikipedia &amp; Wikimedia dossier, Pexels HD B-roll, 2.5D parallax plates, and -14 LUFS broadcast audio.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="secondary"
            onClick={() => navigate('/copilot')}
            className="text-xs"
          >
            <span>Niche Scorer</span>
          </Button>
          <Button
            type="button"
            onClick={() => setIsDirectorChatOpen(true)}
            className="flex items-center gap-1.5 text-xs font-semibold !py-2 !px-3.5 bg-amber-500 hover:bg-amber-400 text-slate-950 border-amber-400 shadow-sm rounded-xl transition-all"
            title="Open Director Command Studio to clone styles or analyze videos"
          >
            <Clapperboard size={14} className="text-slate-950" />
            <span>Director Studio</span>
          </Button>
        </div>
      </div>

      {/* Main 2-Column Asymmetric Studio Production Deck */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-5 items-start">
        {/* LEFT COLUMN (8/12): Interactive Creative Controls */}
        <form
          id="studio-create-form"
          action="/api/jobs/instant"
          method="POST"
          noValidate
          onSubmit={(e) => {
            e.preventDefault();
            handleGenerate();
          }}
          className="xl:col-span-8 flex flex-col gap-5 min-w-0"
        >
          {/* PANEL A: Investigation Brief & Viral Hook Lab */}
          <div className="glass-panel p-5 space-y-3.5">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <label
                htmlFor="studio-topic-input"
                className="text-xs font-bold uppercase tracking-wider text-[var(--tx)] flex items-center gap-2"
              >
                <span>Documentary Subject or Investigation Hook</span>
                <span className="text-red-500" aria-hidden="true">*</span>
              </label>
              <span id="topic-helper-msg" className="text-[11px] text-[var(--mu)]">
                Real historical cases, science mysteries, or verified explainers
              </span>
            </div>

            <div className="flex flex-col sm:flex-row gap-2.5">
              <input
                ref={topicInputRef}
                id="studio-topic-input"
                name="topic"
                type="text"
                required
                enterKeyHint="go"
                aria-invalid={Boolean(topicError)}
                aria-describedby={topicError ? 'topic-error-msg' : 'topic-helper-msg'}
                placeholder='e.g. "CIA Project Azorian" or "How the 1971 D.B. Cooper hijacking unfolded"'
                value={topic}
                onChange={(e) => {
                  setTopic(e.target.value);
                  if (topicError) setTopicError(null);
                }}
                onBlur={() => {
                  setTopicTouched(true);
                  if (topicTouched && !topic.trim()) {
                    setTopicError('Enter a topic or pick one of the starter prompts below.');
                  }
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    if (e.nativeEvent.isComposing || e.nativeEvent.keyCode === 229) return;
                    handleGenerate();
                  }
                }}
                disabled={isGenerating}
                className={`glass-input flex-1 px-4 py-3 text-sm font-medium ${
                  topicError ? '!border-red-500 ring-2 ring-red-500/20' : ''
                }`}
              />
              <Button
                type="button"
                variant="secondary"
                onClick={handleBrainstorm}
                disabled={brainstormMutation.isPending || isGenerating}
                className="whitespace-nowrap !py-3 !px-4 text-xs font-semibold shrink-0"
              >
                {brainstormMutation.isPending ? (
                  <Loader2 size={14} className="animate-spin text-blue-500" />
                ) : (
                  <ListPlus size={14} className="text-blue-600 dark:text-blue-400" />
                )}
                <span>Generate 3 Hooks</span>
              </Button>
            </div>

            {topicError && (
              <div
                id="topic-error-msg"
                role="alert"
                className="text-xs font-medium text-red-600 dark:text-red-400 flex items-center gap-1.5"
              >
                <AlertCircle size={13} className="shrink-0" />
                <span>{topicError}</span>
              </div>
            )}

            {/* Quick Starter Topic Chips */}
            <div className="pill-row-balance items-center gap-1.5 pt-0.5">
              <span className="text-[11px] font-semibold text-[var(--mu)] mr-1">Quick Starters:</span>
              {quickStarters.map((presetTopic) => (
                <button
                  key={presetTopic}
                  type="button"
                  disabled={isGenerating}
                  onClick={() => {
                    setTopic(presetTopic);
                    setTopicError(null);
                  }}
                  className={`px-2.5 py-1 rounded-lg text-[11px] font-medium border transition-colors cursor-pointer ${
                    topic === presetTopic
                      ? 'bg-blue-600 text-white border-blue-500'
                      : 'bg-[var(--gl2)] border-[var(--ln-subtle)] text-[var(--mu)] hover:text-[var(--tx)] hover:border-blue-500/45'
                  }`}
                >
                  {presetTopic}
                </button>
              ))}
            </div>

            {/* Suggested Hook Angles */}
            {suggestedHooks.length > 0 && (
              <div className="space-y-2 pt-2 border-t border-[var(--ln-subtle)]">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-semibold text-[var(--tx)]">
                    Generated Retention Hooks (Click to load or launch):
                  </span>
                  <button
                    type="button"
                    onClick={() => setSuggestedHooks([])}
                    className="text-[11px] text-[var(--mu)] hover:text-[var(--tx)] cursor-pointer"
                  >
                    Dismiss
                  </button>
                </div>
                <div className="grid grid-cols-1 gap-2">
                  {suggestedHooks.map((hook, i) => (
                    <div
                      key={i}
                      className="glass-subcard p-2.5 flex items-center justify-between gap-2 text-xs"
                    >
                      <button
                        type="button"
                        disabled={isGenerating}
                        onClick={() => {
                          setTopic(hook);
                          setTopicError(null);
                        }}
                        className="text-left font-medium text-[var(--tx)] hover:text-blue-600 dark:hover:text-blue-400 flex-1 min-w-0 cursor-pointer"
                      >
                        "{hook}"
                      </button>
                      <button
                        type="button"
                        disabled={isGenerating}
                        onClick={() => {
                          setTopic(hook);
                          handleGenerate(hook);
                        }}
                        className="px-2.5 py-1 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-semibold text-[11px] flex items-center gap-1 shrink-0 cursor-pointer"
                      >
                        <span>Launch</span>
                        <ArrowRight size={12} />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* PANEL B: Editing Physics & Cut Cadence (Accessible Radio Card Grid) */}
          <fieldset className="glass-panel p-5 border-0 m-0 min-w-0">
            <div className="flex items-center justify-between flex-wrap gap-2 mb-3">
              <legend className="text-xs font-bold uppercase tracking-wider text-[var(--tx)] p-0">
                Editing Physics &amp; Pacing Profile
              </legend>
              <span className="text-[11px] font-mono font-semibold text-blue-600 dark:text-blue-400">
                Active: {selectedGenreObj.label} ({selectedGenreObj.cpm})
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
              {genres.map((g) => {
                const active = genre === g.id;
                const GenreIcon = g.Icon;
                const inputId = `genre-radio-${g.id}`;
                return (
                  <div key={g.id} className="relative">
                    <input
                      id={inputId}
                      type="radio"
                      name="genre"
                      value={g.id}
                      checked={active}
                      disabled={isGenerating}
                      onChange={() => setGenre(g.id)}
                      className="visually-hidden-input"
                    />
                    <label
                      htmlFor={inputId}
                      className={`h-full p-3 rounded-xl border flex flex-col justify-between gap-2 transition-all cursor-pointer select-none ${
                        active
                          ? 'bg-blue-600/12 border-blue-500 shadow-sm ring-1 ring-blue-500/40'
                          : 'bg-[var(--gl2)] border-[var(--ln)] hover:border-blue-500/45'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2 min-w-0">
                          <div
                            className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 border ${
                              active
                                ? 'bg-blue-600 text-white border-blue-500'
                                : 'bg-[var(--input-bg)] text-[var(--mu)] border-[var(--input-border)]'
                            }`}
                          >
                            <GenreIcon size={14} />
                          </div>
                          <span className="text-xs font-bold text-[var(--tx)] truncate">{g.label}</span>
                        </div>
                        <span className="text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded-md bg-[var(--input-bg)] border border-[var(--ln-subtle)] text-[var(--mu)] shrink-0">
                          {g.cpm}
                        </span>
                      </div>
                      <p className="text-[11px] text-[var(--mu)] leading-snug">{g.desc}</p>
                    </label>
                  </div>
                );
              })}
            </div>
          </fieldset>

          {/* PANEL C: Optical Color Grade & Narrator Studio (Side-by-Side Radio Card Decks) */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {/* Optical Color Grade (4 choices -> visible radio cards) */}
            <fieldset className="glass-panel p-5 border-0 m-0 min-w-0">
              <div className="flex items-center justify-between gap-2 mb-3">
                <legend className="text-xs font-bold uppercase tracking-wider text-[var(--tx)] flex items-center gap-1.5 p-0">
                  <Palette size={14} className="text-blue-600 dark:text-blue-400" />
                  <span>Optical Color Grade</span>
                </legend>
                <span className="text-[10px] font-mono text-[var(--mu)]">35mm LUT</span>
              </div>

              <div className="grid grid-cols-1 gap-2">
                {stylePresets.map((p) => {
                  const active = stylePreset === p.id;
                  const inputId = `style-radio-${p.id.replace(/\s+/g, '-').toLowerCase()}`;
                  return (
                    <div key={p.id} className="relative">
                      <input
                        id={inputId}
                        type="radio"
                        name="style_preset"
                        value={p.id}
                        checked={active}
                        disabled={isGenerating}
                        onChange={() => setStylePreset(p.id)}
                        className="visually-hidden-input"
                      />
                      <label
                        htmlFor={inputId}
                        className={`p-2.5 rounded-xl border flex items-center gap-3 transition-all cursor-pointer select-none ${
                          active
                            ? 'bg-blue-600/12 border-blue-500 ring-1 ring-blue-500/35'
                            : 'bg-[var(--gl2)] border-[var(--ln)] hover:border-blue-500/45'
                        }`}
                      >
                        <div
                          className={`w-10 h-10 rounded-lg bg-gradient-to-br ${p.swatch} border shrink-0 shadow-inner`}
                        />
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center justify-between gap-2">
                            <span className="text-xs font-bold text-[var(--tx)] truncate">{p.label}</span>
                            {active && <CheckCircle2 size={13} className="text-blue-600 dark:text-blue-400 shrink-0" />}
                          </div>
                          <p className="text-[11px] text-[var(--mu)] truncate mt-0.5">{p.desc}</p>
                        </div>
                      </label>
                    </div>
                  );
                })}
              </div>
            </fieldset>

            {/* Voice Narration Stack (4 choices -> visible radio cards) */}
            <fieldset className="glass-panel p-5 border-0 m-0 min-w-0">
              <div className="flex items-center justify-between gap-2 mb-3">
                <legend className="text-xs font-bold uppercase tracking-wider text-[var(--tx)] flex items-center gap-1.5 p-0">
                  <Mic size={14} className="text-emerald-600 dark:text-emerald-400" />
                  <span>Narrator Voice</span>
                </legend>
                <span className="text-[10px] font-mono text-emerald-600 dark:text-emerald-400 font-semibold">
                  -14 LUFS Mastered
                </span>
              </div>

              <div className="grid grid-cols-1 gap-2">
                {voices.map((v) => {
                  const active = voice === v.id;
                  const inputId = `voice-radio-${v.id}`;
                  return (
                    <div key={v.id} className="relative">
                      <input
                        id={inputId}
                        type="radio"
                        name="voice"
                        value={v.id}
                        checked={active}
                        disabled={isGenerating}
                        onChange={() => setVoice(v.id)}
                        className="visually-hidden-input"
                      />
                      <label
                        htmlFor={inputId}
                        className={`p-2.5 rounded-xl border flex items-center justify-between gap-2.5 transition-all cursor-pointer select-none ${
                          active
                            ? 'bg-blue-600/12 border-blue-500 ring-1 ring-blue-500/35'
                            : 'bg-[var(--gl2)] border-[var(--ln)] hover:border-blue-500/45'
                        }`}
                      >
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-bold text-[var(--tx)] truncate">
                              {v.shortLabel}
                            </span>
                          </div>
                          <p className="text-[11px] text-[var(--mu)] truncate mt-0.5">{v.desc}</p>
                        </div>
                        <span
                          className={`text-[10px] font-mono font-semibold px-2 py-0.5 rounded-md border shrink-0 ${
                            v.id === 'am_michael'
                              ? 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border-emerald-500/35'
                              : 'bg-[var(--input-bg)] text-[var(--mu)] border-[var(--ln-subtle)]'
                          }`}
                        >
                          {v.badge}
                        </span>
                      </label>
                    </div>
                  );
                })}
              </div>
            </fieldset>
          </div>

          {/* PANEL D: Frame Geometry, Duration & Visual Reference Anchor */}
          <div className="glass-panel p-5 space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              {/* Format & Aspect Ratio (2 choices -> radio cards) */}
              <fieldset className="border-0 m-0 p-0 min-w-0">
                <legend className="text-xs font-bold uppercase tracking-wider text-[var(--tx)] mb-2.5 p-0">
                  Frame Geometry
                </legend>
                <div className="grid grid-cols-2 gap-2.5">
                  {[
                    {
                      id: '9:16',
                      title: '9:16 Vertical',
                      sub: 'Shorts / Reels / TikTok',
                      Icon: Smartphone
                    },
                    {
                      id: '16:9',
                      title: '16:9 Cinema',
                      sub: 'YouTube Essay / Wide',
                      Icon: Monitor
                    }
                  ].map((fmt) => {
                    const active = aspectRatio === fmt.id;
                    const FmtIcon = fmt.Icon;
                    const inputId = `ratio-radio-${fmt.id.replace(':', 'x')}`;
                    return (
                      <div key={fmt.id} className="relative">
                        <input
                          id={inputId}
                          type="radio"
                          name="aspect_ratio"
                          value={fmt.id}
                          checked={active}
                          disabled={isGenerating}
                          onChange={() => setAspectRatio(fmt.id)}
                          className="visually-hidden-input"
                        />
                        <label
                          htmlFor={inputId}
                          className={`p-3 rounded-xl border flex items-center gap-2.5 transition-all cursor-pointer select-none ${
                            active
                              ? 'bg-blue-600 text-white border-blue-500 shadow-sm'
                              : 'bg-[var(--gl2)] border-[var(--ln)] text-[var(--tx)] hover:border-blue-500/45'
                          }`}
                        >
                          <FmtIcon size={17} className="shrink-0" />
                          <div className="min-w-0">
                            <div className="text-xs font-bold truncate">{fmt.title}</div>
                            <div
                              className={`text-[10px] truncate ${
                                active ? 'text-blue-100' : 'text-[var(--mu)]'
                              }`}
                            >
                              {fmt.sub}
                            </div>
                          </div>
                        </label>
                      </div>
                    );
                  })}
                </div>
              </fieldset>

              {/* Target Duration (4 choices -> radio pills) */}
              <fieldset className="border-0 m-0 p-0 min-w-0">
                <legend className="text-xs font-bold uppercase tracking-wider text-[var(--tx)] mb-2.5 p-0">
                  Target Runtime
                </legend>
                <div className="grid grid-cols-4 gap-2">
                  {durations.map((d) => {
                    const active = duration === d.id;
                    const inputId = `dur-radio-${d.id}`;
                    return (
                      <div key={d.id} className="relative">
                        <input
                          id={inputId}
                          type="radio"
                          name="duration"
                          value={d.id}
                          checked={active}
                          disabled={isGenerating}
                          onChange={() => setDuration(d.id)}
                          className="visually-hidden-input"
                        />
                        <label
                          htmlFor={inputId}
                          className={`py-2.5 px-2 rounded-xl border flex flex-col items-center justify-center text-center transition-all cursor-pointer select-none ${
                            active
                              ? 'bg-blue-600 text-white border-blue-500 shadow-sm'
                              : 'bg-[var(--gl2)] border-[var(--ln)] text-[var(--tx)] hover:border-blue-500/45'
                          }`}
                        >
                          <span className="text-xs font-extrabold font-mono">{d.label}</span>
                          <span
                            className={`text-[10px] truncate ${
                              active ? 'text-blue-100' : 'text-[var(--mu)]'
                            }`}
                          >
                            {d.sub}
                          </span>
                        </label>
                      </div>
                    );
                  })}
                </div>
              </fieldset>
            </div>

            {/* Optional Style Reference Image Dropzone */}
            <div className="pt-3 border-t border-[var(--ln-subtle)]">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold uppercase tracking-wider text-[var(--tx)] flex items-center gap-1.5">
                  <ImageIcon size={13} className="text-blue-600 dark:text-blue-400" />
                  <span>Starting Visual Reference (Optional)</span>
                </span>
                {anchorFile && <Badge variant="success">Reference Attached</Badge>}
              </div>

              {anchorPreview ? (
                <div className="glass-subcard p-2.5 flex items-center justify-between border-blue-500/40">
                  <div className="flex items-center gap-3 min-w-0">
                    <img
                      src={anchorPreview}
                      alt="Selected visual reference"
                      className="w-11 h-11 rounded-lg object-cover border border-[var(--input-border)] shrink-0"
                    />
                    <div className="min-w-0">
                      <div className="text-xs font-semibold text-[var(--tx)] truncate">
                        {anchorFile?.name}
                      </div>
                      <div className="text-[11px] text-[var(--mu)] font-mono">
                        {anchorFile?.size ? (anchorFile.size / 1024).toFixed(0) : 0} KB · Guides scene plates &amp; Image-to-Video
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
                <label
                  htmlFor="anchor-file-upload"
                  className="cursor-pointer border border-dashed border-[var(--input-border)] hover:border-blue-500/70 rounded-xl p-3 bg-[var(--input-bg)] hover:bg-[var(--gl2)] transition-all flex items-center justify-center gap-2.5 text-[var(--mu)] hover:text-[var(--tx)]"
                >
                  <Upload size={14} className="text-blue-600 dark:text-blue-400 shrink-0" />
                  <span className="text-xs font-medium">
                    Attach reference frame (.png, .jpg, .webp) to anchor documentary mood &amp; Image-to-Video
                  </span>
                  <input
                    id="anchor-file-upload"
                    name="anchor_file"
                    type="file"
                    accept="image/png,image/jpeg,image/webp"
                    className="visually-hidden-input"
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
        </form>

        {/* RIGHT COLUMN (4/12): Live Frame Monitor, Launch Trigger & Quick Telemetry */}
        <div className="xl:col-span-4 flex flex-col gap-5 xl:sticky xl:top-4 min-w-0 preview-deck-container">
          {/* CARD 1: Live Frame Composition Monitor & Launch CTA */}
          <div className="prismatic-launch-card p-5 studio-monitor-card">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-xs bg-emerald-400" />
                <span className="text-xs font-bold uppercase tracking-wider text-white">
                  Live Frame Monitor
                </span>
              </div>
              <span className="font-mono text-[11px] text-cyan-300">
                {aspectRatio === '16:9' ? '1920x1080' : '1080x1920'} · {duration}
              </span>
            </div>

            {/* Aspect-Ratio Preview Canvas */}
            <div className="py-1 flex items-center justify-center">
              <div
                style={{ background: selectedStyleObj.monitorBg }}
                className={`relative overflow-hidden rounded-2xl border border-white/20 shadow-2xl flex flex-col justify-between p-3.5 transition-all duration-300 ${
                  aspectRatio === '16:9'
                    ? 'w-full aspect-video'
                    : 'w-[196px] aspect-[9/16]'
                }`}
              >
                {anchorPreview && (
                  <img
                    src={anchorPreview}
                    alt=""
                    className="absolute inset-0 w-full h-full object-cover opacity-55 mix-blend-luminosity"
                  />
                )}

                {/* Optional 2.35:1 Cinema Letterbox Bars */}
                {genre === 'movie_cinema' && (
                  <>
                    <div className="absolute inset-x-0 top-0 h-3.5 bg-black/90 z-10" />
                    <div className="absolute inset-x-0 bottom-0 h-3.5 bg-black/90 z-10" />
                  </>
                )}

                {/* Top Camera HUD */}
                <div className="relative z-20 flex items-center justify-between gap-1.5 text-[9px] font-mono">
                  <span className="px-1.5 py-0.5 rounded bg-black/55 text-sky-300 border border-white/15 font-bold uppercase">
                    {selectedGenreObj.label}
                  </span>
                  <span className="px-1.5 py-0.5 rounded bg-black/55 text-amber-300 border border-white/15 font-bold">
                    {selectedGenreObj.cpm}
                  </span>
                </div>

                {/* Center Subject Reticle */}
                <div className="relative z-20 my-auto text-center px-1">
                  <span className="inline-block px-2 py-0.5 rounded bg-white/10 border border-white/20 text-[9px] font-mono uppercase tracking-widest text-slate-200 mb-1.5">
                    {selectedStyleObj.label}
                  </span>
                  <p className="text-xs font-extrabold tracking-tight text-white uppercase leading-snug line-clamp-3 drop-shadow">
                    {topic.trim() || 'DECLASSIFIED ARCHIVE READY FOR PRODUCTION'}
                  </p>
                </div>

                {/* Simulated Montserrat-Black Karaoke Safe-Zone Pill */}
                <div className="relative z-20 flex flex-col items-center gap-1 pb-1">
                  <div className="px-2.5 py-1 rounded-md bg-black/80 border border-amber-400/50 text-[10px] font-black tracking-wide uppercase text-white text-center shadow">
                    <span className="text-amber-300">BEAT 01</span> · KINETIC ASS CAPTIONS
                  </div>
                </div>
              </div>
            </div>

            {/* Container-Aware Spec Grid */}
            <div className="studio-monitor-meta grid grid-cols-1 gap-2 text-[11px] pt-1">
              <div className="px-3 py-2 rounded-xl bg-white/8 border border-white/12 flex items-center justify-between">
                <span className="text-slate-400">Voice</span>
                <span className="font-semibold text-white truncate ml-2">
                  {selectedVoiceObj.shortLabel}
                </span>
              </div>
              <div className="px-3 py-2 rounded-xl bg-white/8 border border-white/12 flex items-center justify-between">
                <span className="text-slate-400">API Cost</span>
                <span className="font-mono font-bold text-emerald-400">
                  ${spentAmount.toFixed(2)}
                </span>
              </div>
            </div>

            {/* Primary Form Submit CTA */}
            <button
              type="submit"
              form="studio-create-form"
              disabled={isGenerating}
              className="w-full py-3.5 px-4 rounded-xl bg-blue-600 hover:bg-blue-500 disabled:opacity-60 text-white font-bold text-xs tracking-wide flex items-center justify-center gap-2 shadow-lg shadow-blue-600/30 transition-all cursor-pointer"
            >
              {isGenerating ? (
                <Loader2 size={16} className="animate-spin" />
              ) : (
                <Zap size={16} />
              )}
              <span>
                {isGenerating
                  ? 'Rendering Documentary Pipeline...'
                  : `Launch ${aspectRatio === '16:9' ? '16:9 Documentary' : '9:16 Short'} (${duration})`}
              </span>
            </button>

            {/* Live 4-Step Pipeline Progress */}
            {isGenerating && (
              <div className="pt-3 border-t border-white/15 space-y-2.5" aria-live="polite">
                <div className="flex items-center justify-between text-[11px] font-semibold text-slate-200">
                  <span>Assembly Progress</span>
                  <span className="font-mono text-cyan-300">
                    Stage {Math.min(activeStepIndex + 1, 4)} / 4
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  {pipelineSteps.map((step, idx) => {
                    const isPast = idx < activeStepIndex;
                    const isCurrent = idx === activeStepIndex;
                    return (
                      <div
                        key={step.id}
                        aria-current={isCurrent ? 'step' : undefined}
                        className={`p-2.5 rounded-xl border text-[11px] flex flex-col justify-between ${
                          isPast
                            ? 'bg-emerald-500/20 border-emerald-400/40 text-emerald-200'
                            : isCurrent
                            ? 'bg-blue-600/30 border-cyan-400 text-white'
                            : 'bg-white/5 border-white/10 text-slate-400'
                        }`}
                      >
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-mono text-[10px] font-bold">0{step.id}</span>
                          {isPast ? (
                            <CheckCircle2 size={12} className="text-emerald-400" />
                          ) : isCurrent ? (
                            <Loader2 size={12} className="animate-spin text-cyan-300" />
                          ) : null}
                        </div>
                        <span className="font-semibold leading-tight">{step.name}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {errorMsg && (
              <div
                role="alert"
                className="p-3 bg-red-500/20 border border-red-400/50 rounded-xl flex items-center justify-between gap-2 text-xs text-red-100"
              >
                <div className="flex items-center gap-2 min-w-0">
                  <AlertCircle size={15} className="text-red-300 shrink-0" />
                  <span className="font-medium">{errorMsg}</span>
                </div>
                <button
                  type="button"
                  onClick={() => setErrorMsg(null)}
                  className="text-red-200 hover:text-white cursor-pointer shrink-0"
                  aria-label="Dismiss error"
                >
                  <X size={14} />
                </button>
              </div>
            )}
          </div>

          {/* CARD 2: Generative Video & Asset Readiness */}
          <div className="glass-panel p-4 space-y-3">
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs font-bold text-[var(--tx)] flex items-center gap-1.5">
                <Layers size={14} className="text-amber-600 dark:text-amber-400" />
                <span>Visual &amp; Motion Stack</span>
              </span>
              <Badge variant={videoGenStatus?.hf_token_configured ? 'success' : 'info'}>
                {videoGenStatus?.primary_space || 'Lightricks/LTX-2.5'}
              </Badge>
            </div>
            <p className="text-[11px] text-[var(--mu)] leading-relaxed">
              Combines Wikimedia Commons archival photography, Pexels HD B-roll, 2.5D depth parallax, and ZeroGPU Image-to-Video on Hero beats.
            </p>
            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                const promptText = `Cinematic 35mm documentary shot, ${stylePreset}, ${topic.trim() || 'Declassified historical investigation'}, volumetric lighting, natural camera push-in${anchorFile ? ` (Reference Image: ${anchorFile.name})` : ''}`;
                navigator.clipboard.writeText(promptText);
                setFlowCopied(true);
                setTimeout(() => setFlowCopied(false), 2500);
              }}
              className="w-full !py-2 text-xs justify-center"
              title="Copy cinematic prompt specification for Google Flow"
            >
              {flowCopied ? <Check size={13} className="text-emerald-500" /> : <Copy size={13} />}
              <span>{flowCopied ? 'Prompt Copied for Google Flow' : 'Copy Prompt for Google Flow'}</span>
            </Button>
          </div>

          {/* CARD 3: Compact Recent Renders Rail */}
          {recentJobs.length > 0 && (
            <div className="glass-panel p-4 space-y-3">
              <div className="flex items-center justify-between">
                <h2 className="text-xs font-bold uppercase tracking-wider text-[var(--tx)]">
                  Recent Studio Renders ({recentJobs.length})
                </h2>
                <button
                  type="button"
                  onClick={() => setIsConfirmClearOpen(true)}
                  disabled={clearAllMutation.isPending}
                  className="text-[11px] font-semibold text-[var(--mu)] hover:text-red-600 dark:hover:text-red-400 flex items-center gap-1 transition-colors cursor-pointer"
                >
                  <Trash2 size={11} />
                  <span>Clear</span>
                </button>
              </div>

              <div className="space-y-2">
                {recentJobs.slice(0, 5).map((j: any) => {
                  const videoAsset = j.assets?.find((a: any) => a.type === 'VIDEO' || a.type === 'video');
                  const hasVideo = !!videoAsset;
                  return (
                    <div
                      key={j.id}
                      onClick={() => navigate(`/qc1/${j.id}`)}
                      className="glass-subcard p-2.5 cursor-pointer flex items-center justify-between gap-2 group"
                    >
                      <div className="flex items-center gap-2.5 min-w-0">
                        <div className="w-8 h-8 rounded-lg bg-blue-600/15 text-blue-600 dark:text-blue-400 border border-blue-500/25 flex items-center justify-center shrink-0">
                          <Film size={14} />
                        </div>
                        <div className="min-w-0">
                          <div className="text-xs font-bold text-[var(--tx)] group-hover:text-blue-600 dark:group-hover:text-blue-400 truncate">
                            {j.niche}
                          </div>
                          <div className="text-[10px] text-[var(--mu)] font-mono">
                            #{j.id} · {j.config?.format || '9:16'} · {j.current_stage || j.status}
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-1 shrink-0">
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
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            deleteJobMutation.mutate(j.id);
                          }}
                          className="p-1.5 text-[var(--mu)] hover:text-red-500 transition-colors rounded-lg hover:bg-red-500/10 cursor-pointer"
                          title="Delete project"
                        >
                          <Trash2 size={13} />
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>

              <ConfirmDialog
                isOpen={isConfirmClearOpen}
                title="Clear All Recent Video Jobs?"
                description="This removes all recent job history entries from the studio list."
                confirmLabel="Clear All"
                onConfirm={() => {
                  setIsConfirmClearOpen(false);
                  clearAllMutation.mutate();
                }}
                onCancel={() => setIsConfirmClearOpen(false)}
              />
            </div>
          )}
        </div>
      </div>

      <DirectorChatDrawer isOpen={isDirectorChatOpen} onClose={() => setIsDirectorChatOpen(false)} />
    </div>
  );
}
