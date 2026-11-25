import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Trash2,
  Plus,
  Download,
  ExternalLink,
  Activity,
  CheckCircle2,
  Clock,
  Film,
  Search,
  X,
  HardDrive,
  Package,
  Play,
  Cpu,
  ShieldCheck,
  RefreshCw,
  ArrowRight
} from 'lucide-react';
import { useJobs, useDeleteJob, useClearAllJobs, useCacheStatus, useClearCache } from '../api/client';
import { Tabs, Badge, Button, ConfirmDialog, Progress, EmptyState } from '../components/ui';

const STAGE_LANES = [
  {
    id: 'active',
    title: 'Active Workers',
    subtitle: 'Intake, script, voice & FFmpeg',
    stages: ['IDEA', 'QUEUED', 'RESEARCH', 'SCRIPT', 'AUDIO', 'PLATES', 'ART', 'FFMPEG', 'VIDEO'],
    accent: 'var(--ac)'
  },
  {
    id: 'qc1',
    title: 'QC1 Director Review',
    subtitle: 'Ready for storyboard inspection',
    stages: ['QC1', 'AWAITING_APPROVAL'],
    accent: 'var(--wa)'
  },
  {
    id: 'completed',
    title: 'Mastered & Ready',
    subtitle: 'Exportable MP4 + .ZIP bundles',
    stages: ['QC2', 'READY_TO_PUBLISH', 'PUBLISHED', 'COMPLETED'],
    accent: 'var(--ok)'
  }
];

function formatVoiceShort(v?: string) {
  if (!v) return 'Andrew';
  if (v === 'am_michael' || v.includes('kokoro')) return 'Kokoro Michael';
  const seg = String(v).split('-')[2];
  return seg ? seg.replace('MultilingualNeural', '').replace('Neural', '') : v;
}

function getJobProgress(job: any) {
  const st = String(job?.current_stage || '').toUpperCase();
  if (['READY_TO_PUBLISH', 'PUBLISHED', 'COMPLETED', 'QC2'].includes(st) || job?.status === 'COMPLETED') {
    return 100;
  }
  if (st === 'QC1' || job?.status === 'AWAITING_APPROVAL') return 88;
  if (['FFMPEG', 'VIDEO'].includes(st)) return 72;
  if (['PLATES', 'ART'].includes(st)) return 52;
  if (st === 'AUDIO') return 35;
  if (st === 'SCRIPT') return 20;
  return 12;
}

function resolveVideoUrl(job: any): string | null {
  const videoAsset = job?.assets?.find((a: any) => a.type === 'VIDEO' || a.type === 'video');
  const meta = videoAsset?.metadata || {};
  if (meta.video_url) return meta.video_url;
  if (videoAsset?.path) return `/output/${String(videoAsset.path).split(/[\\/]/).pop()}`;
  return null;
}

export default function Pipeline() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('Stage Board');
  const [stageFilter, setStageFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedJobId, setSelectedJobId] = useState<number | null>(null);
  const [isConfirmClearOpen, setIsConfirmClearOpen] = useState(false);
  const [jobPendingDelete, setJobPendingDelete] = useState<any | null>(null);

  const { data: jobs = [], isLoading, isError, refetch } = useJobs();
  const { data: cache } = useCacheStatus();
  const clearCacheMutation = useClearCache();
  const deleteJobMutation = useDeleteJob();
  const clearAllMutation = useClearAllJobs();

  const laneBuckets = useMemo(() => {
    const active = jobs.filter(
      (j: any) =>
        STAGE_LANES[0].stages.includes(j.current_stage) &&
        j.status !== 'FAILED' &&
        j.status !== 'COMPLETED'
    );
    const qc1 = jobs.filter(
      (j: any) => j.current_stage === 'QC1' || j.status === 'AWAITING_APPROVAL'
    );
    const completed = jobs.filter(
      (j: any) =>
        STAGE_LANES[2].stages.includes(j.current_stage) ||
        j.status === 'COMPLETED' ||
        j.status === 'PUBLISHED'
    );
    const failed = jobs.filter((j: any) => j.status === 'FAILED');
    return { active, qc1, completed, failed };
  }, [jobs]);

  const filteredJobs = useMemo(() => {
    return jobs.filter((j: any) => {
      const q = searchQuery.trim().toLowerCase();
      if (
        q &&
        !String(j.niche || '').toLowerCase().includes(q) &&
        !String(j.id).includes(q) &&
        !String(j.current_stage || '').toLowerCase().includes(q)
      ) {
        return false;
      }
      if (stageFilter === 'active') return laneBuckets.active.some((x: any) => x.id === j.id);
      if (stageFilter === 'qc1') return laneBuckets.qc1.some((x: any) => x.id === j.id);
      if (stageFilter === 'completed') return laneBuckets.completed.some((x: any) => x.id === j.id);
      if (stageFilter === 'failed') return j.status === 'FAILED';
      return true;
    });
  }, [jobs, searchQuery, stageFilter, laneBuckets]);

  const inspectedJob = useMemo(() => {
    if (selectedJobId !== null) {
      const found = jobs.find((j: any) => j.id === selectedJobId);
      if (found) return found;
    }
    return laneBuckets.active[0] || laneBuckets.qc1[0] || laneBuckets.completed[0] || jobs[0] || null;
  }, [jobs, selectedJobId, laneBuckets]);

  const inspectedVideoUrl = inspectedJob ? resolveVideoUrl(inspectedJob) : null;
  const tempMb = Number(cache?.temp_mb ?? 0);

  return (
    <div className="animate-in fade-in min-h-full flex flex-col pb-10 space-y-5">
      {/* Studio Command Header */}
      <div className="flex justify-between items-center flex-wrap gap-3 shrink-0">
        <div>
          <div className="flex items-center gap-2.5 flex-wrap">
            <h1 className="text-2xl font-bold tracking-tight text-[var(--tx)]">
              Render Pipeline &amp; Stage Telemetry
            </h1>
            <Badge variant="success">Single-Worker Thermal Guard</Badge>
          </div>
          <p className="text-[var(--mu)] text-xs mt-0.5">
            Track live assembly workers, preview rendered cuts inline, and export publish-ready `.ZIP` bundles.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button type="button" variant="secondary" onClick={() => refetch()} title="Refresh queue">
            <RefreshCw size={13} />
            <span>Refresh</span>
          </Button>

          {jobs.length > 0 && (
            <Button
              type="button"
              variant="secondary"
              onClick={() => setIsConfirmClearOpen(true)}
              disabled={clearAllMutation.isPending}
              className="hover:!text-red-500"
            >
              <Trash2 size={13} />
              <span>Clear Queue</span>
            </Button>
          )}

          <Button type="button" variant="primary" onClick={() => navigate('/create')}>
            <Plus size={14} />
            <span>New Production</span>
          </Button>
        </div>
      </div>

      {/* Interactive 4-Node Signal Flow Ribbon (Click to Filter Stages) */}
      <div className="glass-panel p-4 grid grid-cols-2 lg:grid-cols-4 gap-3">
        {[
          {
            id: 'all',
            step: '00',
            label: 'Total Tracked',
            count: jobs.length,
            sub: `${laneBuckets.failed.length} failed`,
            Icon: Film,
            tone: 'text-blue-600 dark:text-blue-400 bg-blue-600/15 border-blue-500/30'
          },
          {
            id: 'active',
            step: '01',
            label: 'Active Workers',
            count: laneBuckets.active.length,
            sub: 'Script, TTS & FFmpeg',
            Icon: Activity,
            tone: 'text-cyan-600 dark:text-cyan-400 bg-cyan-500/15 border-cyan-500/30'
          },
          {
            id: 'qc1',
            step: '02',
            label: 'Awaiting QC1',
            count: laneBuckets.qc1.length,
            sub: 'Director inspection',
            Icon: Clock,
            tone: 'text-amber-600 dark:text-amber-400 bg-amber-500/15 border-amber-500/30'
          },
          {
            id: 'completed',
            step: '03',
            label: 'Mastered & Ready',
            count: laneBuckets.completed.length,
            sub: 'MP4 + .ZIP exportable',
            Icon: CheckCircle2,
            tone: 'text-emerald-600 dark:text-emerald-400 bg-emerald-500/15 border-emerald-500/30'
          }
        ].map((node) => {
          const NodeIcon = node.Icon;
          const isSelected = stageFilter === node.id;
          return (
            <button
              key={node.id}
              type="button"
              onClick={() => setStageFilter(isSelected && node.id !== 'all' ? 'all' : node.id)}
              className={`p-3.5 rounded-xl border text-left transition-all cursor-pointer flex items-center justify-between gap-3 ${
                isSelected
                  ? 'bg-blue-600/12 border-blue-500 ring-1 ring-blue-500/35 shadow-xs'
                  : 'bg-[var(--gl2)] border-[var(--ln)] hover:border-blue-500/45'
              }`}
            >
              <div className="min-w-0">
                <div className="flex items-center gap-1.5">
                  <span className="font-mono text-[10px] font-bold text-[var(--mu)]">{node.step}</span>
                  <span className="text-[11px] font-bold uppercase tracking-wider text-[var(--mu)] truncate">
                    {node.label}
                  </span>
                </div>
                <div className="text-2xl font-extrabold font-mono text-[var(--tx)] mt-1 tabular-nums">
                  {node.count}
                </div>
                <div className="text-[11px] text-[var(--mu)] truncate">{node.sub}</div>
              </div>
              <div className={`w-10 h-10 rounded-xl border flex items-center justify-center shrink-0 ${node.tone}`}>
                <NodeIcon size={18} />
              </div>
            </button>
          );
        })}
      </div>

      {/* View Tabs + Search Filter Row */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="-mb-4">
          <Tabs
            tabs={['Stage Board', 'Cinema Showcase', 'Execution Table']}
            activeTab={activeTab}
            onChange={setActiveTab}
            ariaLabel="Pipeline view modes"
            counts={{
              'Stage Board': filteredJobs.length,
              'Cinema Showcase': filteredJobs.length,
              'Execution Table': filteredJobs.length
            }}
          />
        </div>

        <search aria-label="Search pipeline jobs" className="flex items-center gap-2">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-[var(--input-bg)] border border-[var(--input-border)] text-xs">
            <Search size={13} className="text-[var(--mu)] shrink-0" />
            <input
              type="search"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search topic, #id or stage..."
              className="w-44 bg-transparent outline-none text-[var(--tx)] placeholder:text-[var(--mu)]"
            />
            {(searchQuery || stageFilter !== 'all') && (
              <button
                type="button"
                onClick={() => {
                  setSearchQuery('');
                  setStageFilter('all');
                }}
                className="text-[var(--mu)] hover:text-red-500 cursor-pointer"
                title="Clear pipeline filter"
              >
                <X size={13} />
              </button>
            )}
          </div>
        </search>
      </div>

      {isError && (
        <div role="alert" className="p-3.5 bg-red-500/12 border border-red-500/40 text-red-700 dark:text-red-300 text-xs rounded-xl font-medium">
          Unable to reach backend API. Verify the FastAPI server is running.
        </div>
      )}

      {/* Main 2-Column Studio Workspace: 8/12 Active View + 4/12 Live Screening & Guardrail Rail */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-5 items-start">
        {/* LEFT MAIN WORKSPACE (8/12) */}
        <div className="xl:col-span-8 min-w-0">
          {/* VIEW 1: 3-LANE RESPONSIVE STAGE BOARD (Fits viewport without horizontal scrollbar) */}
          <div
            role="tabpanel"
            aria-label="Stage Board"
            hidden={activeTab !== 'Stage Board'}
          >
            {activeTab === 'Stage Board' && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {STAGE_LANES.map((lane) => {
                  const laneJobs = filteredJobs.filter((j: any) => {
                    if (lane.id === 'active') {
                      return (
                        lane.stages.includes(j.current_stage) &&
                        j.status !== 'FAILED' &&
                        j.status !== 'COMPLETED'
                      );
                    }
                    if (lane.id === 'qc1') {
                      return j.current_stage === 'QC1' || j.status === 'AWAITING_APPROVAL';
                    }
                    return (
                      lane.stages.includes(j.current_stage) ||
                      j.status === 'COMPLETED' ||
                      j.status === 'PUBLISHED'
                    );
                  });

                  return (
                    <div key={lane.id} className="glass-panel p-3.5 flex flex-col gap-3 min-w-0">
                      <div className="flex items-start justify-between gap-2 pb-2.5 border-b border-[var(--ln-subtle)]">
                        <div className="min-w-0">
                          <h2 className="text-xs font-bold uppercase tracking-wider text-[var(--tx)] truncate">
                            {lane.title}
                          </h2>
                          <p className="text-[11px] text-[var(--mu)] truncate">{lane.subtitle}</p>
                        </div>
                        <span className="font-mono text-xs font-bold px-2 py-0.5 rounded-lg bg-[var(--gl2)] border border-[var(--ln)] text-[var(--tx)] shrink-0">
                          {laneJobs.length}
                        </span>
                      </div>

                      <div className="scroll-panel-stable flex flex-col gap-2.5 max-h-[600px] pr-0.5">
                        {laneJobs.length === 0 ? (
                          <div className="p-5 rounded-xl border border-dashed border-[var(--ln-subtle)] text-center text-[11px] text-[var(--mu)]">
                            No jobs in {lane.title.toLowerCase()}
                          </div>
                        ) : (
                          laneJobs.map((job: any) => {
                            const isSelected = inspectedJob?.id === job.id;
                            const hasVideo = Boolean(resolveVideoUrl(job));
                            const progressVal = getJobProgress(job);
                            const thumbSrc = `/output/thumb_${job.id}_v1_16x9.jpg`;
                            const genre = String(job.config?.genre || 'crime_doc');

                            return (
                              <div
                                key={job.id}
                                onClick={() => setSelectedJobId(job.id)}
                                className={`glass-subcard overflow-hidden cursor-pointer transition-all group ${
                                  isSelected
                                    ? '!border-blue-500 ring-1 ring-blue-500/40 shadow-sm'
                                    : ''
                                }`}
                              >
                                {/* Thumbnail / Cover Header */}
                                <div className="relative h-24 iridescent-card-crime overflow-hidden flex items-center justify-center">
                                  <img
                                    src={thumbSrc}
                                    alt=""
                                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                                    onError={(e) => {
                                      (e.currentTarget as HTMLImageElement).style.display = 'none';
                                    }}
                                  />
                                  <span className="preserve-white absolute top-2 left-2 px-1.5 py-0.5 rounded-md bg-black/60 text-[10px] font-mono font-bold text-white border border-white/15">
                                    #{job.id} · {job.config?.format || '9:16'}
                                  </span>
                                  <span className="preserve-white absolute top-2 right-2 px-1.5 py-0.5 rounded-md bg-black/60 text-[10px] font-mono text-sky-200 uppercase">
                                    {genre.replace('_', ' ')}
                                  </span>
                                </div>

                                <div className="p-3 space-y-2">
                                  <div className="text-xs font-bold text-[var(--tx)] line-clamp-2 leading-snug">
                                    {job.niche}
                                  </div>

                                  <div className="flex items-center justify-between text-[10px] text-[var(--mu)] font-mono">
                                    <span>{formatVoiceShort(job.config?.voice)}</span>
                                    <span>{job.current_stage || job.status}</span>
                                  </div>

                                  <Progress
                                    value={progressVal}
                                    color={lane.accent}
                                    label={`Job ${job.id} render completion`}
                                  />

                                  <div className="flex items-center justify-between gap-1.5 pt-1">
                                    <button
                                      type="button"
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        navigate(`/qc1/${job.id}`);
                                      }}
                                      className="text-[11px] font-semibold text-blue-600 dark:text-blue-400 hover:underline inline-flex items-center gap-1 cursor-pointer"
                                    >
                                      <span>Open QC1</span>
                                      <ArrowRight size={11} />
                                    </button>

                                    <div className="flex items-center gap-1">
                                      {hasVideo && (
                                        <a
                                          href={`/api/jobs/${job.id}/export`}
                                          onClick={(e) => e.stopPropagation()}
                                          className="p-1 rounded-md text-[var(--mu)] hover:text-blue-600 dark:hover:text-blue-400 hover:bg-blue-500/10"
                                          title="Download Publish-Ready .ZIP Pack"
                                        >
                                          <Download size={12} />
                                        </a>
                                      )}
                                      <button
                                        type="button"
                                        onClick={(e) => {
                                          e.stopPropagation();
                                          setJobPendingDelete(job);
                                        }}
                                        className="p-1 rounded-md text-[var(--mu)] hover:text-red-500 hover:bg-red-500/10 cursor-pointer"
                                        title="Delete job"
                                      >
                                        <Trash2 size={12} />
                                      </button>
                                    </div>
                                  </div>
                                </div>
                              </div>
                            );
                          })
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* VIEW 2: CINEMA SHOWCASE CARDS */}
          <div
            role="tabpanel"
            aria-label="Cinema Showcase"
            hidden={activeTab !== 'Cinema Showcase'}
          >
            {activeTab === 'Cinema Showcase' && (
              filteredJobs.length === 0 ? (
                <EmptyState
                  title="No pipeline jobs match your current filter"
                  description="Clear the search filter or launch a fresh documentary from the Production Deck."
                />
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {filteredJobs.map((job: any, idx: number) => {
                    const hasVideo = Boolean(resolveVideoUrl(job));
                    const isSelected = inspectedJob?.id === job.id;
                    const bannerClass =
                      idx % 3 === 1
                        ? 'iridescent-card-edu'
                        : idx % 3 === 2
                        ? 'iridescent-card-cinema'
                        : 'iridescent-card-crime';

                    return (
                      <div
                        key={job.id}
                        onClick={() => setSelectedJobId(job.id)}
                        className={`glass-panel !p-0 overflow-hidden cursor-pointer transition-all hover:-translate-y-0.5 group ${
                          isSelected ? '!border-blue-500 ring-1 ring-blue-500/40' : ''
                        }`}
                      >
                        <div className={`relative h-36 ${bannerClass} flex items-center justify-center overflow-hidden`}>
                          <img
                            src={`/output/thumb_${job.id}_v1_16x9.jpg`}
                            alt=""
                            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                            onError={(e) => {
                              (e.currentTarget as HTMLImageElement).style.display = 'none';
                            }}
                          />
                          <span className="preserve-white absolute top-2.5 left-2.5 px-2 py-0.5 rounded-lg bg-black/60 text-[10px] font-mono font-bold text-white border border-white/20">
                            Job #{job.id} · {job.config?.format || '9:16'}
                          </span>
                          <span className="preserve-white absolute bottom-2.5 right-2.5 px-2 py-0.5 rounded-lg bg-black/65 text-[10px] font-semibold text-white flex items-center gap-1">
                            <Play size={10} />
                            <span>Click to Preview</span>
                          </span>
                        </div>

                        <div className="p-4 space-y-3">
                          <div>
                            <h3 className="text-sm font-bold text-[var(--tx)] line-clamp-1">
                              {job.niche}
                            </h3>
                            <p className="text-[11px] text-[var(--mu)] font-mono mt-0.5">
                              {formatVoiceShort(job.config?.voice)} · {(job.config?.genre || 'crime_doc').replace('_', ' ')}
                            </p>
                          </div>

                          <div className="flex items-center justify-between pt-2 border-t border-[var(--ln-subtle)]">
                            <Badge
                              variant={
                                job.status === 'FAILED'
                                  ? 'danger'
                                  : hasVideo
                                  ? 'success'
                                  : 'warning'
                              }
                            >
                              {job.current_stage || job.status}
                            </Badge>
                            <div className="flex items-center gap-1.5">
                              <Button
                                type="button"
                                variant="secondary"
                                className="!py-1 !px-2.5 text-[11px]"
                                onClick={(e: any) => {
                                  e.stopPropagation();
                                  navigate(`/qc1/${job.id}`);
                                }}
                              >
                                <span>Inspect QC1</span>
                              </Button>
                              {hasVideo && (
                                <a
                                  href={`/api/jobs/${job.id}/export`}
                                  onClick={(e) => e.stopPropagation()}
                                  className="p-1.5 rounded-lg bg-[var(--gl2)] border border-[var(--input-border)] text-[var(--tx)] hover:border-blue-500"
                                  title="Download .ZIP Pack"
                                >
                                  <Package size={13} />
                                </a>
                              )}
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )
            )}
          </div>

          {/* VIEW 3: EXECUTION TABLE (Responsive Sticky Region) */}
          <div
            role="tabpanel"
            aria-label="Execution Table"
            hidden={activeTab !== 'Execution Table'}
          >
            {activeTab === 'Execution Table' && (
              <div
                role="region"
                aria-label="Pipeline execution history table"
                tabIndex={0}
                className="studio-table-region glass-panel !p-0 max-h-[620px]"
              >
                <table className="w-full text-xs border-collapse">
                  <thead className="bg-[var(--table-head)] backdrop-blur-md">
                    <tr>
                      <th scope="col" className="p-3.5 text-left text-[var(--mu)] font-bold text-[11px] uppercase tracking-wider border-b border-[var(--ln-subtle)]">
                        Documentary Subject
                      </th>
                      <th scope="col" className="p-3.5 text-left text-[var(--mu)] font-bold text-[11px] uppercase tracking-wider border-b border-[var(--ln-subtle)]">
                        Stage
                      </th>
                      <th scope="col" className="p-3.5 text-left text-[var(--mu)] font-bold text-[11px] uppercase tracking-wider border-b border-[var(--ln-subtle)]">
                        Spec
                      </th>
                      <th scope="col" className="p-3.5 text-right text-[var(--mu)] font-bold text-[11px] uppercase tracking-wider border-b border-[var(--ln-subtle)]">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredJobs.map((job: any) => {
                      const isFailed = job.status === 'FAILED';
                      const isDone =
                        job.status === 'COMPLETED' ||
                        job.status === 'PUBLISHED' ||
                        job.current_stage === 'READY_TO_PUBLISH';
                      const isQC = job.current_stage === 'QC1';
                      const hasVideo = Boolean(resolveVideoUrl(job));
                      const isSelected = inspectedJob?.id === job.id;

                      return (
                        <tr
                          key={job.id}
                          onClick={() => setSelectedJobId(job.id)}
                          className={`border-b border-[var(--ln-subtle)] cursor-pointer transition-colors ${
                            isSelected ? 'bg-blue-600/10' : 'hover:bg-[var(--row-hover)]'
                          }`}
                        >
                          <td className="p-3.5">
                            <div className="font-bold text-[var(--tx)] line-clamp-1">{job.niche}</div>
                            <div className="text-[11px] font-mono text-[var(--mu)]">
                              Job #{job.id} · {formatVoiceShort(job.config?.voice)}
                            </div>
                          </td>
                          <td className="p-3.5 whitespace-nowrap">
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
                          <td className="p-3.5 text-[var(--mu)] font-mono whitespace-nowrap">
                            {job.config?.format || '9:16'} · {(job.config?.genre || 'crime_doc').replace('_', ' ')}
                          </td>
                          <td className="p-3.5 whitespace-nowrap">
                            <div className="flex items-center justify-end gap-1.5">
                              {hasVideo && (
                                <a
                                  href={`/api/jobs/${job.id}/export`}
                                  onClick={(e) => e.stopPropagation()}
                                  className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-[var(--gl2)] border border-[var(--input-border)] text-[var(--tx)] hover:border-blue-500 text-[11px] font-semibold"
                                  title="Download Publish-Ready .ZIP Pack"
                                >
                                  <Download size={12} className="text-blue-600 dark:text-blue-400" />
                                  <span>.ZIP</span>
                                </a>
                              )}
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  navigate(`/qc1/${job.id}`);
                                }}
                                className="p-1.5 rounded-lg text-[var(--mu)] hover:text-blue-600 dark:hover:text-blue-400 hover:bg-blue-500/10 cursor-pointer"
                                title="Open QC1 Studio"
                              >
                                <ExternalLink size={14} />
                              </button>
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setJobPendingDelete(job);
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
                    {filteredJobs.length === 0 && !isLoading && (
                      <tr>
                        <td colSpan={4} className="p-8 text-center text-[var(--mu)] text-xs">
                          No matching jobs found.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        {/* RIGHT STICKY INSPECTOR & HARDWARE GUARDRAIL RAIL (4/12) */}
        <div className="xl:col-span-4 flex flex-col gap-5 xl:sticky xl:top-4 min-w-0">
          {/* Card 1: Live Inline Screening Monitor */}
          <div className="prismatic-launch-card p-5 space-y-3.5">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-xs bg-cyan-400" />
                <span className="text-xs font-bold uppercase tracking-wider text-white">
                  Pipeline Screening Deck
                </span>
              </div>
              {inspectedJob && (
                <span className="font-mono text-[11px] text-cyan-300">
                  Job #{inspectedJob.id}
                </span>
              )}
            </div>

            {inspectedJob ? (
              <>
                <div className="rounded-xl overflow-hidden border border-white/15 bg-black flex items-center justify-center min-h-[210px] max-h-[300px]">
                  {inspectedVideoUrl ? (
                    <video
                      key={inspectedVideoUrl}
                      src={inspectedVideoUrl}
                      poster={`/output/thumb_${inspectedJob.id}_v1_16x9.jpg`}
                      controls
                      playsInline
                      className="w-full max-h-[296px] object-contain"
                    />
                  ) : (
                    <div className="p-6 text-center space-y-2">
                      <Cpu size={22} className="text-cyan-400 mx-auto animate-pulse" />
                      <div className="text-xs font-semibold text-slate-200">
                        Stage: {inspectedJob.current_stage || inspectedJob.status}
                      </div>
                      <div className="text-[11px] text-slate-400">
                        Video stream appears automatically once Pass 2 completes.
                      </div>
                    </div>
                  )}
                </div>

                <div>
                  <h3 className="text-sm font-extrabold text-white leading-snug line-clamp-2">
                    {inspectedJob.niche}
                  </h3>
                  <div className="flex items-center gap-2 flex-wrap mt-1.5 text-[11px] font-mono text-slate-300">
                    <span>{inspectedJob.config?.format || '9:16'}</span>
                    <span>·</span>
                    <span>{formatVoiceShort(inspectedJob.config?.voice)}</span>
                    <span>·</span>
                    <span>{inspectedJob.current_stage || inspectedJob.status}</span>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-2 pt-1">
                  <button
                    type="button"
                    onClick={() => navigate(`/qc1/${inspectedJob.id}`)}
                    className="py-2.5 px-3 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs flex items-center justify-center gap-1.5 cursor-pointer"
                  >
                    <ExternalLink size={13} />
                    <span>Open QC1 Studio</span>
                  </button>
                  {inspectedVideoUrl ? (
                    <a
                      href={`/api/jobs/${inspectedJob.id}/export`}
                      className="py-2.5 px-3 rounded-xl bg-white/12 hover:bg-white/20 border border-white/20 text-white font-bold text-xs flex items-center justify-center gap-1.5"
                    >
                      <Package size={13} />
                      <span>Export .ZIP</span>
                    </a>
                  ) : (
                    <button
                      type="button"
                      onClick={() => navigate('/create')}
                      className="py-2.5 px-3 rounded-xl bg-white/12 hover:bg-white/20 border border-white/20 text-white font-bold text-xs flex items-center justify-center gap-1.5 cursor-pointer"
                    >
                      <Plus size={13} />
                      <span>New Video</span>
                    </button>
                  )}
                </div>
              </>
            ) : (
              <div className="p-6 text-center text-xs text-slate-300 space-y-3">
                <p>No renders in queue yet. Launch a documentary to monitor stages and preview output here.</p>
                <Button type="button" onClick={() => navigate('/create')}>
                  <Plus size={13} />
                  <span>Open Production Deck</span>
                </Button>
              </div>
            )}
          </div>

          {/* Card 2: Hardware & Scratch Guardrail Telemetry */}
          <div className="glass-panel p-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-[var(--tx)] flex items-center gap-1.5">
                <HardDrive size={14} className="text-emerald-600 dark:text-emerald-400" />
                <span>Hardware &amp; Scratch Guardrails</span>
              </span>
              <Badge variant="success">16 GB Safe</Badge>
            </div>

            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-[11px]">
                <span className="text-[var(--mu)]">Scratch &amp; Beat LRU Cache</span>
                <span className="font-mono font-bold text-[var(--tx)]">
                  {tempMb.toFixed(1)} / 300.0 MB
                </span>
              </div>
              <Progress
                value={tempMb}
                max={300}
                label="Scratch cache usage out of 300 MB cap"
                color={tempMb > 240 ? 'var(--wa)' : 'var(--ac)'}
              />
            </div>

            <div className="grid grid-cols-2 gap-2 text-[11px] pt-1">
              <div className="glass-subcard p-2.5">
                <div className="text-[var(--mu)]">Master Outputs</div>
                <div className="font-mono font-bold text-[var(--tx)] mt-0.5">
                  {cache?.output_mb ?? '0.0'} MB ({cache?.output_count ?? 0})
                </div>
              </div>
              <div className="glass-subcard p-2.5">
                <div className="text-[var(--mu)]">RAM Sequencer</div>
                <div className="font-semibold text-emerald-600 dark:text-emerald-400 mt-0.5 flex items-center gap-1">
                  <ShieldCheck size={12} />
                  <span>Auto-Unload</span>
                </div>
              </div>
            </div>

            <Button
              type="button"
              variant="secondary"
              disabled={clearCacheMutation.isPending || tempMb <= 0}
              onClick={() => clearCacheMutation.mutate()}
              className="w-full justify-center !py-2 text-xs"
            >
              <Trash2 size={12} />
              <span>{clearCacheMutation.isPending ? 'Purging Scratch...' : 'Purge Temp Scratch'}</span>
            </Button>
          </div>
        </div>
      </div>

      {/* Native Modal Dialogs */}
      <ConfirmDialog
        isOpen={isConfirmClearOpen}
        title="Clear All Pipeline Jobs?"
        description="This removes all queued, active, and completed job entries from the production pipeline."
        confirmLabel="Clear Queue"
        onConfirm={() => {
          setIsConfirmClearOpen(false);
          clearAllMutation.mutate();
        }}
        onCancel={() => setIsConfirmClearOpen(false)}
      />

      <ConfirmDialog
        isOpen={Boolean(jobPendingDelete)}
        title={jobPendingDelete ? `Delete Job #${jobPendingDelete.id}?` : 'Delete Job?'}
        description={
          jobPendingDelete
            ? `Remove "${jobPendingDelete.niche}" from the production pipeline?`
            : 'Remove this job from the production pipeline?'
        }
        confirmLabel="Delete Job"
        onConfirm={() => {
          if (jobPendingDelete) {
            deleteJobMutation.mutate(jobPendingDelete.id);
          }
          setJobPendingDelete(null);
        }}
        onCancel={() => setJobPendingDelete(null)}
      />
    </div>
  );
}
