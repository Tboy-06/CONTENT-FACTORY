import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useJobs } from '../api/client';
import { Thumbnail } from '../components/Thumbnails';
import { Tabs, Badge } from '../components/ui';

export default function Pipeline() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('Board');
  const { data: jobs = [], isLoading, isError } = useJobs();

  // Columns for the board
  const columns = [
    { id: 'queued', title: 'Queued', stages: ['IDEA', 'QUEUED'] },
    { id: 'researching', title: 'Researching', stages: ['RESEARCH'] },
    { id: 'writing', title: 'Writing', stages: ['SCRIPT'] },
    { id: 'storyboard', title: 'Storyboard', stages: ['STORYBOARD', 'VISUALS'] },
    { id: 'qc1', title: 'QC1 approval', stages: ['QC1'] }
  ];

  // Engine badge mapping
  const getEngineBadge = (job: any) => {
    if (job.config?.premium) return <Badge variant="info">Premium</Badge>;
    return <Badge variant="success">Free</Badge>;
  };

  const getJobProgress = (job: any) => {
    const stageIdx = columns.findIndex(c => c.stages.includes(job.current_stage));
    if (stageIdx === -1) return 0;
    return Math.max(5, ((stageIdx + 1) / columns.length) * 100);
  };

  return (
    <div className="animate-in fade-in min-h-full flex flex-col pb-8">
      <div className="flex justify-between items-center flex-wrap gap-3 mb-4 shrink-0">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight">Pipeline</h1>
          <div className="text-[var(--mu)] text-[13px]">Every job, live.</div>
        </div>
        <button className="btn" onClick={() => navigate('/create')}>New job</button>
      </div>

      <Tabs tabs={['Board', 'History']} activeTab={activeTab} onChange={setActiveTab} />

      {isError && (
        <div className="p-4 bg-[rgba(255,107,122,0.1)] border border-[rgba(255,107,122,0.4)] text-[var(--er)] rounded-xl text-sm mb-4">
          Cannot connect to backend. Please check your connection.
        </div>
      )}

      {activeTab === 'Board' && (
        <div className="flex-1 overflow-x-auto overflow-y-hidden pb-2">
          <div className="flex gap-3 h-full min-w-max">
            {columns.map(col => {
              const colJobs = jobs.filter((j: any) => col.stages.includes(j.current_stage));
              const isQC1 = col.id === 'qc1';
              
              return (
                <div key={col.id} className={`w-[210px] flex flex-col ${isQC1 ? 'bg-[rgba(245,184,74,0.06)] border border-[rgba(245,184,74,0.4)] rounded-xl p-2' : ''}`}>
                  <h3 className={`text-xs font-medium flex justify-between mb-2 mx-1 ${isQC1 ? 'text-[var(--wa)]' : 'text-[var(--mu)]'}`}>
                    {col.title}
                    <span>{colJobs.length}</span>
                  </h3>
                  
                  <div className="flex-1 overflow-y-auto flex flex-col gap-2.5 pr-1 pb-4">
                    {colJobs.map((job: any) => {
                      const thumbAsset = job.assets?.find((a: any) => a.type === 'IMAGE' || a.type === 'VIDEO') || job.assets?.[0];
                      const bgUrl = thumbAsset?.path ? `url(${thumbAsset.path})` : "url('https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?ixlib=rb-4.0.3&auto=format&fit=crop&w=400&q=80')";
                      
                      return (
                        <div 
                          key={job.id} 
                          className={`glass-panel p-2 transition-transform hover:-translate-y-0.5 cursor-pointer ${isQC1 ? 'border-[rgba(245,184,74,0.55)] shadow-[0_0_28px_rgba(245,184,74,0.14)]' : ''}`}
                          onClick={() => isQC1 && navigate(`/qc1/${job.id}`)}
                        >
                          <div className="h-[74px] mb-1.5 rounded-lg bg-cover bg-center" style={{backgroundImage: bgUrl}} />
                          <b className="font-medium text-[13px] line-clamp-1">{job.niche}</b>
                          <p className="text-[11px] text-[var(--mu)] flex items-center justify-between mt-1">
                            {job.config?.duration || '60s'} · {job.config?.format || '9:16'}
                            {getEngineBadge(job)}
                          </p>
                          {isQC1 ? (
                            <div className="mt-2 text-center"><Badge variant="warning">QC1 review</Badge></div>
                          ) : (
                            <div className="h-1 bg-[var(--gl2)] rounded-full overflow-hidden mt-2">
                              <div className="h-full bg-gradient-to-r from-[var(--ac)] to-[var(--ac2)]" style={{ width: `${getJobProgress(job)}%` }} />
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {activeTab === 'History' && (
        <div className="flex-1 overflow-auto glass-panel p-0">
          <table className="w-full text-[13px] border-collapse">
            <thead className="bg-[rgba(11,14,23,0.5)] sticky top-0">
              <tr>
                <th className="p-[10px_12px] text-left text-[var(--mu)] font-normal text-xs border-b border-[var(--ln)]">Job</th>
                <th className="p-[10px_12px] text-left text-[var(--mu)] font-normal text-xs border-b border-[var(--ln)]">State</th>
                <th className="p-[10px_12px] text-left text-[var(--mu)] font-normal text-xs border-b border-[var(--ln)]">Duration</th>
                <th className="p-[10px_12px] text-left text-[var(--mu)] font-normal text-xs border-b border-[var(--ln)]">Cost</th>
                <th className="p-[10px_12px] text-left text-[var(--mu)] font-normal text-xs border-b border-[var(--ln)]">Engine</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((job: any) => {
                const isError = job.status === 'FAILED';
                const isDone = job.status === 'COMPLETED';
                const isQC = job.status === 'AWAITING_APPROVAL';
                return (
                  <tr key={job.id} className="border-b border-[var(--ln)] hover:bg-[var(--gl2)] cursor-pointer">
                    <td className="p-[10px_12px] font-medium">{job.niche}</td>
                    <td className="p-[10px_12px]">
                      {isError ? <Badge variant="danger">Failed</Badge> : 
                       isDone ? <Badge variant="success">Completed</Badge> : 
                       isQC ? <Badge variant="warning">QC1</Badge> : 
                       <Badge variant="info">Running</Badge>}
                    </td>
                    <td className="p-[10px_12px] text-[var(--mu)]">-</td>
                    <td className="p-[10px_12px] font-medium">
                      ${job.costs?.reduce((acc: number, c: any) => acc + (c.usd_estimate || 0), 0).toFixed(2) || '0.00'}
                    </td>
                    <td className="p-[10px_12px]">{getEngineBadge(job)}</td>
                  </tr>
                );
              })}
              {jobs.length === 0 && !isLoading && (
                <tr>
                  <td colSpan={5} className="p-8 text-center text-[var(--mu)]">No jobs in history yet.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
