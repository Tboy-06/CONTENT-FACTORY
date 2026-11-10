import React, { useState, useEffect } from 'react';
import { Film, X, Shield, Eye, EyeOff, Clock, Sparkles, Volume2, Plus, Minus, Loader2, Check } from 'lucide-react';
import { Button, Badge } from './ui';
import SafeZoneOverlay from './SafeZoneOverlay';
import { useRegenerateAudio } from '../api/client';

interface VideoStudioModalProps {
  isOpen: boolean;
  onClose: () => void;
  job: any;
}

export default function VideoStudioModal({ isOpen, onClose, job }: VideoStudioModalProps) {
  const [showSafeZone, setShowSafeZone] = useState(true);
  const [localScenes, setLocalScenes] = useState<any[]>([]);
  const [isApplying, setIsApplying] = useState(false);
  const [applyStatus, setApplyStatus] = useState<string | null>(null);

  const regenerateMutation = useRegenerateAudio();

  const jobNiche = job?.niche || 'Video Project';
  const videoAsset = job?.assets?.find((a: any) => a.type === 'VIDEO' || a.type === 'video');
  const jobMeta = videoAsset?.metadata || {};
  const videoUrl = jobMeta.video_url || (videoAsset?.path ? `/output/${videoAsset.path.split(/[\\/]/).pop()}` : null);
  const scenes = jobMeta.scenes || [];
  const hookText = jobMeta.script?.hook || `The truth about ${jobNiche}`;

  useEffect(() => {
    if (scenes.length > 0) {
      setLocalScenes(scenes);
    }
  }, [job]);

  if (!isOpen) return null;

  const handleDurationDelta = (idx: number, delta: number) => {
    setLocalScenes(prev => {
      const copy = [...prev];
      const cur = Number(copy[idx]?.duration || 1.5);
      const next = Math.max(0.8, Math.min(6.0, Math.round((cur + delta) * 10) / 10));
      copy[idx] = { ...copy[idx], duration: next };
      return copy;
    });
  };

  const handleGradeChange = (idx: number, grade: string) => {
    setLocalScenes(prev => {
      const copy = [...prev];
      copy[idx] = { ...copy[idx], grade };
      return copy;
    });
  };

  const handleSfxChange = (idx: number, sfx: string) => {
    setLocalScenes(prev => {
      const copy = [...prev];
      copy[idx] = { ...copy[idx], sfx };
      return copy;
    });
  };

  const totalCalculatedDur = localScenes.reduce((acc, s) => acc + (Number(s.duration) || 1.5), 0);

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-sm p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="studio-modal-title"
    >
      <div className="bg-[#0f1422] border border-[var(--ln)] rounded-2xl w-full max-w-5xl max-h-[92vh] flex flex-col shadow-2xl overflow-hidden animate-in fade-in zoom-in-95">
        
        {/* Header */}
        <div className="p-4 border-b border-[var(--ln)] flex items-center justify-between bg-[#151a2d] shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center font-bold text-white text-sm">
              <Film size={18} />
            </div>
            <div>
              <div id="studio-modal-title" className="font-semibold text-white text-base flex items-center gap-2">
                9:16 Vertical Inspector: {jobNiche}
                <Badge variant="success">9:16 Locked</Badge>
              </div>
              <div className="text-xs text-[var(--mu)]">Frame composition, cut durations, color grading & SFX placement</div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowSafeZone(!showSafeZone)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                showSafeZone
                  ? 'bg-cyan-950/80 text-cyan-300 border-cyan-500/50 hover:bg-cyan-900/80'
                  : 'bg-slate-800 text-slate-300 border-slate-700 hover:text-white'
              }`}
            >
              {showSafeZone ? <Eye size={14} /> : <EyeOff size={14} />}
              <span>{showSafeZone ? 'Hide Safe Zone' : 'Show Safe Zone'}</span>
            </button>

            <button 
              onClick={onClose}
              aria-label="Close"
              className="text-[var(--mu)] hover:text-white text-lg p-1.5 rounded-lg hover:bg-white/10 flex items-center justify-center cursor-pointer"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Studio Content */}
        <div className="flex-1 overflow-y-auto p-6 flex flex-col lg:flex-row items-center lg:items-start justify-center gap-8 bg-[#0b0e17]">
          
          {/* Vertical 9:16 Phone Mockup */}
          <div className="flex flex-col items-center shrink-0 sticky top-0">
            <div className="relative w-[280px] h-[498px] rounded-[32px] p-2 bg-gradient-to-b from-slate-700 via-slate-800 to-slate-900 border-2 border-slate-600 shadow-2xl flex items-center justify-center overflow-hidden">
              {/* Dynamic Island / Speaker Notch */}
              <div className="absolute top-3 left-1/2 -translate-x-1/2 w-20 h-4 bg-black rounded-full z-40 border border-white/10" />

              <div className="relative w-full h-full rounded-[24px] overflow-hidden bg-black flex items-center justify-center">
                {videoUrl ? (
                  <video 
                    controls 
                    playsInline
                    autoPlay
                    loop
                    src={videoUrl} 
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="text-center p-6 text-[var(--mu)] text-xs">
                    Rendering video sequence...
                  </div>
                )}

                {/* Platform Safe Zone Overlay */}
                <SafeZoneOverlay 
                  visible={showSafeZone}
                  caption={hookText}
                />
              </div>
            </div>

            <div className="flex items-center justify-between w-full mt-3 text-xs text-[var(--mu)] px-2 font-mono">
              <span className="flex items-center gap-1">
                <Shield size={13} className="text-cyan-400" />
                1080 x 1920
              </span>
              <span className="flex items-center gap-1 text-slate-300">
                <Clock size={13} className="text-blue-400" />
                {totalCalculatedDur.toFixed(1)}s Total
              </span>
            </div>
          </div>

          {/* Sequence Shots Breakdown & Direct Controls */}
          <div className="flex-1 w-full space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-slate-800">
              <div>
                <h3 className="text-sm font-semibold text-white">Interactive Shot Timeline</h3>
                <p className="text-[11px] text-slate-400">Adjust individual cut pacing, color grade treatment, and SFX cues.</p>
              </div>
              <span className="text-xs text-blue-400 font-mono bg-blue-950/60 border border-blue-500/30 px-2 py-0.5 rounded">
                {localScenes.length} Beats
              </span>
            </div>

            <div className="space-y-2.5 max-h-[58vh] overflow-y-auto pr-1">
              {localScenes.map((sc: any, idx: number) => {
                const thumbUrl = sc.image_path ? `/${sc.image_path.replace(/\\/g, '/')}` : null;
                return (
                  <div key={idx} className="p-3 bg-slate-900/70 border border-slate-800 hover:border-slate-700 rounded-xl space-y-2 transition-all">
                    <div className="flex items-center justify-between gap-3">
                      <div className="flex items-center gap-2.5">
                        <span className="w-6 h-6 rounded-md bg-blue-600/20 text-blue-400 border border-blue-500/30 flex items-center justify-center text-xs font-bold shrink-0">
                          {idx + 1}
                        </span>
                        <span className="text-xs font-semibold text-white">
                          {sc.badge || `BEAT ${idx + 1}`}
                        </span>
                      </div>

                      {/* Duration Stepper */}
                      <div className="flex items-center gap-1.5 bg-slate-950 px-2 py-1 rounded-lg border border-slate-800">
                        <span className="text-[10px] text-slate-400 font-mono mr-1">Dur:</span>
                        <button
                          onClick={() => handleDurationDelta(idx, -0.5)}
                          className="w-5 h-5 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 flex items-center justify-center text-xs"
                          title="Shorten cut by 0.5s"
                        >
                          <Minus size={11} />
                        </button>
                        <span className="text-xs font-mono font-bold text-sky-300 w-9 text-center">
                          {(Number(sc.duration) || 1.5).toFixed(1)}s
                        </span>
                        <button
                          onClick={() => handleDurationDelta(idx, 0.5)}
                          className="w-5 h-5 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 flex items-center justify-center text-xs"
                          title="Extend cut by 0.5s"
                        >
                          <Plus size={11} />
                        </button>
                      </div>
                    </div>

                    {/* Text or Prompt */}
                    <p className="text-[11px] text-slate-300 line-clamp-2 bg-slate-950/60 p-2 rounded border border-slate-800/80">
                      {sc.text || sc.prompt || "Visual beat"}
                    </p>

                    {/* Color Grade & SFX Selectors */}
                    <div className="flex items-center gap-3 pt-1 text-[11px]">
                      <div className="flex items-center gap-1.5">
                        <Sparkles size={12} className="text-amber-400 shrink-0" />
                        <span className="text-slate-400">Grade:</span>
                        <select
                          value={sc.grade || "hard_bw"}
                          onChange={(e) => handleGradeChange(idx, e.target.value)}
                          className="bg-slate-950 border border-slate-800 rounded px-1.5 py-0.5 text-slate-200 text-[11px] outline-none"
                        >
                          <option value="hard_bw">Hard B&W</option>
                          <option value="teal_split">Teal Split</option>
                          <option value="amber">Amber</option>
                          <option value="natural">Natural</option>
                        </select>
                      </div>

                      <div className="flex items-center gap-1.5">
                        <Volume2 size={12} className="text-emerald-400 shrink-0" />
                        <span className="text-slate-400">SFX:</span>
                        <select
                          value={sc.sfx || "whoosh.wav"}
                          onChange={(e) => handleSfxChange(idx, e.target.value)}
                          className="bg-slate-950 border border-slate-800 rounded px-1.5 py-0.5 text-slate-200 text-[11px] outline-none"
                        >
                          <option value="whoosh.wav">Whoosh</option>
                          <option value="thud.wav">Thud</option>
                          <option value="click.wav">Click</option>
                          <option value="riser.wav">Riser</option>
                        </select>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="pt-3 flex items-center justify-between gap-2 border-t border-slate-800">
              <div className="text-xs text-slate-400">
                {applyStatus && <span className="text-emerald-400 font-medium">{applyStatus}</span>}
              </div>
              <div className="flex items-center gap-2">
                <Button onClick={onClose} variant="ghost" className="!text-xs">
                  Close
                </Button>
                <Button
                  onClick={async () => {
                    if (!job?.id || isApplying) return;
                    setIsApplying(true);
                    setApplyStatus(null);
                    try {
                      await regenerateMutation.mutateAsync({
                        jobId: job.id,
                        voice: jobMeta.voice,
                        scenes: localScenes
                      });
                      setApplyStatus("Beats applied & video re-rendered!");
                      setTimeout(() => setApplyStatus(null), 3000);
                    } catch (e: any) {
                      setApplyStatus(`Error: ${e.message}`);
                    } finally {
                      setIsApplying(false);
                    }
                  }}
                  disabled={isApplying || regenerateMutation.isPending}
                  className="bg-blue-600 hover:bg-blue-500 text-white flex items-center gap-1.5 text-xs font-semibold !py-1.5 !px-3.5 rounded-lg shadow-sm"
                >
                  {isApplying ? <Loader2 size={13} className="animate-spin" /> : <Check size={13} />}
                  <span>{isApplying ? 'Re-rendering 9:16 Video...' : 'Apply Beats & Re-render'}</span>
                </Button>
              </div>
            </div>
          </div>

        </div>

      </div>
    </div>
  );
}
