import { useNavigate } from 'react-router-dom';
import { useJobs, useCacheStatus, useClearCache, useDeleteJob } from '../api/client';
import { Button } from '../components/ui';
import { Trash2 } from 'lucide-react';

export default function Dashboard() {
  const navigate = useNavigate();
  const { data: jobs = [] } = useJobs();
  const { data: cache } = useCacheStatus();
  const clearCacheMutation = useClearCache();
  const deleteJobMutation = useDeleteJob();

  const activeJobs = jobs.filter((j: any) => j.status === 'RUNNING' || j.status === 'PENDING' || j.status === 'QUEUED');
  const qcJobs = jobs.filter((j: any) => j.status === 'AWAITING_APPROVAL' || j.current_stage === 'QC1');
  const recentJobs = jobs.filter((j: any) => j.status === 'COMPLETED' || j.status === 'PUBLISHED').slice(0, 5);

  return (
    <div className="animate-in fade-in min-h-full flex flex-col pb-8">
      <div className="flex justify-between items-center flex-wrap gap-3 mb-6 shrink-0">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-white">Pipeline Dashboard</h1>
          <div className="text-slate-400 text-xs mt-1">Real-time job queue, quality review approvals, and local cache monitoring.</div>
        </div>
      </div>

      <div className="grid grid-cols-[repeat(auto-fit,minmax(250px,1fr))] gap-4 mb-6">
        <div className="glass-panel flex justify-between items-center p-4 bg-slate-900 border border-slate-800">
          <div>
            <div className="text-blue-400 text-xs font-medium mb-1">Active Jobs in Queue</div>
            <b className="text-2xl text-white">{activeJobs.length}</b>
          </div>
          <Button variant="primary" onClick={() => navigate('/pipeline')}>View Pipeline</Button>
        </div>
        
        <div className="glass-panel flex justify-between items-center p-4 bg-slate-900 border border-slate-800">
          <div>
            <div className="text-amber-400 text-xs font-medium mb-1">Quality Review Approvals</div>
            <b className="text-2xl text-amber-400">{qcJobs.length}</b>
          </div>
          <Button 
            variant="secondary"
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
            <div 
              key={job.id} 
              className="glass-panel p-3 flex justify-between items-center cursor-pointer hover:bg-[var(--gl2)] transition-colors" 
              onClick={() => navigate(`/qc1/${job.id}`)}
            >
              <div>
                <b className="font-medium text-[14px]">{job.niche}</b>
                <div className="text-[12px] text-[var(--mu)]">Finished {new Date(job.updated_at || Date.now()).toLocaleDateString()}</div>
              </div>
              <div className="flex items-center gap-2">
                <Button 
                  variant="ghost" 
                  className="text-xs py-1 h-auto"
                  onClick={(e) => {
                    e.stopPropagation();
                    navigate(`/qc1/${job.id}`);
                  }}
                >
                  Open in Studio
                </Button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    if (confirm(`Delete video #${job.id} (${job.niche})?`)) {
                      deleteJobMutation.mutate(job.id);
                    }
                  }}
                  className="p-1.5 rounded hover:bg-red-500/20 text-slate-400 hover:text-red-400 transition-colors"
                  title="Delete Job"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
