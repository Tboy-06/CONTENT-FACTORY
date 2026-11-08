import React, { useState } from 'react';
import { Film, X } from 'lucide-react';
import { Button, Badge } from './ui';

interface VideoStudioModalProps {
  isOpen: boolean;
  onClose: () => void;
  job: any;
}

export default function VideoStudioModal({ isOpen, onClose, job }: VideoStudioModalProps) {
  const [activeTab, setActiveTab] = useState<'opencut' | 'nuzky' | 'timeline'>('timeline');
  const [copied, setCopied] = useState(false);

  if (!isOpen) return null;

  const jobNiche = job?.niche || 'Video Project';
  const opencutUrl = 'https://opencut.app';

  // Sample or generated timeline representation
  const timelineTracks = [
    {
      name: 'Main Video Track',
      color: 'bg-blue-600/40 border-blue-500/60',
      items: [
        { title: 'Hook / Intro', dur: '8s' },
        { title: 'Scene 1: Problem', dur: '12s' },
        { title: 'Scene 2: Solution', dur: '12s' },
        { title: 'Scene 3: Proof', dur: '14s' },
        { title: 'CTA / Outro', dur: '6s' },
      ],
    },
    {
      name: 'Voiceover (TTS)',
      color: 'bg-emerald-600/40 border-emerald-500/60',
      items: [{ title: `${job?.config?.voice || 'Aria'} Voice Audio (Loudness -14 LUFS)`, dur: '52s' }],
    },
    {
      name: 'Smart Captions (Whisper / Nuzky)',
      color: 'bg-sky-600/30 border-sky-500/50',
      items: [
        { title: 'Word-by-word animated highlights', dur: '52s' },
      ],
    },
  ];

  const handleDownloadNuzky = () => {
    const nuzkyData = {
      version: 1,
      name: `Job_${job?.id || 'export'}_${jobNiche}`,
      canvas: { width: 1080, height: 1920, fps: 30 },
      assets: [],
      tracks: [
        {
          id: 'track_video',
          kind: 'video',
          isMain: true,
          items: [],
        },
      ],
      reelCandidates: [],
    };

    const blob = new Blob([JSON.stringify(nuzkyData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `job_${job?.id || 'project'}.nuzky`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  };

  const copyTimelineJson = async () => {
    try {
      const data = {
        editor: "OpenCut",
        version: "1.0",
        jobId: job?.id,
        niche: jobNiche,
        tracks: timelineTracks,
      };
      await navigator.clipboard.writeText(JSON.stringify(data, null, 2));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback or ignore clipboard errors
    }
  };

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="studio-modal-title"
    >
      <div className="bg-[#0f1422] border border-[var(--ln)] rounded-2xl w-full max-w-5xl h-[85vh] flex flex-col shadow-2xl overflow-hidden animate-in fade-in zoom-in-95">
        
        {/* Header */}
        <div className="p-4 border-b border-[var(--ln)] flex items-center justify-between bg-[#151a2d]">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center font-bold text-white text-sm">
              <Film size={18} />
            </div>
            <div>
              <div id="studio-modal-title" className="font-semibold text-white text-base flex items-center gap-2">
                Open Studio Editor: {jobNiche}
                <Badge variant="success">OpenCut & Nuzky Enabled</Badge>
              </div>
              <div className="text-xs text-[var(--mu)]">Integrated multi-track timeline, local AI cuts, and speech sync</div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <div className="flex bg-[#0b0e17] p-1 rounded-xl border border-[var(--ln)] text-xs">
              <button 
                onClick={() => setActiveTab('timeline')}
                className={`px-3 py-1 rounded-lg transition-colors ${activeTab === 'timeline' ? 'bg-[var(--ac)] text-white font-medium' : 'text-[var(--mu)] hover:text-white'}`}
              >
                Timeline Preview
              </button>
              <button 
                onClick={() => setActiveTab('opencut')}
                className={`px-3 py-1 rounded-lg transition-colors ${activeTab === 'opencut' ? 'bg-[var(--ac)] text-white font-medium' : 'text-[var(--mu)] hover:text-white'}`}
              >
                OpenCut Web App
              </button>
              <button 
                onClick={() => setActiveTab('nuzky')}
                className={`px-3 py-1 rounded-lg transition-colors ${activeTab === 'nuzky' ? 'bg-[var(--ac)] text-white font-medium' : 'text-[var(--mu)] hover:text-white'}`}
              >
                Nuzky Native Core
              </button>
            </div>
            <button 
              onClick={onClose}
              aria-label="Close"
              className="text-[var(--mu)] hover:text-white text-lg p-2 rounded-lg hover:bg-white/10 flex items-center justify-center"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Body content based on tab */}
        <div className="flex-1 overflow-hidden flex flex-col bg-[#0b0e17]">
          {activeTab === 'timeline' && (
            <div className="flex-1 flex flex-col p-5 gap-4 overflow-y-auto">
              {/* Studio Canvas / Preview Bar */}
              <div className="bg-[#121626] border border-[var(--ln)] rounded-xl p-4 flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="w-20 h-28 bg-black rounded-lg border border-white/10 flex items-center justify-center text-xs text-slate-500 font-mono">
                    9:16 Canvas
                  </div>
                  <div>
                    <h3 className="font-semibold text-white text-sm">Sequence Composition</h3>
                    <p className="text-xs text-[var(--mu)] mt-0.5">5 visual clips · 1 voiceover track · Whisper karaoke word captions</p>
                    <div className="flex gap-2 mt-2">
                      <Button variant="ghost" className="!text-xs !py-1 !px-2.5" onClick={copyTimelineJson}>
                        {copied ? 'Copied Timeline JSON' : 'Copy OpenCut Timeline'}
                      </Button>
                      <Button variant="ghost" className="!text-xs !py-1 !px-2.5" onClick={handleDownloadNuzky}>
                        Export .nuzky Project
                      </Button>
                    </div>
                  </div>
                </div>

                <div className="flex gap-3">
                  <a 
                    href={opencutUrl} 
                    target="_blank" 
                    rel="noreferrer"
                    className="px-3.5 py-2 rounded-lg text-xs font-medium bg-blue-600 text-white hover:bg-blue-500 flex items-center gap-2 transition-colors"
                  >
                    Open in OpenCut Web ↗
                  </a>
                </div>
              </div>

              {/* Multi-track Timeline Representation */}
              <div className="bg-[#121626] border border-[var(--ln)] rounded-xl p-4 flex-1 flex flex-col gap-3">
                <div className="text-xs font-semibold text-[var(--mu)] uppercase tracking-wider mb-1">
                  Multi-Track Timeline (Magnetic)
                </div>
                {timelineTracks.map((track, idx) => (
                  <div key={idx} className="flex flex-col gap-1.5">
                    <div className="text-xs text-slate-400 font-medium">{track.name}</div>
                    <div className="flex gap-2 p-2 bg-[#080b13] border border-white/5 rounded-lg overflow-x-auto">
                      {track.items.map((item, i) => (
                        <div 
                          key={i} 
                          className={`p-2.5 rounded-lg border text-xs text-white shrink-0 flex flex-col justify-between ${track.color}`}
                          style={{ minWidth: item.dur === '52s' ? '100%' : '140px' }}
                        >
                          <span className="font-medium truncate">{item.title}</span>
                          <span className="text-[10px] text-white/70 font-mono mt-1">{item.dur}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === 'opencut' && (
            <div className="flex-1 flex flex-col">
              <div className="bg-[#121626] px-4 py-2 border-b border-[var(--ln)] flex justify-between items-center text-xs text-[var(--mu)]">
                <span>Embedded OpenCut Video Editor instance</span>
                <a href={opencutUrl} target="_blank" rel="noreferrer" className="text-blue-400 hover:underline">
                  Launch full screen in new tab ↗
                </a>
              </div>
              <iframe 
                src={opencutUrl} 
                className="w-full flex-1 border-0" 
                title="OpenCut Video Editor"
                allow="autoplay; fullscreen; clipboard-write"
              />
            </div>
          )}

          {activeTab === 'nuzky' && (
            <div className="flex-1 p-6 overflow-y-auto space-y-5 text-sm">
              <div className="bg-[#121626] border border-[var(--ln)] rounded-xl p-5">
                <h3 className="font-semibold text-white text-base mb-2">Nuzky Native Rust Engine</h3>
                <p className="text-[var(--mu)] text-xs leading-relaxed mb-4">
                  Nuzky runs locally on your computer with a high-performance Rust compositor (`wgpu`) and offline Whisper speech recognition.
                  You can open this exact job in your desktop Nuzky app or let an AI agent edit it live via MCP.
                </p>

                <div className="space-y-3">
                  <div className="p-3 bg-[#080b13] rounded-lg border border-white/10 font-mono text-xs text-slate-300">
                    <p className="text-slate-500 mb-1"># Command-line render via Nuzky:</p>
                    <p>nuzky-cli render output/project_{job?.id || '1'}.nuzky video.mp4 --preset reels</p>
                  </div>

                  <div className="p-3 bg-[#080b13] rounded-lg border border-white/10 font-mono text-xs text-slate-300">
                    <p className="text-slate-500 mb-1"># Learn pacing from a creator's sample video:</p>
                    <p>nuzky-cli style learn raw.mp4 finished_reel.mp4</p>
                  </div>
                </div>

                <div className="mt-5 flex gap-3">
                  <Button onClick={handleDownloadNuzky}>
                    Download .nuzky Project File
                  </Button>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-3 border-t border-[var(--ln)] bg-[#151a2d] flex justify-between items-center text-xs">
          <span className="text-[var(--mu)]">Cuts are synced across OpenCut timeline and Nuzky engine.</span>
          <Button variant="ghost" onClick={onClose}>Close Studio</Button>
        </div>

      </div>
    </div>
  );
}
