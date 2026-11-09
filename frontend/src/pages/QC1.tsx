import { useState, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useJobs, useApproveJob, useRejectJob } from '../api/client';
import { Thumbnail } from '../components/Thumbnails';
import { Button, Badge, Tabs } from '../components/ui';
import { useConnectivity } from '../lib/connectivity';

export default function QC1() {
  const { id } = useParams();
  const navigate = useNavigate();
  const isOnline = useConnectivity();
  const { data: jobs = [] } = useJobs();
  
  const [activeTab, setActiveTab] = useState('Scenes');
  const [activeThumb, setActiveThumb] = useState('mountain');
  
  const approveMutation = useApproveJob();
  const rejectMutation = useRejectJob();

  const job = useMemo(() => jobs.find((j: any) => String(j.id) === id), [jobs, id]);
  
  if (!job) {
    return <div className="p-8 text-center text-[var(--mu)]">Loading job details...</div>;
  }

  const isFree = !job.config?.premium;
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
        
        {/* Left Side: Preview & Scenes */}
        <div className="glass-panel p-4 flex flex-col gap-3">
          <div className="relative aspect-video rounded-xl overflow-hidden bg-black">
            <Thumbnail type={activeThumb} className="w-full h-full rounded-none" />
            <div className="absolute inset-0 m-auto w-[54px] h-[54px] rounded-full bg-white/20 border border-white/40 flex items-center justify-center cursor-pointer hover:bg-white/30 transition-colors">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="#fff"><path d="M8 5v14l11-7z"/></svg>
            </div>
          </div>
          
          <div className="grid grid-cols-6 gap-2 mt-1">
            {thumbnails.map(t => (
              <div 
                key={t}
                onClick={() => setActiveThumb(t)}
                className={`h-12 border-2 rounded-lg overflow-hidden cursor-pointer ${activeThumb === t ? 'border-[var(--ac)]' : 'border-transparent'}`}
              >
                <Thumbnail type={t} className="w-full h-full rounded-none" />
              </div>
            ))}
          </div>
          <div className="text-[13px] text-[var(--mu)]">Scene thumbnails. Click one to inspect it.</div>
        </div>

        {/* Right Side: Script & Config */}
        <div className="glass-panel p-4 flex flex-col min-h-0">
          <Tabs tabs={['Scenes']} activeTab={activeTab} onChange={setActiveTab} />
          
          <div className="flex-1 overflow-auto text-[13px] mb-4">

            {activeTab === 'Scenes' && (
              <div className="space-y-2 text-[var(--mu)]">
                <p>1. Sunrise, window light · 8s</p>
                <p>2. Morning routine · 12s</p>
                <p>3. Focus at the desk · 12s</p>
                <p>4. City commute · 10s</p>
                <p>5. Small changes, big results · 12s</p>
                <p>6. End card · 6s</p>
              </div>
            )}

          </div>
          
          <div className="glass-panel p-3 bg-transparent flex justify-between items-center mb-3">
            <div>
              <div className="text-[var(--mu)] text-[13px]">Estimated cost</div>
              <div className="text-[11px] text-[var(--mu)]">
                {isFree ? 'Local and free-tier engines, no paid calls' : 'Narration $0.12, b-roll $0.38, render $0.25'}
              </div>
            </div>
            <b className="text-xl">{isFree ? '$0.00' : '~$0.75'}</b>
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
            <Button onClick={handleApprove} disabled={approveMutation.isPending || isApproved}>
              {isApproved ? 'Rendering started' : 'Approve and continue'}
            </Button>
          </div>
        </div>
      </div>

    </div>
  );
}