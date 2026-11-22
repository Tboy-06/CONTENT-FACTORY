import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Film,
  Download,
  Trash2,
  Plus,
  Search,
  Layers,
  Brain,
  Package,
  Radio,
  ArrowRight
} from 'lucide-react';
import {
  useJobs,
  useDeleteJob,
  useClearAllJobs,
  useHouseQuotas,
  useContinueHarvesterMilestone,
  useLearnedRules
} from '../api/client';
import { Button, Badge, EmptyState, Tabs } from '../components/ui';

const STATUS_FILTERS = [
  { id: 'All', label: 'All Videos' },
  { id: 'READY', label: 'Ready / QC1' },
  { id: 'COMPLETED', label: 'Completed' },
  { id: 'PUBLISHED', label: 'Published' }
];

export default function Vault() {
  const navigate = useNavigate();
  const { data: jobs = [], isLoading } = useJobs();
  const { data: houseQuotas } = useHouseQuotas();
  const { data: learnedRulesData } = useLearnedRules();
  const deleteJobMutation = useDeleteJob();
  const clearAllMutation = useClearAllJobs();
  const continueMilestoneMutation = useContinueHarvesterMilestone();

  const [activeTab, setActiveTab] = useState('Rendered Videos');
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('All');

  const vaultJobs = jobs.filter(
    (j: any) =>
      j.status === 'COMPLETED' ||
      j.status === 'PUBLISHED' ||
      j.current_stage === 'QC1' ||
      j.current_stage === 'READY_TO_PUBLISH' ||
      j.assets?.some((a: any) => a.type === 'VIDEO' || a.type === 'video')
  );

  const filteredJobs = vaultJobs.filter((j: any) => {
    if (search && !String(j.niche || '').toLowerCase().includes(search.toLowerCase())) return false;
    if (statusFilter === 'READY') {
      return j.current_stage === 'QC1' || j.current_stage === 'READY_TO_PUBLISH' || j.status === 'AWAITING_APPROVAL';
    }
    if (statusFilter !== 'All' && j.status !== statusFilter) return false;
    return true;
  });

  const qData = houseQuotas?.data;
  const totalRecords = qData?.total_records ?? 0;
  const masterTarget = qData?.target_total ?? 0;
  const milestoneCap = qData?.current_milestone_cap ?? 0;
  const milestoneStatus = qData?.milestone_status ?? 'LOADING';
  const isAtMilestone =
    milestoneStatus === 'PAUSED_AT_100K_CHECKPOINT' ||
    (milestoneCap > 0 && totalRecords >= milestoneCap);
  const lastHarvested = qData?.last_harvested_item;
  const houses = qData?.houses || {};
  const rules = learnedRulesData?.rules || [];
  const totalRules = learnedRulesData?.total_rules ?? rules.length;

  return (
    <div className="animate-in fade-in min-h-full flex flex-col pb-8 space-y-5">
      {/* Header */}
      <div className="flex justify-between items-center flex-wrap gap-3 shrink-0">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-[var(--tx)]">Director Vault</h1>
          <div className="text-[var(--mu)] text-xs mt-0.5">
            Finished video archive, 1-click publish packs, 5-House training memory, and Reflexion guardrails.
          </div>
        </div>

        <div className="flex items-center gap-2">
          {vaultJobs.length > 0 && (
            <Button
              variant="secondary"
              onClick={() => {
                if (confirm('Clear all vault videos and jobs?')) {
                  clearAllMutation.mutate();
                }
              }}
              disabled={clearAllMutation.isPending}
              className="hover:!text-red-500"
            >
              <Trash2 size={13} />
              <span>Clear Vault</span>
            </Button>
          )}
          <Button variant="primary" onClick={() => navigate('/create')}>
            <Plus size={14} />
            <span>New Video</span>
          </Button>
        </div>
      </div>

      {/* Unified 3-Zone Vault KPI Strip */}
      <div className="glass-panel p-4 grid grid-cols-1 md:grid-cols-3 gap-4 md:gap-0 md:divide-x divide-[var(--ln-subtle)]">
        <div className="md:pr-5 flex items-center justify-between">
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-wider text-[var(--mu)]">
              Rendered Media Library
            </div>
            <div className="text-2xl font-bold font-mono text-[var(--tx)] mt-1">{vaultJobs.length}</div>
            <div className="text-[11px] text-[var(--mu)]">Exportable MP4 & .ZIP packs</div>
          </div>
          <div className="w-9 h-9 rounded-xl bg-blue-600/15 border border-blue-500/30 text-blue-600 dark:text-blue-400 flex items-center justify-center">
            <Film size={17} />
          </div>
        </div>

        <div className="md:px-5 flex items-center justify-between">
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-wider text-[var(--mu)]">
              5-House Knowledge Vault
            </div>
            <div className="text-2xl font-bold font-mono text-[var(--tx)] mt-1">
              {qData ? totalRecords.toLocaleString() : '--'}
              <span className="text-xs font-normal text-[var(--mu)]">
                {' '}
                / {masterTarget > 0 ? masterTarget.toLocaleString() : '--'}
              </span>
            </div>
            <div className="text-[11px] text-[var(--mu)]">
              Milestone cap: {milestoneCap > 0 ? milestoneCap.toLocaleString() : '--'} ({milestoneStatus})
            </div>
          </div>
          <div className="w-9 h-9 rounded-xl bg-amber-500/15 border border-amber-500/30 text-amber-600 dark:text-amber-400 flex items-center justify-center">
            <Layers size={17} />
          </div>
        </div>

        <div className="md:pl-5 flex items-center justify-between">
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-wider text-[var(--mu)]">
              Reflexion Guardrails
            </div>
            <div className="text-2xl font-bold font-mono text-emerald-600 dark:text-emerald-400 mt-1">
              {totalRules}
            </div>
            <div className="text-[11px] text-[var(--mu)]">Active auto-critic rules injected</div>
          </div>
          <div className="w-9 h-9 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-600 dark:text-emerald-400 flex items-center justify-center">
            <Brain size={17} />
          </div>
        </div>
      </div>

      {/* Mode Switcher */}
      <div className="-mb-2">
        <Tabs
          tabs={['Rendered Videos', '5-House Knowledge & Rules']}
          activeTab={activeTab}
          onChange={setActiveTab}
        />
      </div>

      {/* TAB 1: RENDERED VIDEOS */}
      {activeTab === 'Rendered Videos' && (
        <div className="space-y-4">
          {/* Search & Segmented Status Filter Bar */}
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-1.5 flex-wrap">
              {STATUS_FILTERS.map((f) => {
                const active = statusFilter === f.id;
                return (
                  <button
                    key={f.id}
                    onClick={() => setStatusFilter(f.id)}
                    className={`px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all cursor-pointer ${
                      active
                        ? 'bg-blue-600 text-white border-blue-500 shadow-sm'
                        : 'bg-[var(--gl)] text-[var(--mu)] border-[var(--ln)] hover:bg-[var(--gl2)] hover:text-[var(--tx)]'
                    }`}
                  >
                    {f.label}
                  </button>
                );
              })}
            </div>

            <div className="relative min-w-[240px] flex-1 sm:flex-initial">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--mu)]" />
              <input
                type="text"
                placeholder="Search vault videos..."
                className="glass-input w-full pl-9 pr-3 py-1.5 text-xs"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
          </div>

          {isLoading ? (
            <div className="grid grid-cols-[repeat(auto-fill,minmax(250px,1fr))] gap-4">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="glass-panel overflow-hidden animate-pulse h-[220px]" />
              ))}
            </div>
          ) : filteredJobs.length === 0 ? (
            <EmptyState
              title="No finished videos match this filter"
              description="Launch a new documentary or switch status filters to inspect your vault."
            />
          ) : (
            <div className="grid grid-cols-[repeat(auto-fill,minmax(265px,1fr))] gap-4 pb-4">
              {filteredJobs.map((job: any, idx: number) => {
                const videoAsset = job.assets?.find((a: any) => a.type === 'VIDEO' || a.type === 'video');
                const videoMeta = videoAsset?.metadata || {};
                const videoUrl =
                  videoMeta.video_url ||
                  (videoAsset?.path ? `/output/${videoAsset.path.split(/[\\/]/).pop()}` : null);
                const genre = String(videoMeta.genre || job.config?.genre || 'auto');
                const cardBannerClass =
                  genre === 'viral_edu'
                    ? 'iridescent-card-edu'
                    : genre === 'movie_cinema' || genre === 'action_hype'
                    ? 'iridescent-card-cinema'
                    : idx % 3 === 1
                    ? 'iridescent-card-edu'
                    : idx % 3 === 2
                    ? 'iridescent-card-cinema'
                    : 'iridescent-card-crime';

                return (
                  <div
                    key={job.id}
                    onClick={() => navigate(`/qc1/${job.id}`)}
                    className="glass-panel overflow-hidden cursor-pointer transition-all hover:-translate-y-1 hover:border-blue-500/50 group !p-0 flex flex-col justify-between"
                  >
                    {/* Iridescent Media Header */}
                    <div className={`relative h-[126px] ${cardBannerClass} flex items-center justify-center p-4`}>
                      <div className="w-11 h-11 rounded-xl bg-white/15 backdrop-blur-md text-white border border-white/30 flex items-center justify-center shadow-lg group-hover:scale-105 transition-transform">
                        <Film size={20} />
                      </div>
                      <span className="preserve-white absolute top-2.5 left-2.5 text-[10px] font-mono font-bold px-2 py-0.5 rounded-lg bg-black/45 backdrop-blur-sm text-white border border-white/20">
                        {job.config?.format || '9:16'}
                      </span>
                      <span className="preserve-white absolute top-2.5 right-2.5 text-[10px] font-mono font-bold px-2 py-0.5 rounded-lg bg-black/45 backdrop-blur-sm text-white border border-white/20">
                        Job #{job.id}
                      </span>
                      <span className="preserve-white absolute bottom-2.5 right-2.5 text-[10px] font-mono font-semibold px-2 py-0.5 rounded-md bg-black/45 text-white">
                        {videoMeta.duration ? `${Math.round(videoMeta.duration)}s` : job.config?.duration || '--'}
                      </span>
                    </div>

                    <div className="p-4 space-y-3 flex-1 flex flex-col justify-between">
                      <div>
                        <b className="font-bold text-sm text-[var(--tx)] line-clamp-2 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors leading-snug">
                          {job.niche}
                        </b>

                        <div className="flex justify-between items-center text-xs mt-2">
                          <Badge
                            variant={
                              job.status === 'PUBLISHED' || job.status === 'COMPLETED'
                                ? 'success'
                                : job.current_stage === 'QC1'
                                ? 'warning'
                                : 'info'
                            }
                          >
                            {job.status === 'PUBLISHED'
                              ? 'Published'
                              : job.current_stage === 'QC1'
                              ? 'QC1 Ready'
                              : job.current_stage || 'Ready'}
                          </Badge>
                          <span className="font-mono text-[10px] text-[var(--mu)] uppercase">
                            {genre.replace('_', ' ')}
                          </span>
                        </div>
                      </div>

                      {/* Actions Row */}
                      <div className="flex items-center justify-between gap-2 pt-2.5 border-t border-[var(--ln-subtle)]">
                        <div className="flex items-center gap-2">
                          {videoUrl && (
                            <a
                              href={videoUrl}
                              download={`${String(job.niche || 'video').replace(/[^a-zA-Z0-9_-]/g, '_')}_9x16.mp4`}
                              onClick={(e) => e.stopPropagation()}
                              className="inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-1 rounded-lg bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 border border-emerald-500/30 hover:bg-emerald-500/25 transition-colors"
                              title="Download MP4 video"
                            >
                              <Download size={12} />
                              <span>MP4</span>
                            </a>
                          )}

                          {videoUrl && (
                            <a
                              href={`/api/jobs/${job.id}/export`}
                              onClick={(e) => e.stopPropagation()}
                              className="inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-1 rounded-lg bg-blue-500/15 text-blue-700 dark:text-blue-400 border border-blue-500/30 hover:bg-blue-500/25 transition-colors"
                              title="Download Publish-Ready .ZIP Pack (MP4 + Thumb + Captions + Copy)"
                            >
                              <Package size={12} />
                              <span>.ZIP Pack</span>
                            </a>
                          )}
                        </div>

                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            deleteJobMutation.mutate(job.id);
                          }}
                          className="text-[var(--mu)] hover:text-red-500 p-1.5 transition-colors rounded-lg hover:bg-red-500/10 cursor-pointer"
                          title="Delete video from vault"
                        >
                          <Trash2 size={13} />
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* TAB 2: 5-HOUSE KNOWLEDGE & REFLEXION RULES */}
      {activeTab === '5-House Knowledge & Rules' && (
        <div className="space-y-5">
          {/* Live Harvester Status Banner */}
          <div className="glass-panel p-4 flex flex-col md:flex-row md:items-center justify-between gap-3">
            <div className="space-y-1">
              <div className="flex items-center gap-2 flex-wrap">
                <Radio size={14} className="text-emerald-500 animate-pulse" />
                <span className="text-xs font-bold text-[var(--tx)]">
                  Live 5-House Dataset Harvester
                </span>
                <Badge variant={isAtMilestone ? 'warning' : 'success'}>
                  {milestoneStatus}
                </Badge>
                <span className="text-[11px] font-mono text-[var(--mu)]">
                  {qData ? totalRecords.toLocaleString() : '--'} / {masterTarget > 0 ? masterTarget.toLocaleString() : '--'} (
                  {masterTarget > 0 ? ((totalRecords / masterTarget) * 100).toFixed(2) : '0.00'}%)
                </span>
              </div>
              {lastHarvested && (
                <div className="text-[11px] text-[var(--mu)] truncate max-w-2xl">
                  Latest ingested: <b className="text-[var(--tx)]">{lastHarvested.house}</b> / {lastHarvested.sub_room} · "{lastHarvested.preview}"
                </div>
              )}
            </div>

            {isAtMilestone && (
              <Button
                variant="primary"
                onClick={() => continueMilestoneMutation.mutate()}
                disabled={continueMilestoneMutation.isPending}
              >
                <span>
                  {qData?.milestone_step
                    ? `Advance Milestone (+${qData.milestone_step.toLocaleString()})`
                    : 'Advance Next Milestone'}
                </span>
                <ArrowRight size={13} />
              </Button>
            )}
          </div>

          {/* 5-House Breakdown Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Object.entries(houses).map(([houseKey, houseVal]: [string, any]) => {
              const count = houseVal?.count ?? 0;
              const target = houseVal?.target ?? 0;
              const pct = target > 0 ? Math.min(100, (count / target) * 100) : 0;
              const isFull = houseVal?.status === 'FULL' || (target > 0 && count >= target);
              const subRooms = houseVal?.sub_rooms || {};
              const title = houseKey.replace(/^HOUSE_\d+_/, '').replace(/_/g, ' ');

              return (
                <div key={houseKey} className="glass-panel p-4 space-y-3 flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between gap-2 mb-1">
                      <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--tx)] truncate">
                        {title}
                      </h3>
                      <Badge variant={isFull ? 'warning' : 'success'}>{isFull ? 'FULL' : 'OPEN'}</Badge>
                    </div>
                    <div className="flex items-baseline justify-between font-mono text-xs mt-1">
                      <span className="text-base font-bold text-[var(--tx)]">{count.toLocaleString()}</span>
                      <span className="text-[11px] text-[var(--mu)]">
                        / {target.toLocaleString()} ({pct.toFixed(2)}%)
                      </span>
                    </div>
                    <div className="h-1.5 bg-[var(--ln-subtle)] rounded-md overflow-hidden mt-2">
                      <div
                        className={`h-full transition-all duration-500 ${isFull ? 'bg-amber-500' : 'bg-blue-600'}`}
                        style={{ width: `${Math.max(pct, count > 0 ? 1.5 : 0)}%` }}
                      />
                    </div>
                  </div>

                  {/* Sub-rooms */}
                  {Object.keys(subRooms).length > 0 && (
                    <div className="pt-2.5 border-t border-[var(--ln-subtle)] flex flex-wrap gap-1.5">
                      {Object.entries(subRooms).map(([srKey, srVal]: [string, any]) => (
                        <span
                          key={srKey}
                          className="text-[10px] font-mono px-2 py-0.5 rounded-lg bg-[var(--gl2)] border border-[var(--ln-subtle)] text-[var(--mu)]"
                        >
                          {srKey}: <b className="text-[var(--tx)]">{(srVal?.count ?? 0).toLocaleString()}</b>
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Reflexion Guardrails Section */}
          <div className="glass-panel p-5 space-y-3">
            <div className="flex items-center justify-between border-b border-[var(--ln-subtle)] pb-2.5">
              <div className="flex items-center gap-2">
                <Brain size={16} className="text-blue-600 dark:text-blue-400" />
                <h2 className="text-sm font-bold text-[var(--tx)]">
                  Reflexion Auto-Critic Learned Rules
                </h2>
              </div>
              <Badge variant="info">{totalRules} Active Rules</Badge>
            </div>

            {rules.length === 0 ? (
              <div className="p-6 text-center text-xs text-[var(--mu)]">
                No editorial mistakes logged yet. Every QC1 edit or critic rejection automatically builds a permanent rule here.
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {rules.map((rule, i) => (
                  <div key={i} className="glass-subcard p-3.5 space-y-1.5">
                    <div className="flex items-center justify-between gap-2">
                      <Badge variant="info">#{rule.category}</Badge>
                      <span className="text-[11px] font-mono font-semibold text-amber-600 dark:text-amber-400">
                        Caught {rule.occurrences}x
                      </span>
                    </div>
                    <p className="text-xs text-[var(--tx)] leading-relaxed">{rule.lesson}</p>
                    {rule.context_topic && (
                      <div className="text-[10px] text-[var(--mu)] font-mono">
                        Context: {rule.context_topic}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
