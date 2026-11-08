import { useState, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useJobs, useApproveJob, useRejectJob } from '../api/client';
import { Button, Badge, Tabs } from '../components/ui';
import { useConnectivity } from '../lib/connectivity';
import { Film } from 'lucide-react';
import VideoStudioModal from '../components/VideoStudioModal';

export default function QC1() {
  const { id } = useParams();
  const navigate = useNavigate();
  const isOnline = useConnectivity();
  const { data: jobs = [] } = useJobs();
  
  const [activeTab, setActiveTab] = useState('Script');
  const [isStudioOpen, setIsStudioOpen] = useState(false);
  
  const approveMutation = useApproveJob();
  const rejectMutation = useRejectJob();

  const job = useMemo(() => jobs.find((j: any) => String(j.id) === id), [jobs, id]);
  
  if (!job) {
    return <div className="p-8 text-center text-[var(--mu)]">Loading job details...</div>;
  }

  const isFree = !job.config?.premium;
  const isApproved = job.status !== 'AWAITING_APPROVAL' && job.status !== 'PENDING';

  // Dynamic asset resolution
  const videoAsset = job?.assets?.find((a: any) => a.type === 'VIDEO');
  const jobMeta = videoAsset?.metadata || {};
  const videoUrl = jobMeta.video_url || (videoAsset?.path ? `/output/${videoAsset.path.split(/[\\/]/).pop()}` : null);
  const realScenes = jobMeta.scenes || [];
  const realScript = jobMeta.script || {};
  const hookText = realScript.hook || `Discover the truth behind ${job.niche}.`;
  const bodyText = realScript.body || "A comprehensive breakdown formulated dynamically for this sequence.";
  const ctaText = realScript.cta || "Save this video and follow for more.";
  const voiceName = jobMeta.voice || job.config?.voice || 'Aria';
  const totalDuration = jobMeta.duration ? `${Math.round(jobMeta.duration)}s` : '18s';
  
  const handleApprove = async () => {
    if (approveMutation.isPending) return;
    try {
      await approveMutation.mutateAsync({ jobId: String(job.id) });
    } catch(e) {
      console.error(e);
    }
  };

  const handleReject = async () => {
    if (rejectMutation.isPending) return;
    try {
      await rejectMutation.mutateAsync({ jobId: String(job.id), reason: 'User requested rejection' });
      navigate('/pipeline');
    } catch(e) {
      console.error(e);
    }
  };

  const thumbnails = ['mountain', 'forest', 'city', 'ocean', 'night', 'warm'];

  return (
    <div className="animate-in fade-in min-h-full flex flex-col pb-8">
      <div className="flex justify-between items-center flex-wrap gap-3 mb-4 shrink-0">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight flex items-center gap-2">
            Storyboard approval 
            {isApproved ? <Badge variant="success">Approved · Rendering</Badge> : <Badge variant="warning">QC1 stage · Manual review</Badge>}
          </h1>
          <div className="text-[var(--mu)] text-[13px]">{job.niche}. Nothing renders until you approve.</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1.5fr_1fr] gap-4 flex-1 overflow-y-auto">
        
        {/* Left Side: Real Video Player or Scene Plates */}
        <div className="glass-panel p-4 flex flex-col gap-3">
          <div className="relative aspect-[9/16] max-h-[460px] rounded-xl overflow-hidden bg-black flex items-center justify-center border border-slate-800 mx-auto w-full">
            {videoUrl ? (
              <video 
                controls 
                playsInline
                src={videoUrl} 
                className="w-full h-full object-contain"
              />
            ) : (
              <div className="text-center p-6 text-[var(--mu)] text-xs">
                Video rendering in progress. When ready, playback will stream directly here.
              </div>
            )}
          </div>
          
          {realScenes.length > 0 && (
            <div className="grid grid-cols-4 gap-2 mt-1">
              {realScenes.map((sc: any, idx: number) => (
                <div 
                  key={idx}
                  className="p-2 border border-slate-800 rounded-lg bg-slate-900/60 text-[11px] text-slate-300 flex flex-col justify-between truncate"
                >
                  <span className="font-semibold text-sky-400">{sc.badge || `Scene ${idx+1}`}</span>
                  <span className="text-[10px] text-slate-500 font-mono mt-1">{sc.duration}s</span>
                </div>
              ))}
            </div>
          )}
          <div className="text-[13px] text-[var(--mu)]">Sequence playback and cuts. Tap Edit in Studio to customize in OpenCut / Nuzky.</div>
        </div>

        {/* Right Side: Dynamic Script & Configuration */}
        <div className="glass-panel p-4 flex flex-col min-h-0">
          <Tabs tabs={['Script', 'Scenes', 'Visuals']} activeTab={activeTab} onChange={setActiveTab} />
          
          <div className="flex-1 overflow-auto text-[13px] mb-4">
            {activeTab === 'Script' && (
              <div className="space-y-4">
                <div className="text-white font-medium">Title: {job.niche}</div>
                <div>
                  <b className="text-sky-400 text-xs uppercase tracking-wide">Hook</b><br/>
                  <p className="text-slate-200 mt-1 bg-slate-900/50 p-2.5 rounded-lg border border-slate-800">{hookText}</p>
                </div>
                <div>
                  <b className="text-sky-400 text-xs uppercase tracking-wide">Core Insight</b><br/>
                  <p className="text-slate-200 mt-1 bg-slate-900/50 p-2.5 rounded-lg border border-slate-800">{bodyText}</p>
                </div>
                <div>
                  <b className="text-sky-400 text-xs uppercase tracking-wide">Call To Action</b><br/>
                  <p className="text-slate-200 mt-1 bg-slate-900/50 p-2.5 rounded-lg border border-slate-800">{ctaText}</p>
                </div>
                <div className="text-xs text-[var(--mu)]">
                  Voice Engine: <span className="text-white font-medium">{voiceName} (Edge-TTS Offline Sync)</span>
                </div>
              </div>
            )}
            {activeTab === 'Scenes' && (
              <div className="space-y-2">
                {realScenes.length > 0 ? (
                  realScenes.map((sc: any, idx: number) => (
                    <div key={idx} className="p-3 bg-slate-900/60 border border-slate-800 rounded-lg text-xs flex justify-between items-center">
                      <div className="pr-3">
                        <span className="font-semibold text-sky-400 mr-2">{sc.badge || `Scene ${idx+1}`}:</span>
                        <span className="text-slate-300">{sc.text}</span>
                      </div>
                      <span className="text-slate-500 font-mono shrink-0">{sc.duration}s</span>
                    </div>
                  ))
                ) : (
                  <div className="text-xs text-[var(--mu)]">Scenes will appear here once parsed.</div>
                )}
              </div>
            )}
            {activeTab === 'Visuals' && (
              <div className="space-y-4">
                <div>
                  <b className="text-xs text-sky-400 uppercase tracking-wide">Format & Engine</b><br/>
                  <span className="text-slate-200">Vertical 9:16 (1080x1920) · Rendered via FFmpeg / Nuzky Compositor</span>
                </div>
                <div>
                  <b className="text-xs text-sky-400 uppercase tracking-wide">Captions</b><br/>
                  <span className="text-slate-200">Word-by-word synced subtitle track burned directly to final cut.</span>
                </div>
              </div>
            )}
          </div>
          
          <div className="glass-panel p-3 bg-transparent flex justify-between items-center mb-3">
            <div>
              <div className="text-[var(--mu)] text-[13px]">Production cost</div>
              <div className="text-[11px] text-[var(--mu)]">
                Local free-tier engine: $0.00 API spend
              </div>
            </div>
            <b className="text-xl text-emerald-400">$0.00</b>
          </div>
          
          {!isFree && (
            <div className={`p-2.5 rounded-xl border text-xs mb-4 ${
              isOnline 
                ? 'bg-[rgba(245,184,74,0.1)] border-[rgba(245,184,74,0.4)] text-[var(--wa)]' 
                : 'bg-[rgba(255,107,122,0.1)] border-[rgba(255,107,122,0.4)] text-[var(--er)]'
            }`}>
              {isOnline 
                ? '1 scene may require premium assets. This could raise the cost by about $0.30.' 
                : '1 scene needs a premium asset, which is not available offline. A local stock clip will be used. Reconnect to swap it.'
              }
            </div>
          )}

          <div className="flex gap-2 justify-end flex-wrap mt-auto">
            <Button variant="ghost" className="!bg-[rgba(255,107,122,0.1)] !text-[var(--er)] !border-[rgba(255,107,122,0.4)]" onClick={handleReject} disabled={rejectMutation.isPending || isApproved}>Reject</Button>
            <Button variant="ghost" className="!border-[var(--ac)] text-[var(--ac)] hover:bg-[var(--ac)]/10 flex items-center gap-1.5" onClick={() => setIsStudioOpen(true)}>
              <Film size={15} /> Edit in Studio (OpenCut / Nuzky)
            </Button>
            <Button onClick={handleApprove} disabled={approveMutation.isPending || isApproved}>
              {isApproved ? 'Rendering started' : 'Approve and continue'}
            </Button>
          </div>
        </div>
      </div>

      <VideoStudioModal 
        isOpen={isStudioOpen} 
        onClose={() => setIsStudioOpen(false)} 
        job={job} 
      />
    </div>
  );
}
