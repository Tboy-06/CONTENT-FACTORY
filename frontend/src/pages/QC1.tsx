import { useState, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useJobs, useApproveJob, useRejectJob } from '../api/client';
import { Button, Badge } from '../components/ui';
import { useConnectivity } from '../lib/connectivity';
import { RefreshCw, Play, Save, CheckCircle2, Trash2 } from 'lucide-react';

export default function QC1() {
  const { id } = useParams();
  const navigate = useNavigate();
  const isOnline = useConnectivity();
  const { data: jobs = [] } = useJobs();
  
  const approveMutation = useApproveJob();
  const rejectMutation = useRejectJob();

  const job = useMemo(() => jobs.find((j: any) => String(j.id) === id), [jobs, id]);
  
  if (!job) {
    return <div className="p-8 text-center text-[var(--mu)]">Loading job details...</div>;
  }

  const isApproved = job.status !== 'AWAITING_APPROVAL' && job.status !== 'PENDING';
  
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

  // Mock Storyboard Data for the grid
  const storyboard = Array.from({length: 12}).map((_, i) => ({
    id: i,
    thumb: `https://images.unsplash.com/photo-1${500000000000 + i}?auto=format&fit=crop&w=400&q=80`,
    script: "This is a dramatic line of spoken text that will be synthesized by Edge-TTS.",
    prompt: "dark cinematic atmosphere, highly detailed, dramatic lighting"
  }));

  return (
    <div className="animate-in fade-in min-h-full flex flex-col pb-8">
      <div className="flex justify-between items-center flex-wrap gap-3 mb-4 shrink-0">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight flex items-center gap-2">
            Review & Storyboard
            {isApproved ? <Badge variant="success">Approved</Badge> : <Badge variant="warning">QC1 Review</Badge>}
          </h1>
          <div className="text-[var(--mu)] text-[13px]">{job.niche}</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_2fr] gap-4 flex-1 overflow-y-hidden">
        
        {/* Left Side: 9:16 Preview Player */}
        <div className="glass-panel p-4 flex flex-col gap-3 h-full">
          <div className="relative aspect-[9/16] rounded-xl overflow-hidden bg-black mx-auto max-h-full">
             <div className="absolute inset-0 bg-gradient-to-t from-black/80 to-transparent flex flex-col justify-end p-4">
                <div className="text-white text-center font-bold text-lg mb-8 drop-shadow-md">
                   Spoken text overlay goes here
                </div>
             </div>

            <div className="absolute inset-0 m-auto w-[64px] h-[64px] rounded-full bg-white/20 border border-white/40 flex items-center justify-center cursor-pointer hover:bg-white/30 transition-colors">
              <Play fill="#fff" />
            </div>

            {/* TikTok Safe Zone Overlay */}
            <div className="absolute inset-0 pointer-events-none border-[2px] border-dashed border-red-500/50 m-4 rounded-xl flex items-center justify-center">
              <span className="text-red-500/50 font-mono text-xs absolute top-2 right-2">SAFE ZONE</span>
            </div>
          </div>
        </div>

        {/* Right Side: 12-Card Storyboard Grid */}
        <div className="glass-panel p-4 flex flex-col min-h-0 relative">
          
          <div className="flex-1 overflow-y-auto pr-2 pb-20">
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
              {storyboard.map(scene => (
                 <div key={scene.id} className="bg-slate-900/50 rounded-lg p-2.5 border border-slate-800 flex flex-col gap-2">
                    <div className="aspect-[9/16] rounded-md overflow-hidden bg-black relative max-h-[160px] mx-auto w-full">
                       <img src={scene.thumb} className="w-full h-full object-cover" />
                       <div className="absolute top-1 left-1 bg-black/60 text-white text-[10px] px-1.5 rounded">Shot {scene.id + 1}</div>
                    </div>
                    <textarea defaultValue={scene.script} className="w-full h-[50px] bg-slate-800/50 border border-slate-700 rounded text-xs p-1.5 text-slate-300 resize-none focus:border-blue-500 outline-none" title="Spoken Script" />
                    <textarea defaultValue={scene.prompt} className="w-full h-[40px] bg-slate-800/50 border border-slate-700 rounded text-[10px] p-1.5 text-slate-400 resize-none focus:border-amber-500 outline-none font-mono" title="Image Prompt" />
                    <div className="flex items-center gap-1.5 justify-end">
                       <Button variant="ghost" className="text-[10px] py-1 px-2 h-auto text-slate-400 hover:text-amber-400"><RefreshCw size={10} className="mr-1"/> Re-roll Visual</Button>
                       <Button variant="ghost" className="text-[10px] py-1 px-2 h-auto text-slate-400 hover:text-blue-400"><RefreshCw size={10} className="mr-1"/> Audio</Button>
                    </div>
                 </div>
              ))}
            </div>
          </div>

          {/* Bottom Action Bar */}
          <div className="absolute bottom-0 left-0 right-0 glass-panel border-t border-[var(--ln)] rounded-t-none p-3 bg-[var(--bg)] flex justify-between items-center z-10">
            <div className="flex items-center gap-4 text-xs text-slate-300">
               <label className="flex items-center gap-1.5"><input type="checkbox" defaultChecked className="rounded border-slate-700 bg-slate-800" /> TikTok</label>
               <label className="flex items-center gap-1.5"><input type="checkbox" defaultChecked className="rounded border-slate-700 bg-slate-800" /> YT Shorts</label>
               <label className="flex items-center gap-1.5"><input type="checkbox" defaultChecked className="rounded border-slate-700 bg-slate-800" /> Reels</label>

               <Badge variant="success" className="flex items-center gap-1"><CheckCircle2 size={12} /> Cookie Status: Active</Badge>
            </div>

            <div className="flex gap-2">
              <Button variant="ghost" className="!bg-[rgba(255,107,122,0.1)] !text-[var(--er)] !border-[rgba(255,107,122,0.4)] flex items-center gap-1.5" onClick={handleReject} disabled={rejectMutation.isPending || isApproved}>
                 <Trash2 size={14} /> Delete & Clean Temp Files
              </Button>
              <Button onClick={handleApprove} disabled={approveMutation.isPending || isApproved} className="flex items-center gap-1.5 bg-blue-600 hover:bg-blue-500 text-white">
                <Save size={14} /> {isApproved ? 'Publishing...' : 'Approve & Publish'}
              </Button>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}