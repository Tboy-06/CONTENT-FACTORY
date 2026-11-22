import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Trash2,
  Plus,
  Download,
  ExternalLink,
  Activity,
  CheckCircle2,
  Clock
} from 'lucide-react';
import { useJobs, useDeleteJob, useClearAllJobs } from '../api/client';
import { Tabs, Badge, Button } from '../components/ui';

export default function Pipeline() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('Board');
  const { data: jobs = [], isLoading, isError } = useJobs();
  const deleteJobMutation = useDeleteJob();
  const clearAllMutation = useClearAllJobs();

  const columns = [
    { id: 'queued', title: 'Queued', stages: ['IDEA', 'QUEUED'] },
    { id: 'researching', title: 'Researching', stages: ['RESEARCH'] },
    { id: 'writing', title: 'Scripting', stages: ['SCRIPT'] },
    { id: 'production', title: 'Rendering & Beats', stages: ['AUDIO', 'PLATES', 'ART', 'FFMPEG', 'VIDEO'] },
    { id: 'qc1', title: 'QC1 Review', stages: ['QC1', 'AWAITING_APPROVAL'] },
    { id: 'completed', title: 'Completed & Ready', stages: ['QC2', 'READY_TO_PUBLISH', 'PUBLISHED', 'COMPLETED'] }
  ];

  const getEngineBadge = (job: any) => {
    if (job.config?.premium) return <Badge variant="info">Premium</Badge>;
    return <Badge variant="success">Free</Badge>;
  };

  const getJobProgress = (job: any) => {
    const stageIdx = columns.findIndex((c) => c.stages.includes(job.current_stage));
    if (stageIdx === -1) return 12;
    return Math.max(12, ((stageIdx + 1) / columns.length) * 100);
  };

  const activeCount = jobs.filter(
    (j: any) =>
      ['IDEA', 'QUEUED', 'RESEARCH', 'SCRIPT', 'AUDIO', 'PLATES', 'ART', 'FFMPEG', 'VIDEO'].includes(
        j.current_stage
      ) && j.status !== 'FAILED'
  ).length;

  const qcCount = jobs.filter(
    (j: any) => j.current_stage === 'QC1' || j.status === 'AWAITING_APPROVAL'
  ).length;

  const completedCount = jobs.filter(
    (j: any) =>
      ['QC2', 'READY_TO_PUBLISH', 'PUBLISHED', 'COMPLETED'].includes(j.current_stage) ||
      j.status === 'COMPLETED' ||
      j.status === 'PUBLISHED'
  ).length;

  return (
    <div className="animate-in fade-in min-h-full flex flex-col pb-8 space-y-5">
      {/* Top Header */}
      <div className="flex justify-between items-center flex-wrap gap-3 shrink-0">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-[var(--tx)]">Production Pipeline</h1>
          <div className="text-[var(--mu)] text-xs mt-0.5">
            Real-time Kanban stage tracking and publish-pack exports across all rendering jobs.
          </div>
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
              className="hover:!text-red-500"
            >
              <Trash2 size={13} />
              <span>Clear All</span>
            </Button>
          )}

          <Button variant="primary" onClick={() => navigate('/create')}>
            <Plus size={14} />
            <span>New Video</span>
          </Button>
        </div>
      </div>

      {/* Unified 3-Zone Pipeline KPI Strip */}
      <div className="glass-panel p-4 grid grid-cols-1 sm:grid-cols-3 gap-4 sm:gap-0 sm:divide-x divide-[var(--ln-subtle)]">
        <div className="sm:pr-5 flex items-center justify-between">
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-wider text-[var(--mu)]">
              Active & Queued
            </div>
            <div className="text-2xl font-bold text-[var(--tx)] font-mono mt-1">{activeCount}</div>
            <div className="text-[11px] text-[var(--mu)]">Script, audio & FFmpeg workers</div>
          </div>
          <div className="w-9 h-9 rounded-xl bg-blue-600/15 border border-blue-500/30 text-blue-600 dark:text-blue-400 flex items-center justify-center">
            <Activity size={17} />
          </div>
        </div>

        <div className="sm:px-5 flex items-center justify-between">
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-wider text-[var(--mu)]">
              Awaiting QC1 Review
            </div>
            <div className="text-2xl font-bold text-amber-600 dark:text-amber-400 font-mono mt-1">
              {qcCount}
            </div>
            <div className="text-[11px] text-[var(--mu)]">Ready for director inspection</div>
          </div>
          <div className="w-9 h-9 rounded-xl bg-amber-500/15 border border-amber-500/30 text-amber-600 dark:text-amber-400 flex items-center justify-center">
            <Clock size={17} />
          </div>
        </div>

        <div className="sm:pl-5 flex items-center justify-between">
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-wider text-[var(--mu)]">
              Completed & Exportable
            </div>
            <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400 font-mono mt-1">
              {completedCount}
            </div>
            <div className="text-[11px] text-[var(--mu)]">Out of {jobs.length} total jobs tracked</div>
          </div>
          <div className="w-9 h-9 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-600 dark:text-emerald-400 flex items-center justify-center">
            <CheckCircle2 size={17} />
          </div>
        </div>
      </div>

      <div className="-mb-2">
        <Tabs tabs={['Board', 'History']} activeTab={activeTab} onChange={setActiveTab} />
      </div>

      {isError && (
        <div className="p-3.5 bg-red-500/12 border border-red-500/40 text-red-700 dark:text-red-300 text-xs rounded-xl font-medium">
          Failed to connect to backend server. Make sure port 8000 is running.
        </div>
      )}

      {activeTab === 'Board' && (
        <div className="flex-1 overflow-x-auto overflow-y-auto pb-2">
          <div className="flex gap-3.5 h-full min-w-max">
            {columns.map((col) => {
              const colJobs = jobs.filter((j: any) => col.stages.includes(j.current_stage));
              const isQC1 = col.id === 'qc1';
              const isCompleted = col.id === 'completed';

              return (
                <div
                  key={col.id}
                  className={`w-[248px] flex flex-col glass-panel p-3 ${
                    isQC1
                      ? '!border-amber-500/45 shadow-md shadow-amber-500/10'
                      : isCompleted
                      ? '!border-emerald-500/35'
                      : ''
                  }`}
                >
                  <h3
                    className={`text-xs font-bold flex justify-between items-center mb-3 px-1 ${
                      isQC1
                        ? 'text-amber-600 dark:text-amber-400'
                        : isCompleted
                        ? 'text-emerald-600 dark:text-emerald-400'
                        : 'text-[var(--tx)]'
                    }`}
                  >
                    <span>{col.title}</span>
                    <span className="font-mono text-[10px] px-2 py-0.5 rounded-lg bg-[var(--gl2)] border border-[var(--ln-subtle)] text-[var(--mu)]">
                      {colJobs.length}
                    </span>
                  </h3>

                  <div className="flex-1 overflow-y-auto flex flex-col gap-2.5 pr-0.5 pb-2">
                    {colJobs.length === 0 ? (
                      <div className="p-4 rounded-xl border border-dashed border-[var(--ln-subtle)] text-center text-[11px] text-[var(--mu)]">
                        No jobs in {col.title.toLowerCase()}
                      </div>
                    ) : (
                      colJobs.map((job: any) => {
                        const videoAsset = job.assets?.find(
                          (a: any) => a.type === 'VIDEO' || a.type === 'video'
                        );
                        const hasVideo = !!videoAsset;

                        return (
                          <div
                            key={job.id}
                            className={`glass-subcard p-3 transition-all hover:-translate-y-0.5 cursor-pointer relative group ${
                              isQC1 ? 'border-amber-500/45' : ''
                            }`}
                            onClick={() => navigate(`/qc1/${job.id}`)}
                          >
                            <div className="flex items-center justify-between mb-1.5">
                              <span className="text-[10px] text-[var(--mu)] font-mono font-semibold">
                                Job #{job.id}
                              </span>
                              <div className="flex items-center gap-1">
                                {getEngineBadge(job)}
                                {hasVideo && (
                                  <a
                                    href={`/api/jobs/${job.id}/export`}
                                    onClick={(e) => e.stopPropagation()}
                                    className="p-1 text-[var(--mu)] hover:text-blue-600 dark:hover:text-blue-400 rounded-md hover:bg-blue-500/10"
                                    title="Download Publish-Ready .ZIP Pack"
                                  >
                                    <Download size={12} />
                                  </a>
                                )}
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    deleteJobMutation.mutate(job.id);
                                  }}
                                  className="opacity-0 group-hover:opacity-100 p-1 text-[var(--mu)] hover:text-red-500 transition-opacity cursor-pointer"
                                  title="Delete job"
                                >
                                  <Trash2 size={12} />
                                </button>
                              </div>
                            </div>

                            <b className="font-semibold text-[13px] text-[var(--tx)] line-clamp-2 block mb-1.5 leading-snug">
                              {job.niche}
                            </b>

                            <p className="text-[11px] text-[var(--mu)] flex items-center justify-between">
                              <span>
                                {job.config?.voice
                                  ? String(job.config.voice).split('-')[2]?.replace('Neural', '')
                                  : 'Aria'}
                              </span>
                              <span className="font-mono text-[10px] font-semibold">
                                {job.config?.format || '9:16'}
                              </span>
                            </p>

                            {isQC1 ? (
                              <div className="mt-2.5 flex items-center justify-between">
                                <Badge variant="warning">Review QC1</Badge>
                                <span className="text-[10px] font-semibold text-blue-600 dark:text-blue-400">
                                  Inspect &rarr;
                                </span>
                              </div>
                            ) : (
                              <div className="h-1.5 bg-[var(--ln-subtle)] rounded-md overflow-hidden mt-2.5">
                                <div
                                  className={`h-full transition-all ${
                                    isCompleted ? 'bg-emerald-500' : 'bg-blue-600'
                                  }`}
                                  style={{ width: `${getJobProgress(job)}%` }}
                                />
                              </div>
                            )}
                          </div>
                        );
                      })
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {activeTab === 'History' && (
        <div className="flex-1 overflow-auto glass-panel !p-0">
          <table className="w-full text-[13px] border-collapse">
            <thead className="bg-[var(--table-head)] sticky top-0 backdrop-blur-md">
              <tr>
                <th className="p-3 text-left text-[var(--mu)] font-semibold text-[11px] uppercase tracking-wider border-b border-[var(--ln-subtle)]">
                  Job / Topic
                </th>
                <th className="p-3 text-left text-[var(--mu)] font-semibold text-[11px] uppercase tracking-wider border-b border-[var(--ln-subtle)]">
                  Stage
                </th>
                <th className="p-3 text-left text-[var(--mu)] font-semibold text-[11px] uppercase tracking-wider border-b border-[var(--ln-subtle)]">
                  Format
                </th>
                <th className="p-3 text-right text-[var(--mu)] font-semibold text-[11px] uppercase tracking-wider border-b border-[var(--ln-subtle)]">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((job: any) => {
                const isFailed = job.status === 'FAILED';
                const isDone =
                  job.status === 'COMPLETED' ||
                  job.status === 'PUBLISHED' ||
                  job.current_stage === 'READY_TO_PUBLISH';
                const isQC = job.current_stage === 'QC1';
                const hasVideo = job.assets?.some((a: any) => a.type === 'VIDEO' || a.type === 'video');

                return (
                  <tr
                    key={job.id}
                    onClick={() => navigate(`/qc1/${job.id}`)}
                    className="border-b border-[var(--ln-subtle)] hover:bg-[var(--row-hover)] cursor-pointer transition-colors"
                  >
                    <td className="p-3">
                      <div className="font-semibold text-[var(--tx)]">{job.niche}</div>
                      <div className="text-[11px] font-mono text-[var(--mu)]">Job #{job.id}</div>
                    </td>
                    <td className="p-3">
                      {isFailed ? (
                        <Badge variant="danger">Failed</Badge>
                      ) : isDone ? (
                        <Badge variant="success">{job.current_stage || 'Completed'}</Badge>
                      ) : isQC ? (
                        <Badge variant="warning">QC1 Review</Badge>
                      ) : (
                        <Badge variant="info">{job.current_stage || 'Running'}</Badge>
                      )}
                    </td>
                    <td className="p-3 text-[var(--mu)] font-mono text-xs">
                      {job.config?.format || '9:16'}
                    </td>
                    <td className="p-3">
                      <div className="flex items-center justify-end gap-1.5">
                        {hasVideo && (
                          <a
                            href={`/api/jobs/${job.id}/export`}
                            onClick={(e) => e.stopPropagation()}
                            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-[var(--gl2)] border border-[var(--input-border)] text-[var(--tx)] hover:border-blue-500 text-[11px] font-semibold transition-colors"
                            title="Download Publish-Ready .ZIP Pack"
                          >
                            <Download size={12} className="text-blue-600 dark:text-blue-400" />
                            <span>.ZIP</span>
                          </a>
                        )}
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            navigate(`/qc1/${job.id}`);
                          }}
                          className="p-1.5 rounded-lg text-[var(--mu)] hover:text-blue-600 dark:hover:text-blue-400 hover:bg-blue-500/10 cursor-pointer"
                          title="Open QC1 Inspector"
                        >
                          <ExternalLink size={14} />
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            deleteJobMutation.mutate(job.id);
                          }}
                          className="p-1.5 rounded-lg text-[var(--mu)] hover:text-red-500 hover:bg-red-500/10 cursor-pointer"
                          title="Delete job"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
              {jobs.length === 0 && !isLoading && (
                <tr>
                  <td colSpan={4} className="p-8 text-center text-[var(--mu)] text-xs">
                    No jobs in history yet. Create your first documentary to populate the pipeline.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
