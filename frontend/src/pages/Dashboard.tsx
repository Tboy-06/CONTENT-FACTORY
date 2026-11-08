import { useNavigate } from 'react-router-dom';
import { useJobs, useSpend } from '../api/client';
import { Button } from '../components/ui';

export default function Dashboard() {
  const navigate = useNavigate();
  const { data: jobs = [] } = useJobs();
  const { data: spend } = useSpend();

  const activeJobs = jobs.filter((j: any) => j.status === 'RUNNING' || j.status === 'PENDING' || j.status === 'QUEUED');
  const qcJobs = jobs.filter((j: any) => j.status === 'AWAITING_APPROVAL' || j.current_stage === 'QC1');
  const recentJobs = jobs.filter((j: any) => j.status === 'COMPLETED' || j.status === 'PUBLISHED').slice(0, 3);

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
        
        <div className="glass-panel flex justify-between items-center p-5">
          <div>
            <div className="text-[var(--mu)] text-[13px] font-medium mb-1">Spend this month</div>
            <b className="text-3xl">${spend != null ? spend.toFixed(2) : '0.00'}</b>
          </div>
          <div className="text-[var(--mu)] text-[13px] bg-[var(--gl2)] px-2.5 py-1 rounded-lg">of $50 cap</div>
        </div>
        
        <div className="glass-panel flex justify-between items-center p-5">
          <div>
            <div className="text-[var(--mu)] text-[13px] font-medium mb-1">Storage</div>
            <b className="text-3xl">12 GB</b>
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
