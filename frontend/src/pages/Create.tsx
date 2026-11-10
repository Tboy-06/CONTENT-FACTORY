import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Zap, Sparkles, Loader2, Film, CheckCircle2, ArrowRight, Trash2, AlertCircle, Upload, Image as ImageIcon, X } from 'lucide-react';
import { Button, Card, Badge } from '../components/ui';
import { useCreateInstantJob, useBrainstormHooks, useJobs, useDeleteJob, useClearAllJobs, useUploadAnchor, api } from '../api/client';

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
  const [aspectRatio, setAspectRatio] = useState('9:16');
  const [duration, setDuration] = useState('45s');
  const [anchorFile, setAnchorFile] = useState<File | null>(null);
  const [anchorPreview, setAnchorPreview] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [activeStepIndex, setActiveStepIndex] = useState(0);
  const [suggestedHooks, setSuggestedHooks] = useState<string[]>([]);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const { data: recentJobs = [] } = useJobs();
  const instantMutation = useCreateInstantJob();
  const brainstormMutation = useBrainstormHooks();
  const deleteJobMutation = useDeleteJob();
  const clearAllMutation = useClearAllJobs();
  const uploadAnchorMutation = useUploadAnchor();

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
      'SCRIPT': 0,
      'AUDIO': 1,
      'PLATES': 2,
      'FFMPEG': 3,
      'QC1': 4
    };

    try {
      const res = await instantMutation.mutateAsync({
        topic: finalTopic,
        voice,
        style_preset: stylePreset,
        aspect_ratio: aspectRatio,
        duration
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

      // Poll real job stage from backend
      const interval = setInterval(async () => {
        try {
          const jobs = await api.get('/api/jobs');
          const currentJob = jobs.find((j: any) => j.id === jobId);

          if (currentJob) {
            // Update active stage based on real backend progress
            if (currentJob.current_stage && currentJob.current_stage in stageMap) {
              setActiveStepIndex(stageMap[currentJob.current_stage]);
            }

            const hasVideo = currentJob.assets?.some((a: any) => a.type === 'VIDEO' || a.type === 'video');

            if (currentJob.current_stage === 'QC1' && hasVideo) {
              clearInterval(interval);
              setActiveStepIndex(4);
              setTimeout(() => navigate(`/qc1/${jobId}`), 400);
            } else if (currentJob.status === 'FAILED') {
              clearInterval(interval);
              setIsGenerating(false);
              setErrorMsg(currentJob.current_stage ? `Pipeline failed at stage: ${currentJob.current_stage}` : 'Generation encountered an error. Please try again.');
            }
          }
        } catch {
          // ignore transient errors
        }

        // Safety timeout of 180s (prevent eternal loop)
        if (Date.now() - startTime > 180000) {
          clearInterval(interval);
          setIsGenerating(false);
          setErrorMsg('Generation timed out. Check terminal logs.');
        }
      }, 1000);

    } catch (e: any) {
      console.error(e);
      setIsGenerating(false);
      setErrorMsg(e?.message || 'Failed to start video generation.');
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

          {/* 4. Aspect Ratio & Format */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase tracking-wider text-slate-300">
              4. Format & Ratio
            </label>
            <select
              value={aspectRatio}
              onChange={(e) => setAspectRatio(e.target.value)}
              disabled={isGenerating}
              className="w-full px-3 py-2.5 rounded-xl bg-slate-950/80 border border-slate-700 text-xs text-white outline-none focus:border-blue-500 cursor-pointer"
            >
              <option value="9:16">9:16 Vertical (Shorts, Reels, TikTok)</option>
              <option value="16:9">16:9 Horizontal (YouTube Channel, Video Essay)</option>
            </select>
          </div>

          {/* 5. Target Duration */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase tracking-wider text-slate-300">
              5. Target Duration
            </label>
            <select
              value={duration}
              onChange={(e) => setDuration(e.target.value)}
              disabled={isGenerating}
              className="w-full px-3 py-2.5 rounded-xl bg-slate-950/80 border border-slate-700 text-xs text-white outline-none focus:border-blue-500 cursor-pointer"
            >
              <option value="45s">45 Seconds (High-Tempo Short)</option>
              <option value="60s">60 Seconds (Full Short)</option>
              <option value="3m">3 Minutes (Standard Documentary Essay)</option>
              <option value="5m">5 Minutes (Deep Investigation)</option>
            </select>
          </div>

          {/* 6. Custom Visual Anchor (Optional Style Reference) */}
          <div className="col-span-full space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                <ImageIcon size={13} className="text-blue-400" />
                <span>6. Visual Anchor / Reference Image (Optional)</span>
              </label>
              {anchorFile && (
                <span className="text-[10px] text-emerald-400 font-mono">Anchor attached</span>
              )}
            </div>
            
            {anchorPreview ? (
              <div className="relative rounded-xl border border-blue-500/40 bg-slate-950/80 p-2 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <img src={anchorPreview} alt="Anchor preview" className="w-12 h-12 rounded-lg object-cover border border-slate-700" />
                  <div>
                    <div className="text-xs font-medium text-white truncate max-w-[200px]">{anchorFile?.name}</div>
                    <div className="text-[10px] text-slate-400 font-mono">{(anchorFile?.size ? (anchorFile.size / 1024).toFixed(0) : 0)} KB • Style Reference</div>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setAnchorFile(null);
                    setAnchorPreview(null);
                  }}
                  className="p-1.5 rounded-lg text-slate-400 hover:text-red-400 hover:bg-red-500/10 transition-colors"
                  title="Remove visual anchor"
                >
                  <X size={15} />
                </button>
              </div>
            ) : (
              <label className="cursor-pointer border border-dashed border-slate-700 hover:border-blue-500/60 rounded-xl p-3 bg-slate-950/50 hover:bg-slate-900/50 transition-all flex items-center justify-center gap-2.5 text-slate-400 hover:text-slate-200">
                <Upload size={14} className="text-blue-400" />
                <span className="text-xs">Upload style reference image (.png, .jpg) to anchor scene plates</span>
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

        {/* 5. Action Button: Generate Short */}
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

        {/* Error Alert if Generation Failed */}
        {errorMsg && (
          <div className="p-3 bg-red-950/70 border border-red-500/40 rounded-xl flex items-center justify-between text-xs text-red-300">
            <div className="flex items-center gap-2">
              <AlertCircle size={16} className="text-red-400 shrink-0" />
              <span>{errorMsg}</span>
            </div>
            <button onClick={() => setErrorMsg(null)} className="text-red-400 hover:text-white ml-2 text-sm">&times;</button>
          </div>
        )}

      </Card>

      {/* Recent Video Projects Quick Access */}
      {recentJobs.length > 0 && (
        <div className="space-y-3 pt-2">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-300">Recent Videos Ready for Review</h2>
            <div className="flex items-center gap-3">
              <span className="text-xs text-[var(--mu)]">{recentJobs.length} Projects Total</span>
              <button
                onClick={() => {
                  if (confirm("Clear all recent jobs?")) {
                    clearAllMutation.mutate();
                  }
                }}
                disabled={clearAllMutation.isPending}
                className="text-[11px] text-slate-400 hover:text-red-400 flex items-center gap-1 transition-colors"
                title="Clear all job history"
              >
                <Trash2 size={12} />
                <span>Clear All</span>
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
            {recentJobs.slice(0, 9).map((j: any) => {
              const videoAsset = j.assets?.find((a: any) => a.type === 'VIDEO' || a.type === 'video');
              const hasVideo = !!videoAsset;
              return (
                <div
                  key={j.id}
                  onClick={() => navigate(`/qc1/${j.id}`)}
                  className="p-3.5 rounded-xl bg-slate-900/50 border border-slate-800 hover:border-blue-500/60 cursor-pointer transition-all flex items-center justify-between group relative"
                >
                  <div className="flex items-center gap-3 truncate pr-2">
                    <div className="w-8 h-8 rounded-lg bg-blue-600/20 text-blue-400 border border-blue-500/30 flex items-center justify-center shrink-0">
                      <Film size={16} />
                    </div>
                    <div className="truncate">
                      <div className="text-xs font-semibold text-white group-hover:text-blue-400 transition-colors truncate">
                        {j.niche}
                      </div>
                      <div className="text-[10px] text-slate-500 font-mono mt-0.5">
                        Job #{j.id} | {j.current_stage || j.status}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className={`text-[10px] font-mono px-2 py-0.5 rounded border shrink-0 ${
                      hasVideo ? 'text-emerald-400 border-emerald-500/30 bg-emerald-950/40' : 'text-amber-400 border-amber-500/30 bg-amber-950/40'
                    }`}>
                      {hasVideo ? '9:16 MP4' : (j.status === 'FAILED' ? 'Failed' : 'Pending')}
                    </span>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        deleteJobMutation.mutate(j.id);
                      }}
                      className="opacity-0 group-hover:opacity-100 p-1 text-slate-500 hover:text-red-400 transition-all rounded hover:bg-slate-800"
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

    </div>
  );
}
