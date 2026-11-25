import React, { useState, useEffect, useRef } from 'react';
import { Film, X, Shield, Eye, EyeOff, Clock, Palette, Volume2, Plus, Minus, Loader2, Check } from 'lucide-react';
import { Button, Badge, useDialogLightDismissFallback } from './ui';
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
  const dialogRef = useRef<HTMLDialogElement | null>(null);
  useDialogLightDismissFallback(dialogRef, isOpen);

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

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (isOpen && !dialog.open) {
      dialog.showModal();
    } else if (!isOpen && dialog.open) {
      dialog.close();
    }
  }, [isOpen]);

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
    <dialog
      ref={dialogRef}
      {...({ closedby: 'any' } as any)}
      aria-labelledby="studio-modal-title"
      onClose={onClose}
      className="m-auto p-0 bg-transparent border-0 w-[calc(100%-2rem)] max-w-5xl max-h-[92vh] overflow-visible"
    >
      <div className="light-adapt-surface acrylic-shell w-full max-h-[92vh] flex flex-col shadow-2xl overflow-hidden animate-in fade-in zoom-in-95">
        
        {/* Header */}
        <div className="p-4 border-b border-[var(--ln-subtle)] flex items-center justify-between bg-[var(--gl)] shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-xl bg-blue-600 flex items-center justify-center font-bold text-white text-sm preserve-white shadow-sm">
              <Film size={18} />
            </div>
            <div>
              <h1 id="studio-modal-title" className="font-bold text-[var(--tx)] text-base flex items-center gap-2">
                <span>Vertical & Cinema Inspector: {jobNiche}</span>
                <Badge variant="success">Shot Locked</Badge>
              </h1>
              <div className="text-xs text-[var(--mu)]">Frame composition, cut durations, color grading & SFX placement</div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setShowSafeZone(!showSafeZone)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold border transition-colors cursor-pointer ${
                showSafeZone
                  ? 'bg-cyan-500/15 text-cyan-700 dark:text-cyan-300 border-cyan-500/40'
                  : 'bg-[var(--gl2)] text-[var(--mu)] border-[var(--input-border)] hover:text-[var(--tx)]'
              }`}
            >
              {showSafeZone ? <Eye size={14} /> : <EyeOff size={14} />}
              <span>{showSafeZone ? 'Hide Safe Zone' : 'Show Safe Zone'}</span>
            </button>

            <button 
              type="button"
              onClick={() => dialogRef.current?.close()}
              aria-label="Close"
              className="text-[var(--mu)] hover:text-[var(--tx)] text-lg p-1.5 rounded-lg hover:bg-[var(--gl2)] flex items-center justify-center cursor-pointer"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Studio Content */}
        <div className="flex-1 overflow-y-auto p-6 flex flex-col lg:flex-row items-center lg:items-start justify-center gap-8 bg-[var(--shell-bg)]">
          
          {/* Responsive Preview Mockup (16:9 or 9:16) */}
          <div className="flex flex-col items-center shrink-0 sticky top-0">
            {(() => {
              const isWidescreen = job?.config?.format === '16:9' || (job?.config as any)?.aspect_ratio === '16:9';
              return (
                <>
                  {isWidescreen ? (
                    /* 16:9 Cinema Container */
                    <div className="relative w-full max-w-[460px] aspect-video rounded-2xl p-2 bg-gradient-to-b from-slate-700 via-slate-800 to-slate-900 border-2 border-slate-600 shadow-2xl flex items-center justify-center overflow-hidden">
                      <div className="relative w-full h-full rounded-xl overflow-hidden bg-black flex items-center justify-center">
                        {videoUrl ? (
                          <video 
                            controls 
                            playsInline
                            autoPlay
                            loop
                            src={videoUrl} 
                            className="w-full h-full object-contain"
                          />
                        ) : (
                          <div className="text-center p-6 text-[var(--mu)] text-xs">
                            Rendering 16:9 video sequence...
                          </div>
                        )}
                      </div>
                    </div>
                  ) : (
                    /* 9:16 Phone Container */
                    <div className="relative w-[280px] h-[498px] rounded-[32px] p-2 bg-gradient-to-b from-slate-700 via-slate-800 to-slate-900 border-2 border-slate-600 shadow-2xl flex items-center justify-center overflow-hidden">
                      {/* Dynamic Island / Speaker Notch */}
                      <div className="absolute top-3 left-1/2 -translate-x-1/2 w-20 h-4 bg-black rounded-md z-40 border border-white/10" />

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
                  )}

                  <div className="flex items-center justify-between w-full mt-3 text-xs text-[var(--mu)] px-2 font-mono">
                    <span className="flex items-center gap-1">
                      <Shield size={13} className="text-cyan-600 dark:text-cyan-400" />
                      {isWidescreen ? '1920 x 1080 Widescreen' : '1080 x 1920'}
                    </span>
                    <span className="flex items-center gap-1 text-[var(--tx)]">
                      <Clock size={13} className="text-blue-600 dark:text-blue-400" />
                      {totalCalculatedDur.toFixed(1)}s Total
                    </span>
                  </div>
                </>
              );
            })()}
          </div>

          {/* Sequence Shots Breakdown & Direct Controls */}
          <div className="flex-1 w-full min-w-0 space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-[var(--ln-subtle)]">
              <div>
                <h3 className="text-sm font-bold text-[var(--tx)]">Interactive Shot Timeline</h3>
                <p className="text-[11px] text-[var(--mu)]">Adjust individual cut pacing, color grade treatment, and SFX cues.</p>
              </div>
              <Badge variant="info">{localScenes.length} Beats</Badge>
            </div>

            <div className="scroll-panel-stable space-y-2.5 max-h-[58vh] pr-1">
              {localScenes.map((sc: any, idx: number) => {
                return (
                  <div key={idx} className="glass-subcard p-3 space-y-2">
                    <div className="flex items-center justify-between gap-3">
                      <div className="flex items-center gap-2.5 min-w-0">
                        <span className="w-6 h-6 rounded-md bg-blue-600/15 text-blue-600 dark:text-blue-400 border border-blue-500/30 flex items-center justify-center text-xs font-bold shrink-0">
                          {idx + 1}
                        </span>
                        <span className="text-xs font-semibold text-[var(--tx)] truncate">
                          {sc.badge || `BEAT ${idx + 1}`}
                        </span>
                      </div>

                      {/* Duration Stepper */}
                      <div className="flex items-center gap-1.5 bg-[var(--input-bg)] px-2 py-1 rounded-lg border border-[var(--input-border)]">
                        <span className="text-[10px] text-[var(--mu)] font-mono mr-1">Dur:</span>
                        <button
                          type="button"
                          onClick={() => handleDurationDelta(idx, -0.5)}
                          className="w-5 h-5 rounded bg-[var(--gl2)] hover:border-blue-500 border border-[var(--ln-subtle)] text-[var(--tx)] flex items-center justify-center text-xs cursor-pointer"
                          title="Shorten cut by 0.5s"
                        >
                          <Minus size={11} />
                        </button>
                        <span className="text-xs font-mono font-bold text-blue-600 dark:text-sky-300 w-9 text-center">
                          {(Number(sc.duration) || 1.5).toFixed(1)}s
                        </span>
                        <button
                          type="button"
                          onClick={() => handleDurationDelta(idx, 0.5)}
                          className="w-5 h-5 rounded bg-[var(--gl2)] hover:border-blue-500 border border-[var(--ln-subtle)] text-[var(--tx)] flex items-center justify-center text-xs cursor-pointer"
                          title="Extend cut by 0.5s"
                        >
                          <Plus size={11} />
                        </button>
                      </div>
                    </div>

                    {/* Text or Prompt */}
                    <p className="text-[11px] text-[var(--tx)] line-clamp-2 bg-[var(--input-bg)] p-2 rounded-lg border border-[var(--ln-subtle)]">
                      {sc.text || sc.prompt || 'Visual beat'}
                    </p>

                    {/* Color Grade & SFX Selectors */}
                    <div className="flex items-center flex-wrap gap-3 pt-1 text-[11px]">
                      <div className="flex items-center gap-1.5">
                        <Palette size={12} className="text-[var(--mu)] shrink-0" />
                        <span className="text-[var(--mu)]">Grade:</span>
                        <select
                          value={sc.grade || 'hard_bw'}
                          onChange={(e) => handleGradeChange(idx, e.target.value)}
                          className="glass-input !rounded-md px-2 py-0.5 text-[11px] cursor-pointer"
                        >
                          <option value="hard_bw">Hard B&amp;W</option>
                          <option value="teal_split">Teal Split</option>
                          <option value="amber">Amber</option>
                          <option value="natural">Natural</option>
                        </select>
                      </div>

                      <div className="flex items-center gap-1.5">
                        <Volume2 size={12} className="text-emerald-600 dark:text-emerald-400 shrink-0" />
                        <span className="text-[var(--mu)]">SFX:</span>
                        <select
                          value={sc.sfx || 'whoosh.wav'}
                          onChange={(e) => handleSfxChange(idx, e.target.value)}
                          className="glass-input !rounded-md px-2 py-0.5 text-[11px] cursor-pointer"
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

            <div className="pt-3 flex items-center justify-between gap-2 border-t border-[var(--ln-subtle)]">
              <div className="text-xs text-[var(--mu)]" role="status">
                {applyStatus && <span className="text-emerald-600 dark:text-emerald-400 font-semibold">{applyStatus}</span>}
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
                  className="bg-blue-600 hover:bg-blue-500 text-white preserve-white flex items-center gap-1.5 text-xs font-semibold !py-1.5 !px-3.5 rounded-lg shadow-sm"
                >
                  {isApplying ? <Loader2 size={13} className="animate-spin" /> : <Check size={13} />}
                  <span>{isApplying ? 'Re-rendering 9:16 Video...' : 'Apply Beats & Re-render'}</span>
                </Button>
              </div>
            </div>
          </div>

        </div>

      </div>
    </dialog>
  );
}
