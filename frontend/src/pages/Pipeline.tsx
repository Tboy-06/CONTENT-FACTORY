import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Trash2, Plus, Film, Clock } from 'lucide-react';
import { useJobs, useDeleteJob, useClearAllJobs } from '../api/client';
import { Tabs, Badge, Button } from '../components/ui';

export default function Pipeline() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('Board');
  const { data: jobs = [], isLoading, isError } = useJobs();
  const deleteJobMutation = useDeleteJob();
  const clearAllMutation = useClearAllJobs();

  // Columns capturing all real backend stages
  const columns = [
    { id: 'queued', title: 'Queued', stages: ['IDEA', 'QUEUED'] },
    { id: 'researching', title: 'Researching', stages: ['RESEARCH'] },
    { id: 'writing', title: 'Scripting', stages: ['SCRIPT'] },
    { id: 'production', title: 'Rendering & Beats', stages: ['AUDIO', 'PLATES', 'ART', 'FFMPEG', 'VIDEO'] },
    { id: 'qc1', title: 'QC1 Review', stages: ['QC1'] },
    { id: 'completed', title: 'Completed', stages: ['QC2', 'PUBLISHED', 'COMPLETED'] }
  ];

  const getEngineBadge = (job: any) => {
    if (job.config?.premium) return <Badge variant="info">Premium</Badge>;
    return <Badge variant="success">Free</Badge>;
  };

  const getJobProgress = (job: any) => {
    const stageIdx = columns.findIndex(c => c.stages.includes(job.current_stage));
    if (stageIdx === -1) return 10;
    return Math.max(10, ((stageIdx + 1) / columns.length) * 100);
  };

  return (
    <div className="animate-in fade-in min-h-full flex flex-col pb-8">
      {/* Top Header */}
      <div className="flex justify-between items-center flex-wrap gap-3 mb-4 shrink-0">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight text-white">Production Pipeline</h1>
          <div className="text-[var(--mu)] text-[13px]">Real-time stage tracking across all rendering and queued jobs.</div>
        </div>

        <div className="flex items-center gap-2">
          {jobs.length > 0 && (
            <Button
              variant="secondary"
              onClick={() => {
                if (confirm('Clear all job history?')) {
                  clearAllMutation.mutate();
                }
              }}
              disabled={clearAllMutation.isPending}
              className="flex items-center gap-1.5 text-xs !py-1.5 !px-3 border-slate-700 text-slate-300 hover:text-red-400"
            >
              <Trash2 size={13} />
              <span>Clear All</span>
            </Button>
          )}

          <Button 
            variant="primary" 
            onClick={() => navigate('/create')}
            className="flex items-center gap-1.5 text-xs !py-1.5 !px-3"
          >
            <Plus size={14} />
            <span>New Video</span>
          </Button>
        </div>
      </div>

      <Tabs tabs={['Board', 'History']} activeTab={activeTab} onChange={setActiveTab} />

      {isError && (
        <div className="p-3 bg-red-950/60 border border-red-500/40 text-red-300 text-xs rounded-xl mb-3">
          Failed to connect to backend server. Make sure port 8000 is running.
        </div>
      )}

      {activeTab === 'Board' && (
        <div className="flex-1 overflow-x-auto overflow-y-auto pb-2">
          <div className="flex gap-3 h-full min-w-max">
            {columns.map(col => {
              const colJobs = jobs.filter((j: any) => col.stages.includes(j.current_stage));
              const isQC1 = col.id === 'qc1';
              
              return (
                <div key={col.id} className={`w-[230px] flex flex-col ${isQC1 ? 'bg-[rgba(245,184,74,0.06)] border border-[rgba(245,184,74,0.4)] rounded-xl p-2' : ''}`}>
                  <h3 className={`text-xs font-semibold flex justify-between items-center mb-2 mx-1 ${isQC1 ? 'text-[var(--wa)]' : 'text-[var(--mu)]'}`}>
                    <span>{col.title}</span>
                    <span className="font-mono text-[10px] px-1.5 py-0.2 rounded bg-slate-800 text-slate-400">{colJobs.length}</span>
                  </h3>
                  
                  <div className="flex-1 overflow-y-auto flex flex-col gap-2.5 pr-1 pb-4">
                    {colJobs.map((job: any) => {
                      const videoAsset = job.assets?.find((a: any) => a.type === 'VIDEO' || a.type === 'video');
                      const hasVideo = !!videoAsset;
                      
                      return (
                        <div 
                          key={job.id} 
                          className={`glass-panel p-2.5 transition-all hover:-translate-y-0.5 cursor-pointer relative group ${isQC1 ? 'border-[rgba(245,184,74,0.55)] shadow-[0_0_24px_rgba(245,184,74,0.12)]' : 'hover:border-blue-500/50'}`}
                          onClick={() => navigate(`/qc1/${job.id}`)}
                        >
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-[10px] text-slate-400 font-mono">Job #{job.id}</span>
                            <div className="flex items-center gap-1">
                              {getEngineBadge(job)}
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  deleteJobMutation.mutate(job.id);
                                }}
                                className="opacity-0 group-hover:opacity-100 p-0.5 text-slate-500 hover:text-red-400 transition-opacity"
                                title="Delete job"
                              >
                                <Trash2 size={12} />
                              </button>
                            </div>
                          </div>

                          <b className="font-medium text-[13px] text-white line-clamp-1 block mb-1">{job.niche}</b>

                          <p className="text-[11px] text-[var(--mu)] flex items-center justify-between">
                            <span>{job.config?.voice ? String(job.config.voice).split('-')[2] : 'Aria'}</span>
                            <span className="font-mono text-[10px] text-slate-400">{job.config?.format || '9:16'}</span>
                          </p>

                          {isQC1 ? (
                            <div className="mt-2 text-center">
                              <Badge variant="warning">QC1 Review</Badge>
                            </div>
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
        <div className="flex-1 overflow-auto glass-panel p-0 rounded-xl">
          <table className="w-full text-[13px] border-collapse">
            <thead className="bg-[rgba(11,14,23,0.8)] sticky top-0">
              <tr>
                <th className="p-[10px_12px] text-left text-[var(--mu)] font-normal text-xs border-b border-[var(--ln)]">Job</th>
                <th className="p-[10px_12px] text-left text-[var(--mu)] font-normal text-xs border-b border-[var(--ln)]">Stage</th>
                <th className="p-[10px_12px] text-left text-[var(--mu)] font-normal text-xs border-b border-[var(--ln)]">Format</th>
                <th className="p-[10px_12px] text-left text-[var(--mu)] font-normal text-xs border-b border-[var(--ln)]">Actions</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((job: any) => {
                const isError = job.status === 'FAILED';
                const isDone = job.status === 'COMPLETED';
                const isQC = job.current_stage === 'QC1';
                return (
                  <tr 
                    key={job.id} 
                    onClick={() => navigate(`/qc1/${job.id}`)}
                    className="border-b border-[var(--ln)] hover:bg-[var(--gl2)] cursor-pointer"
                  >
                    <td className="p-[10px_12px] font-medium text-white">{job.niche}</td>
                    <td className="p-[10px_12px]">
                      {isError ? <Badge variant="danger">Failed</Badge> : 
                       isDone ? <Badge variant="success">Completed</Badge> : 
                       isQC ? <Badge variant="warning">QC1 Review</Badge> : 
                       <Badge variant="info">{job.current_stage || 'Running'}</Badge>}
                    </td>
                    <td className="p-[10px_12px] text-[var(--mu)] font-mono text-xs">{job.config?.format || '9:16'}</td>
                    <td className="p-[10px_12px]">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          deleteJobMutation.mutate(job.id);
                        }}
                        className="text-slate-500 hover:text-red-400 p-1"
                        title="Delete job"
                      >
                        <Trash2 size={14} />
                      </button>
                    </td>
                  </tr>
                );
              })}
              {jobs.length === 0 && !isLoading && (
                <tr>
                  <td colSpan={4} className="p-8 text-center text-[var(--mu)]">No jobs in history yet.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
