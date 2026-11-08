import { useNavigate } from 'react-router-dom';
import { useJobs, useCacheStatus, useClearCache } from '../api/client';
import { Button } from '../components/ui';
import { Trash2 } from 'lucide-react';

export default function Dashboard() {
  const navigate = useNavigate();
  const { data: jobs = [] } = useJobs();
  const { data: cache } = useCacheStatus();
  const clearCacheMutation = useClearCache();

  const activeJobs = jobs.filter((j: any) => j.status === 'RUNNING' || j.status === 'PENDING' || j.status === 'QUEUED');
  const qcJobs = jobs.filter((j: any) => j.status === 'AWAITING_APPROVAL' || j.current_stage === 'QC1');
  const recentJobs = jobs.filter((j: any) => j.status === 'COMPLETED' || j.status === 'PUBLISHED').slice(0, 5);

  return (
    <div className="animate-in fade-in min-h-full flex flex-col pb-8">
      <div className="flex justify-between items-center flex-wrap gap-3 mb-6 shrink-0">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight">Dashboard</h1>
          <div className="text-[var(--mu)] text-[13px] mt-1">Your video production studio.</div>
        </div>
      </div>

      <div className="grid grid-cols-[repeat(auto-fit,minmax(250px,1fr))] gap-4 mb-6">
        <div className="glass-panel flex justify-between items-center p-5 bg-gradient-to-br from-[rgba(79,124,255,0.08)] to-[rgba(139,92,255,0.02)] border-[rgba(79,124,255,0.2)]">
          <div>
            <div className="text-[var(--ac)] text-[13px] font-medium mb-1">Active Jobs</div>
            <b className="text-3xl text-white">{activeJobs.length}</b>
          </div>
          <Button onClick={() => navigate('/pipeline')}>View Pipeline</Button>
        </div>
        
        <div className="glass-panel flex justify-between items-center p-5 border-[rgba(245,184,74,0.4)] bg-gradient-to-br from-[rgba(245,184,74,0.1)] to-[rgba(245,184,74,0.02)]">
          <div>
            <div className="text-[var(--wa)] text-[13px] font-medium mb-1">Approvals Needed</div>
            <b className="text-3xl text-[var(--wa)]">{qcJobs.length}</b>
          </div>
          <Button 
            className="!bg-[var(--wa)] !text-[#000]" 
            onClick={() => {
              if (qcJobs.length > 0) navigate(`/qc1/${qcJobs[0].id}`);
              else navigate('/pipeline');
            }}
          >
            Review QC1
          </Button>
        </div>
        
        {/* Real Temp Folder & Cache Counter */}
        <div className="glass-panel flex justify-between items-center p-5">
          <div>
            <div className="text-[var(--mu)] text-[13px] font-medium mb-1">Temp Cache Folder</div>
            <b className="text-3xl">{cache?.temp_mb ?? '0.0'} MB</b>
            <div className="text-[11px] text-slate-500 mt-0.5">{cache?.temp_count ?? 0} intermediate files</div>
          </div>
          <Button 
            variant="secondary"
            onClick={() => clearCacheMutation.mutate()}
            disabled={clearCacheMutation.isPending || !(cache?.temp_mb > 0)}
            className="flex items-center gap-1.5 text-xs border-slate-700"
          >
            <Trash2 size={13} className="text-red-400" />
            <span>{clearCacheMutation.isPending ? 'Clearing...' : 'Clear Cache'}</span>
          </Button>
        </div>
        
        {/* Video Output Storage */}
        <div className="glass-panel flex justify-between items-center p-5">
          <div>
            <div className="text-[var(--mu)] text-[13px] font-medium mb-1">Output Storage</div>
            <b className="text-3xl">{cache?.output_mb ?? '0.0'} MB</b>
            <div className="text-[11px] text-slate-500 mt-0.5">{cache?.output_count ?? 0} finished renders</div>
          </div>
        </div>
      </div>

      <h2 className="font-semibold text-[15px] mb-3">Recent Videos</h2>
      {recentJobs.length === 0 ? (
        <div className="glass-panel p-6 text-center text-[var(--mu)]">
          No finished videos yet.
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          {recentJobs.map((job: any) => (
            <div key={job.id} className="glass-panel p-3 flex justify-between items-center cursor-pointer hover:bg-[var(--gl2)] transition-colors" onClick={() => navigate('/vault')}>
              <div>
                <b className="font-medium text-[14px]">{job.niche}</b>
                <div className="text-[12px] text-[var(--mu)]">Finished {new Date(job.updated_at || Date.now()).toLocaleDateString()}</div>
              </div>
              <Button variant="ghost" className="text-xs py-1 h-auto">View in Vault</Button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
