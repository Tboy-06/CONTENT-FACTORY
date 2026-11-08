import React, { useState } from 'react';
import { Film, X, Shield, Eye, EyeOff } from 'lucide-react';
import { Button, Badge } from './ui';
import SafeZoneOverlay from './SafeZoneOverlay';

interface VideoStudioModalProps {
  isOpen: boolean;
  onClose: () => void;
  job: any;
}

export default function VideoStudioModal({ isOpen, onClose, job }: VideoStudioModalProps) {
  const [showSafeZone, setShowSafeZone] = useState(true);

  if (!isOpen) return null;

  const jobNiche = job?.niche || 'Video Project';
  const videoAsset = job?.assets?.find((a: any) => a.type === 'VIDEO');
  const jobMeta = videoAsset?.metadata || {};
  const videoUrl = jobMeta.video_url || (videoAsset?.path ? `/output/${videoAsset.path.split(/[\\/]/).pop()}` : null);
  const scenes = jobMeta.scenes || [];
  const hookText = jobMeta.script?.hook || `The truth about ${jobNiche}`;

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-sm p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="studio-modal-title"
    >
      <div className="bg-[#0f1422] border border-[var(--ln)] rounded-2xl w-full max-w-4xl max-h-[92vh] flex flex-col shadow-2xl overflow-hidden animate-in fade-in zoom-in-95">
        
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
              <div className="text-xs text-[var(--mu)]">Frame composition, pacing, and TikTok/Shorts safe zones</div>
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
              className="text-[var(--mu)] hover:text-white text-lg p-1.5 rounded-lg hover:bg-white/10 flex items-center justify-center"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Studio Content */}
        <div className="flex-1 overflow-y-auto p-6 flex flex-col md:flex-row items-center md:items-start justify-center gap-8 bg-[#0b0e17]">
          
          {/* Vertical 9:16 Phone Mockup */}
          <div className="flex flex-col items-center shrink-0">
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

            <div className="flex items-center gap-2 mt-3 text-xs text-[var(--mu)]">
              <Shield size={14} className="text-cyan-400" />
              <span>1080 x 1920 (9:16 Vertical Reel)</span>
            </div>
          </div>

          {/* Sequence Shots Breakdown */}
          <div className="flex-1 w-full max-w-xl space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-slate-800">
              <h3 className="text-sm font-semibold text-white">Shot List & Cut Timing</h3>
              <span className="text-xs text-[var(--mu)]">{scenes.length} Scenes Total</span>
            </div>

            <div className="space-y-2.5">
              {scenes.map((sc: any, idx: number) => (
                <div key={idx} className="p-3 bg-slate-900/60 border border-slate-800 rounded-xl flex items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <div className="w-7 h-7 rounded-lg bg-blue-600/20 text-blue-400 border border-blue-500/30 flex items-center justify-center text-xs font-bold shrink-0">
                      {idx + 1}
                    </div>
                    <div>
                      <div className="text-xs font-semibold text-white flex items-center gap-2">
                        {sc.badge || `SCENE ${idx+1}`}
                        <span className="text-[10px] text-slate-500 font-mono">({sc.duration}s)</span>
                      </div>
                      <p className="text-[11px] text-slate-300 line-clamp-1 mt-0.5">{sc.text}</p>
                    </div>
                  </div>
                  {sc.image_path && (
                    <span className="text-[10px] text-emerald-400 bg-emerald-950/60 border border-emerald-500/30 px-2 py-0.5 rounded font-mono shrink-0">
                      Rendered
                    </span>
                  )}
                </div>
              ))}
            </div>

            <div className="pt-3 flex justify-end">
              <Button onClick={onClose} variant="ghost" className="!text-xs">
                Close Inspector
              </Button>
            </div>
          </div>

        </div>

      </div>
    </div>
  );
}
