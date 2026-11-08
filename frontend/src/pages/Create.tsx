import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Zap, Sparkles, Loader2, Film, CheckCircle2, ArrowRight } from 'lucide-react';
import { Button, Card, Badge } from '../components/ui';
import { useCreateInstantJob, useBrainstormHooks, useJobs, api } from '../api/client';

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

const pipelineSteps = [
  { id: 1, name: 'Writing Script', stage: 'SCRIPT' },
  { id: 2, name: 'Generating Voice & Subs', stage: 'AUDIO' },
  { id: 3, name: 'Rendering Visual Plates', stage: 'PLATES' },
  { id: 4, name: 'FFmpeg 9:16 Render', stage: 'FFMPEG' }
];

export default function Create() {
  const navigate = useNavigate();
  const [topic, setTopic] = useState('');
  const [stylePreset, setStylePreset] = useState('Dark Documentary');
  const [voice, setVoice] = useState('en-US-AriaNeural');
  const [isGenerating, setIsGenerating] = useState(false);
  const [activeStepIndex, setActiveStepIndex] = useState(0);
  const [suggestedHooks, setSuggestedHooks] = useState<string[]>([]);

  const { data: recentJobs = [] } = useJobs();
  const instantMutation = useCreateInstantJob();
  const brainstormMutation = useBrainstormHooks();

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
    setActiveStepIndex(0);

    try {
      const res = await instantMutation.mutateAsync({
        topic: finalTopic,
        voice,
        style_preset: stylePreset
      });

      const jobId = res.id;

      // Realistic 4-step progress animation while polling
      const stepTimer1 = setTimeout(() => setActiveStepIndex(1), 1800);
      const stepTimer2 = setTimeout(() => setActiveStepIndex(2), 3800);
      const stepTimer3 = setTimeout(() => setActiveStepIndex(3), 5800);

      // Active polling
      const startTime = Date.now();
      const interval = setInterval(async () => {
        try {
          const jobs = await api.get('/api/jobs');
          const currentJob = jobs.find((j: any) => j.id === jobId);

          if (currentJob) {
            if (currentJob.current_stage === 'QC1' || currentJob.status === 'RUNNING' && currentJob.stages?.some((s: any) => s.stage === 'QC1')) {
              clearInterval(interval);
              clearTimeout(stepTimer1);
              clearTimeout(stepTimer2);
              clearTimeout(stepTimer3);
              setActiveStepIndex(4);
              setTimeout(() => navigate(`/qc1/${jobId}`), 400);
            } else if (currentJob.status === 'FAILED') {
              clearInterval(interval);
              setIsGenerating(false);
            }
          }
        } catch {
          // ignore transient errors
        }

        if (Date.now() - startTime > 45000) {
          clearInterval(interval);
          navigate(`/qc1/${jobId}`);
        }
      }, 1200);

    } catch (e) {
      console.error(e);
      setIsGenerating(false);
    }
  };

  return (
    <div className="animate-in fade-in min-h-full flex flex-col pb-12 space-y-6 max-w-5xl mx-auto">
      
      {/* Header */}
      <div className="flex justify-between items-center flex-wrap gap-2">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-white">Video Launchpad</h1>
          <p className="text-[13px] text-[var(--mu)]">Zero-cost local short video production engine (Edge-TTS + FFmpeg + Pillow).</p>
        </div>
        <Badge variant="success">Zero API Cost</Badge>
      </div>

      {/* View 1: The "New Video" Launchpad Card */}
      <Card className="!p-6 bg-slate-900/70 border-slate-700/80 space-y-5 shadow-xl">
        
        {/* Topic Input Box & Viral Hook Button */}
        <div className="space-y-2">
          <label className="text-xs font-semibold uppercase tracking-wider text-slate-300">
            1. Topic or Idea
          </label>
          <div className="flex gap-2">
            <input
              type="text"
              placeholder='e.g. "3 psychological tricks people use on you" or "Why waking up at 5 AM actually works"'
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleGenerate()}
              disabled={isGenerating}
              className="flex-1 px-4 py-3 rounded-xl bg-slate-950/80 border border-slate-700 text-white placeholder-slate-500 text-sm outline-none focus:border-blue-500 transition-colors"
            />
            <Button
              variant="secondary"
              onClick={handleBrainstorm}
              disabled={brainstormMutation.isPending || isGenerating}
              className="flex items-center gap-1.5 whitespace-nowrap !py-3 !px-4 text-xs font-medium border-slate-700"
            >
              {brainstormMutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} className="text-amber-400" />}
              <span>Brainstorm 3 Viral Hooks</span>
            </Button>
          </div>

          {/* Brainstormed Hook Suggestions */}
          {suggestedHooks.length > 0 && (
            <div className="space-y-1.5 pt-1 animate-in fade-in">
              <span className="text-[11px] font-medium text-slate-400">Click any high-retention hook to use it:</span>
              <div className="grid grid-cols-1 gap-1.5">
                {suggestedHooks.map((hook, i) => (
                  <button
                    key={i}
                    onClick={() => {
                      setTopic(hook);
                      handleGenerate(hook);
                    }}
                    disabled={isGenerating}
                    className="text-left text-xs p-2.5 rounded-lg bg-blue-950/30 border border-blue-800/40 text-blue-200 hover:bg-blue-900/40 hover:border-blue-500 transition-colors flex items-center justify-between group"
                  >
                    <span>“{hook}”</span>
                    <ArrowRight size={14} className="text-blue-400 opacity-0 group-hover:opacity-100 transition-opacity shrink-0 ml-2" />
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Style Preset & Voice Controls */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
          
          {/* 2. Visual Style Preset Dropdown */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase tracking-wider text-slate-300">
              2. Visual Aesthetic Preset
            </label>
            <select
              value={stylePreset}
              onChange={(e) => setStylePreset(e.target.value)}
              disabled={isGenerating}
              className="w-full px-3 py-2.5 rounded-xl bg-slate-950/80 border border-slate-700 text-xs text-white outline-none focus:border-blue-500 cursor-pointer"
            >
              {stylePresets.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.label} - {p.desc}
                </option>
              ))}
            </select>
          </div>

          {/* 3. Voice Selector Dropdown */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase tracking-wider text-slate-300">
              3. Voice Narration (Edge-TTS)
            </label>
            <select
              value={voice}
              onChange={(e) => setVoice(e.target.value)}
              disabled={isGenerating}
              className="w-full px-3 py-2.5 rounded-xl bg-slate-950/80 border border-slate-700 text-xs text-white outline-none focus:border-blue-500 cursor-pointer"
            >
              {voices.map((v) => (
                <option key={v.id} value={v.id}>{v.label}</option>
              ))}
            </select>
          </div>

        </div>

        {/* 4. Action Button: Generate Short */}
        <div className="pt-2">
          <Button
            onClick={() => handleGenerate()}
            disabled={!topic.trim() || isGenerating}
            className="w-full py-3.5 text-sm font-semibold flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl shadow-lg shadow-blue-600/25 transition-all"
          >
            {isGenerating ? <Loader2 size={18} className="animate-spin" /> : <Zap size={18} />}
            <span>{isGenerating ? 'Assembling Video...' : 'Generate Short (9:16 Vertical)'}</span>
          </Button>
        </div>

        {/* Live 4-Step Status Bar */}
        {isGenerating && (
          <div className="pt-3 space-y-3 border-t border-slate-800">
            <div className="flex items-center justify-between text-xs font-medium text-slate-300">
              <span>Assembly Pipeline Progress</span>
              <span className="font-mono text-blue-400">Step {Math.min(activeStepIndex + 1, 4)} of 4</span>
            </div>

            <div className="grid grid-cols-4 gap-2">
              {pipelineSteps.map((step, idx) => {
                const isPast = idx < activeStepIndex;
                const isCurrent = idx === activeStepIndex;
                return (
                  <div
                    key={step.id}
                    className={`p-2.5 rounded-lg border text-xs flex flex-col justify-between transition-all ${
                      isPast
                        ? 'bg-emerald-950/40 border-emerald-500/40 text-emerald-300'
                        : isCurrent
                        ? 'bg-blue-950/60 border-blue-500 text-white shadow-[0_0_12px_rgba(59,130,246,0.3)] animate-pulse'
                        : 'bg-slate-950/40 border-slate-800 text-slate-500'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-mono text-[10px]">0{step.id}</span>
                      {isPast ? (
                        <CheckCircle2 size={12} className="text-emerald-400" />
                      ) : isCurrent ? (
                        <Loader2 size={12} className="animate-spin text-blue-400" />
                      ) : null}
                    </div>
                    <span className="font-medium text-[11px] leading-tight">{step.name}</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

      </Card>

      {/* Recent Video Projects Quick Access */}
      {recentJobs.length > 0 && (
        <div className="space-y-3 pt-2">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-300">Recent Videos Ready for Review</h2>
            <span className="text-xs text-[var(--mu)]">{recentJobs.length} Projects Total</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
            {recentJobs.slice(0, 6).map((j: any) => {
              const videoAsset = j.assets?.find((a: any) => a.type === 'VIDEO');
              const hasVideo = !!videoAsset;
              return (
                <div
                  key={j.id}
                  onClick={() => navigate(`/qc1/${j.id}`)}
                  className="p-3.5 rounded-xl bg-slate-900/50 border border-slate-800 hover:border-blue-500/60 cursor-pointer transition-all flex items-center justify-between group"
                >
                  <div className="flex items-center gap-3 truncate">
                    <div className="w-8 h-8 rounded-lg bg-blue-600/20 text-blue-400 border border-blue-500/30 flex items-center justify-center shrink-0">
                      <Film size={16} />
                    </div>
                    <div className="truncate">
                      <div className="text-xs font-semibold text-white group-hover:text-blue-400 transition-colors truncate">
                        {j.niche}
                      </div>
                      <div className="text-[10px] text-slate-500 font-mono mt-0.5">
                        Job #{j.id} · {j.current_stage || j.status}
                      </div>
                    </div>
                  </div>
                  <span className={`text-[10px] font-mono px-2 py-0.5 rounded border shrink-0 ${
                    hasVideo ? 'text-emerald-400 border-emerald-500/30 bg-emerald-950/40' : 'text-amber-400 border-amber-500/30 bg-amber-950/40'
                  }`}>
                    {hasVideo ? '9:16 MP4' : 'Pending'}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

    </div>
  );
}
