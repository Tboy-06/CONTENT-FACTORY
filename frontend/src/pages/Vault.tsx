import { useState, useMemo } from 'react';
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
  ArrowRight,
  ShieldCheck,
  Play,
  ExternalLink,
  CheckCircle2,
  X,
  FileText
} from 'lucide-react';
import {
  useJobs,
  useDeleteJob,
  useClearAllJobs,
  useHouseQuotas,
  useContinueHarvesterMilestone,
  useLearnedRules
} from '../api/client';
import {
  Button,
  Badge,
  EmptyState,
  Tabs,
  ConfirmDialog,
  Progress,
  ProgressRing
} from '../components/ui';

const STATUS_FILTERS = [
  { id: 'All', label: 'All Masters' },
  { id: 'READY', label: 'QC1 / Ready' },
  { id: 'COMPLETED', label: 'Completed' },
  { id: 'PUBLISHED', label: 'Published' }
];

function resolveVaultVideoUrl(job: any): string | null {
  const videoAsset = job?.assets?.find((a: any) => a.type === 'VIDEO' || a.type === 'video');
  const videoMeta = videoAsset?.metadata || {};
  if (videoMeta.video_url) return videoMeta.video_url;
  if (videoAsset?.path) return `/output/${String(videoAsset.path).split(/[\\/]/).pop()}`;
  return null;
}

export default function Vault() {
  const navigate = useNavigate();
  const { data: jobs = [], isLoading } = useJobs();
  const { data: houseQuotas } = useHouseQuotas();
  const { data: learnedRulesData } = useLearnedRules();
  const deleteJobMutation = useDeleteJob();
  const clearAllMutation = useClearAllJobs();
  const continueMilestoneMutation = useContinueHarvesterMilestone();

  const [activeTab, setActiveTab] = useState('Master Media Archive');
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('All');
  const [formatFilter, setFormatFilter] = useState<'ALL' | '9:16' | '16:9'>('ALL');
  const [ruleCategoryFilter, setRuleCategoryFilter] = useState('ALL');
  const [ruleSearch, setRuleSearch] = useState('');
  const [selectedVaultJobId, setSelectedVaultJobId] = useState<number | null>(null);
  const [isConfirmClearOpen, setIsConfirmClearOpen] = useState(false);
  const [jobPendingDelete, setJobPendingDelete] = useState<any | null>(null);

  const vaultJobs = useMemo(
    () =>
      jobs.filter(
        (j: any) =>
          j.status === 'COMPLETED' ||
          j.status === 'PUBLISHED' ||
          j.current_stage === 'QC1' ||
          j.current_stage === 'READY_TO_PUBLISH' ||
          j.assets?.some((a: any) => a.type === 'VIDEO' || a.type === 'video')
      ),
    [jobs]
  );

  const filteredJobs = useMemo(
    () =>
      vaultJobs.filter((j: any) => {
        if (search && !String(j.niche || '').toLowerCase().includes(search.toLowerCase())) {
          return false;
        }
        const fmt = j.config?.format || '9:16';
        if (formatFilter !== 'ALL' && fmt !== formatFilter) return false;
        if (statusFilter === 'READY') {
          return (
            j.current_stage === 'QC1' ||
            j.current_stage === 'READY_TO_PUBLISH' ||
            j.status === 'AWAITING_APPROVAL'
          );
        }
        if (statusFilter !== 'All' && j.status !== statusFilter) return false;
        return true;
      }),
    [vaultJobs, search, statusFilter, formatFilter]
  );

  const screenedJob = useMemo(() => {
    if (selectedVaultJobId !== null) {
      const match = vaultJobs.find((j: any) => j.id === selectedVaultJobId);
      if (match) return match;
    }
    return filteredJobs[0] || vaultJobs[0] || null;
  }, [vaultJobs, filteredJobs, selectedVaultJobId]);

  const screenedVideoUrl = screenedJob ? resolveVaultVideoUrl(screenedJob) : null;

  const qData = houseQuotas?.data;
  const totalRecords = qData?.total_records ?? 0;
  const masterTarget = qData?.target_total ?? 0;
  const milestoneCap = qData?.current_milestone_cap ?? 0;
  const milestoneStatus = qData?.milestone_status ?? 'IDLE';
  const isHarvesterLive = Boolean(qData?.harvester_active);
  const isPausedForRender =
    Boolean(qData?.render_lock_active) || milestoneStatus === 'PAUSED_FOR_ACTIVE_RENDER';
  const isAtMilestone =
    milestoneStatus === 'PAUSED_AT_100K_CHECKPOINT' ||
    (milestoneCap > 0 && totalRecords >= milestoneCap);
  const lastHarvested = qData?.last_harvested_item;
  const houses = qData?.houses || {};

  const rules = learnedRulesData?.rules || [];
  const totalRules = learnedRulesData?.total_rules ?? rules.length;

  const ruleCategories = useMemo(() => {
    const cats = Array.from(new Set(rules.map((r) => r.category).filter(Boolean)));
    return ['ALL', ...cats];
  }, [rules]);

  const filteredRules = useMemo(
    () =>
      rules.filter((r) => {
        if (ruleCategoryFilter !== 'ALL' && r.category !== ruleCategoryFilter) return false;
        if (
          ruleSearch &&
          !r.lesson.toLowerCase().includes(ruleSearch.toLowerCase()) &&
          !String(r.context_topic || '').toLowerCase().includes(ruleSearch.toLowerCase())
        ) {
          return false;
        }
        return true;
      }),
    [rules, ruleCategoryFilter, ruleSearch]
  );

  const maxRuleHits = Math.max(...rules.map((r) => Number(r.occurrences || 1)), 5);

  return (
    <div className="animate-in fade-in min-h-full flex flex-col pb-10 space-y-5">
      {/* Studio Header */}
      <div className="flex justify-between items-center flex-wrap gap-3 shrink-0">
        <div>
          <div className="flex items-center gap-2.5 flex-wrap">
            <h1 className="text-2xl font-bold tracking-tight text-[var(--tx)]">
              Director Vault &amp; Reflexion Logs
            </h1>
            <Badge variant="info">Master Archive + Self-Healing Memory</Badge>
          </div>
          <p className="text-[var(--mu)] text-xs mt-0.5">
            Screen finished documentaries, audit learned Reflexion editorial guardrails, and inspect the 5-House training vault.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {vaultJobs.length > 0 && (
            <Button
              type="button"
              variant="secondary"
              onClick={() => setIsConfirmClearOpen(true)}
              disabled={clearAllMutation.isPending}
              className="hover:!text-red-500"
            >
              <Trash2 size={13} />
              <span>Clear Archive</span>
            </Button>
          )}
          <Button type="button" variant="primary" onClick={() => navigate('/create')}>
            <Plus size={14} />
            <span>New Production</span>
          </Button>
        </div>
      </div>

      {/* 3-Zone KPI & ProgressRing Banner */}
      <div className="glass-panel p-5 grid grid-cols-1 md:grid-cols-3 gap-5 md:divide-x divide-[var(--ln-subtle)]">
        <div className="flex items-center justify-between gap-3 md:pr-5">
          <div>
            <span className="text-[11px] font-bold uppercase tracking-wider text-[var(--mu)]">
              Master Media Archive
            </span>
            <div className="text-3xl font-extrabold font-mono text-[var(--tx)] mt-1 tabular-nums">
              {vaultJobs.length}
            </div>
            <p className="text-[11px] text-[var(--mu)] mt-0.5">
              Finished renders with MP4 &amp; `.ZIP` packs
            </p>
          </div>
          <div className="w-12 h-12 rounded-2xl bg-blue-600/15 border border-blue-500/30 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0">
            <Film size={20} />
          </div>
        </div>

        <div className="flex items-center justify-between gap-3 md:px-5">
          <div>
            <span className="text-[11px] font-bold uppercase tracking-wider text-[var(--mu)]">
              Director &amp; Reflexion Rules
            </span>
            <div className="text-3xl font-extrabold font-mono text-emerald-600 dark:text-emerald-400 mt-1 tabular-nums">
              {totalRules}
            </div>
            <p className="text-[11px] text-[var(--mu)] mt-0.5">
              Active editorial lessons injected into scripts
            </p>
          </div>
          <div className="w-12 h-12 rounded-2xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-600 dark:text-emerald-400 flex items-center justify-center shrink-0">
            <Brain size={20} />
          </div>
        </div>

        <div className="flex items-center justify-between gap-3 md:pl-5">
          <div className="min-w-0">
            <span className="text-[11px] font-bold uppercase tracking-wider text-[var(--mu)]">
              5-House Brain Milestone
            </span>
            <div className="text-2xl font-extrabold font-mono text-[var(--tx)] mt-1 tabular-nums truncate">
              {qData ? totalRecords.toLocaleString() : '--'}
              <span className="text-xs font-normal text-[var(--mu)]">
                {' '}
                / {milestoneCap > 0 ? milestoneCap.toLocaleString() : '--'}
              </span>
            </div>
            <p className="text-[11px] text-[var(--mu)] mt-0.5">
              {isAtMilestone
                ? 'Checkpoint reached'
                : isPausedForRender
                ? 'Paused for active render'
                : isHarvesterLive
                ? 'Harvester actively syncing'
                : 'Harvester idle'}
            </p>
          </div>
          <ProgressRing
            value={totalRecords}
            max={Math.max(1, milestoneCap)}
            size={54}
            color="var(--wa)"
            label="5-House current milestone completion"
          />
        </div>
      </div>

      {/* Accessible Single-Row Tab Switcher */}
      <div className="-mb-2">
        <Tabs
          tabs={[
            'Master Media Archive',
            'Director & Reflexion Logs',
            '5-House Knowledge Matrix'
          ]}
          activeTab={activeTab}
          onChange={setActiveTab}
          ariaLabel="Director Vault sections"
          counts={{
            'Master Media Archive': vaultJobs.length,
            'Director & Reflexion Logs': totalRules,
            '5-House Knowledge Matrix': Object.keys(houses).length || 5
          }}
        />
      </div>

      {/* =================================================================== */}
      {/* TAB 1: MASTER MEDIA ARCHIVE + INLINE VAULT SCREENING MONITOR        */}
      {/* =================================================================== */}
      <div
        role="tabpanel"
        aria-label="Master Media Archive"
        hidden={activeTab !== 'Master Media Archive'}
      >
        {activeTab === 'Master Media Archive' && (
          <div className="space-y-4">
            <search
              aria-label="Filter master archive videos"
              className="flex flex-wrap items-center justify-between gap-3"
            >
              <div className="pill-row-balance items-center gap-1.5">
                {STATUS_FILTERS.map((f) => {
                  const active = statusFilter === f.id;
                  return (
                    <button
                      key={f.id}
                      type="button"
                      onClick={() => setStatusFilter(f.id)}
                      className={`px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all cursor-pointer ${
                        active
                          ? 'bg-blue-600 text-white border-blue-500 shadow-xs'
                          : 'bg-[var(--gl)] text-[var(--mu)] border-[var(--ln)] hover:bg-[var(--gl2)] hover:text-[var(--tx)]'
                      }`}
                    >
                      {f.label}
                    </button>
                  );
                })}

                <span className="mx-1 h-4 w-px bg-[var(--ln-subtle)]" aria-hidden="true" />

                {(['ALL', '9:16', '16:9'] as const).map((fmt) => {
                  const active = formatFilter === fmt;
                  return (
                    <button
                      key={fmt}
                      type="button"
                      onClick={() => setFormatFilter(fmt)}
                      className={`px-2.5 py-1.5 rounded-xl text-xs font-mono font-semibold border transition-all cursor-pointer ${
                        active
                          ? 'bg-amber-500 text-slate-950 border-amber-400'
                          : 'bg-[var(--gl)] text-[var(--mu)] border-[var(--ln)] hover:text-[var(--tx)]'
                      }`}
                    >
                      {fmt === 'ALL' ? 'All Ratios' : fmt}
                    </button>
                  );
                })}
              </div>

              <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-[var(--input-bg)] border border-[var(--input-border)] min-w-[230px]">
                <Search size={14} className="text-[var(--mu)] shrink-0" />
                <input
                  type="search"
                  placeholder="Search master videos..."
                  className="w-full bg-transparent text-xs outline-none text-[var(--tx)] placeholder:text-[var(--mu)]"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
                {search && (
                  <button
                    type="button"
                    onClick={() => setSearch('')}
                    className="text-[var(--mu)] hover:text-red-500 cursor-pointer"
                  >
                    <X size={13} />
                  </button>
                )}
              </div>
            </search>

            {isLoading ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {[...Array(3)].map((_, i) => (
                  <div key={i} className="glass-panel animate-pulse h-[240px]" />
                ))}
              </div>
            ) : filteredJobs.length === 0 ? (
              <EmptyState
                title="No master videos match this filter"
                description="Reset your status/ratio filters or launch a new documentary from the Production Deck."
              />
            ) : (
              <div className="grid grid-cols-1 xl:grid-cols-12 gap-5 items-start">
                {/* Media Showcase Grid (8/12) */}
                <div className="xl:col-span-8 grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {filteredJobs.map((job: any, idx: number) => {
                    const videoAsset = job.assets?.find(
                      (a: any) => a.type === 'VIDEO' || a.type === 'video'
                    );
                    const videoMeta = videoAsset?.metadata || {};
                    const videoUrl = resolveVaultVideoUrl(job);
                    const genre = String(videoMeta.genre || job.config?.genre || 'auto');
                    const isSelected = screenedJob?.id === job.id;
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
                        onClick={() => setSelectedVaultJobId(job.id)}
                        className={`glass-panel !p-0 overflow-hidden cursor-pointer transition-all hover:-translate-y-0.5 group flex flex-col justify-between ${
                          isSelected ? '!border-blue-500 ring-1 ring-blue-500/40 shadow-md' : ''
                        }`}
                      >
                        <div className={`relative h-36 ${cardBannerClass} flex items-center justify-center overflow-hidden`}>
                          <img
                            src={`/output/thumb_${job.id}_v1_16x9.jpg`}
                            alt=""
                            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                            onError={(e) => {
                              (e.currentTarget as HTMLImageElement).style.display = 'none';
                            }}
                          />
                          <span className="preserve-white absolute top-2.5 left-2.5 text-[10px] font-mono font-bold px-2 py-0.5 rounded-lg bg-black/60 text-white border border-white/20">
                            {job.config?.format || '9:16'}
                          </span>
                          <span className="preserve-white absolute top-2.5 right-2.5 text-[10px] font-mono font-bold px-2 py-0.5 rounded-lg bg-black/60 text-white border border-white/20">
                            Job #{job.id}
                          </span>
                          <span className="preserve-white absolute bottom-2.5 left-2.5 text-[10px] font-semibold px-2 py-0.5 rounded-md bg-black/65 text-sky-200 flex items-center gap-1">
                            <Play size={10} />
                            <span>Screen</span>
                          </span>
                          <span className="preserve-white absolute bottom-2.5 right-2.5 text-[10px] font-mono font-semibold px-2 py-0.5 rounded-md bg-black/65 text-white">
                            {videoMeta.duration
                              ? `${Math.round(videoMeta.duration)}s`
                              : job.config?.duration || '--'}
                          </span>
                        </div>

                        <div className="p-4 space-y-3 flex-1 flex flex-col justify-between">
                          <div>
                            <h3 className="font-bold text-sm text-[var(--tx)] line-clamp-2 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors leading-snug">
                              {job.niche}
                            </h3>

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

                          <div className="flex items-center justify-between gap-2 pt-2.5 border-t border-[var(--ln-subtle)]">
                            <div className="flex items-center gap-1.5">
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  navigate(`/qc1/${job.id}`);
                                }}
                                className="inline-flex items-center gap-1 text-[11px] font-semibold px-2.5 py-1 rounded-lg bg-[var(--gl2)] border border-[var(--input-border)] text-[var(--tx)] hover:border-blue-500 cursor-pointer"
                              >
                                <ExternalLink size={11} />
                                <span>QC1</span>
                              </button>

                              {videoUrl && (
                                <a
                                  href={videoUrl}
                                  download={`${String(job.niche || 'video').replace(/[^a-zA-Z0-9_-]/g, '_')}_master.mp4`}
                                  onClick={(e) => e.stopPropagation()}
                                  className="inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-1 rounded-lg bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 border border-emerald-500/30 hover:bg-emerald-500/25"
                                  title="Download MP4"
                                >
                                  <Download size={11} />
                                  <span>MP4</span>
                                </a>
                              )}

                              {videoUrl && (
                                <a
                                  href={`/api/jobs/${job.id}/export`}
                                  onClick={(e) => e.stopPropagation()}
                                  className="inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-1 rounded-lg bg-blue-500/15 text-blue-700 dark:text-blue-400 border border-blue-500/30 hover:bg-blue-500/25"
                                  title="Download Publish-Ready .ZIP Pack"
                                >
                                  <Package size={11} />
                                  <span>.ZIP</span>
                                </a>
                              )}
                            </div>

                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                setJobPendingDelete(job);
                              }}
                              className="text-[var(--mu)] hover:text-red-500 p-1.5 transition-colors rounded-lg hover:bg-red-500/10 cursor-pointer"
                              title="Delete from vault"
                            >
                              <Trash2 size={13} />
                            </button>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* Sticky Vault Screening Monitor (4/12) */}
                <div className="xl:col-span-4 xl:sticky xl:top-4">
                  <div className="prismatic-launch-card p-5 space-y-3.5">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold uppercase tracking-wider text-white flex items-center gap-2">
                        <span className="w-2 h-2 rounded-xs bg-emerald-400" />
                        <span>Master Screening Room</span>
                      </span>
                      {screenedJob && (
                        <span className="font-mono text-[11px] text-cyan-300">
                          Job #{screenedJob.id}
                        </span>
                      )}
                    </div>

                    {screenedJob ? (
                      <>
                        <div className="rounded-xl overflow-hidden border border-white/15 bg-black flex items-center justify-center min-h-[220px] max-h-[320px]">
                          {screenedVideoUrl ? (
                            <video
                              key={screenedVideoUrl}
                              src={screenedVideoUrl}
                              poster={`/output/thumb_${screenedJob.id}_v1_16x9.jpg`}
                              controls
                              playsInline
                              className="w-full max-h-[316px] object-contain"
                            />
                          ) : (
                            <div className="p-6 text-center text-xs text-slate-400">
                              Master stream unavailable on disk.
                            </div>
                          )}
                        </div>

                        <div>
                          <h3 className="text-sm font-extrabold text-white leading-snug">
                            {screenedJob.niche}
                          </h3>
                          <p className="text-[11px] text-slate-300 mt-1 line-clamp-2">
                            {screenedJob.assets?.find((a: any) => a.type === 'VIDEO' || a.type === 'video')?.metadata?.script?.hook ||
                              'Mastered at -14 LUFS with burned-in Montserrat-Black karaoke captions.'}
                          </p>
                        </div>

                        <div className="grid grid-cols-2 gap-2 pt-1">
                          <button
                            type="button"
                            onClick={() => navigate(`/qc1/${screenedJob.id}`)}
                            className="py-2.5 px-3 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs flex items-center justify-center gap-1.5 cursor-pointer"
                          >
                            <ExternalLink size={13} />
                            <span>Edit in QC1</span>
                          </button>
                          <a
                            href={`/api/jobs/${screenedJob.id}/export`}
                            className="py-2.5 px-3 rounded-xl bg-white text-slate-950 hover:bg-cyan-50 font-extrabold text-xs flex items-center justify-center gap-1.5"
                          >
                            <Package size={13} />
                            <span>Download .ZIP</span>
                          </a>
                        </div>
                      </>
                    ) : null}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* =================================================================== */}
      {/* TAB 2: DIRECTOR & REFLEXION LOGS (DEDICATED STUDIO AUDIT CONSOLE)   */}
      {/* =================================================================== */}
      <div
        role="tabpanel"
        aria-label="Director & Reflexion Logs"
        hidden={activeTab !== 'Director & Reflexion Logs'}
      >
        {activeTab === 'Director & Reflexion Logs' && (
          <div className="space-y-4">
            <search
              aria-label="Filter Reflexion rules and director logs"
              className="flex flex-wrap items-center justify-between gap-3"
            >
              <div className="pill-row-balance items-center gap-1.5">
                {ruleCategories.map((cat) => {
                  const active = ruleCategoryFilter === cat;
                  return (
                    <button
                      key={cat}
                      type="button"
                      onClick={() => setRuleCategoryFilter(cat)}
                      className={`px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all cursor-pointer uppercase ${
                        active
                          ? 'bg-blue-600 text-white border-blue-500 shadow-xs'
                          : 'bg-[var(--gl)] text-[var(--mu)] border-[var(--ln)] hover:text-[var(--tx)]'
                      }`}
                    >
                      {cat === 'ALL' ? 'All Rule Categories' : `#${cat}`}
                    </button>
                  );
                })}
              </div>

              <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-[var(--input-bg)] border border-[var(--input-border)] min-w-[240px]">
                <Search size={14} className="text-[var(--mu)] shrink-0" />
                <input
                  type="search"
                  value={ruleSearch}
                  onChange={(e) => setRuleSearch(e.target.value)}
                  placeholder="Search editorial lessons..."
                  className="w-full bg-transparent text-xs outline-none text-[var(--tx)] placeholder:text-[var(--mu)]"
                />
                {ruleSearch && (
                  <button
                    type="button"
                    onClick={() => setRuleSearch('')}
                    className="text-[var(--mu)] hover:text-red-500 cursor-pointer"
                  >
                    <X size={13} />
                  </button>
                )}
              </div>
            </search>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
              {/* Left (7/12): Self-Healing Reflexion Guardrail Cards */}
              <div className="lg:col-span-7 glass-panel p-5 space-y-3.5">
                <div className="flex items-center justify-between pb-3 border-b border-[var(--ln-subtle)]">
                  <div className="flex items-center gap-2">
                    <Brain size={16} className="text-emerald-600 dark:text-emerald-400" />
                    <div>
                      <h2 className="text-sm font-bold text-[var(--tx)]">
                        Self-Healing Reflexion Guardrails
                      </h2>
                      <p className="text-[11px] text-[var(--mu)]">
                        Mistakes caught in QC1 or Auto-Critic are permanently injected into future planner prompts
                      </p>
                    </div>
                  </div>
                  <Badge variant="success">{filteredRules.length} Rules</Badge>
                </div>

                {filteredRules.length === 0 ? (
                  <div className="p-8 text-center text-xs text-[var(--mu)]">
                    No Reflexion rules match this filter yet. Timeline edits and auto-critic catches populate here automatically.
                  </div>
                ) : (
                  <div className="scroll-panel-stable space-y-3 max-h-[560px] pr-1">
                    {filteredRules.map((rule, i) => (
                      <div key={i} className="glass-subcard p-4 space-y-2.5">
                        <div className="flex items-center justify-between gap-2">
                          <div className="flex items-center gap-2">
                            <span className="w-6 h-6 rounded-lg bg-emerald-500/15 border border-emerald-500/30 text-emerald-600 dark:text-emerald-400 flex items-center justify-center">
                              <ShieldCheck size={13} />
                            </span>
                            <Badge variant="info">#{rule.category}</Badge>
                          </div>
                          <span className="text-[11px] font-mono font-bold text-amber-600 dark:text-amber-400">
                            Prevented {rule.occurrences}x
                          </span>
                        </div>

                        <p className="text-xs text-[var(--tx)] font-medium leading-relaxed">
                          {rule.lesson}
                        </p>

                        <Progress
                          value={Number(rule.occurrences || 1)}
                          max={maxRuleHits}
                          color="var(--ok)"
                          label={`Rule recurrence weight ${rule.occurrences}`}
                        />

                        {rule.context_topic && (
                          <div className="text-[11px] text-[var(--mu)] font-mono flex items-center gap-1.5">
                            <FileText size={11} />
                            <span>Origin context: {rule.context_topic}</span>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Right (5/12): Chronological Director Production Log */}
              <div className="lg:col-span-5 glass-panel p-5 space-y-3.5">
                <div className="flex items-center justify-between pb-3 border-b border-[var(--ln-subtle)]">
                  <div>
                    <h2 className="text-sm font-bold text-[var(--tx)]">
                      Director Production Audit Trail
                    </h2>
                    <p className="text-[11px] text-[var(--mu)]">
                      Recent render milestones &amp; verification checkpoints
                    </p>
                  </div>
                  <Badge variant="neutral">{vaultJobs.length} Logged</Badge>
                </div>

                {vaultJobs.length === 0 ? (
                  <div className="p-6 text-center text-xs text-[var(--mu)]">
                    No completed production logs yet.
                  </div>
                ) : (
                  <div className="scroll-panel-stable space-y-2.5 max-h-[560px] pr-1">
                    {vaultJobs.slice(0, 12).map((job: any) => {
                      const videoAsset = job.assets?.find(
                        (a: any) => a.type === 'VIDEO' || a.type === 'video'
                      );
                      const hasDossier = Boolean(videoAsset?.metadata?.fact_dossier);
                      const createdStr = job.created_at
                        ? new Date(job.created_at).toLocaleString([], {
                            month: 'short',
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit'
                          })
                        : 'Recent';

                      return (
                        <div
                          key={job.id}
                          onClick={() => navigate(`/qc1/${job.id}`)}
                          className="glass-subcard p-3 cursor-pointer flex items-start justify-between gap-3 group"
                        >
                          <div className="flex items-start gap-2.5 min-w-0">
                            <span className="w-6 h-6 rounded-lg bg-blue-600/15 text-blue-600 dark:text-blue-400 border border-blue-500/25 flex items-center justify-center shrink-0 mt-0.5">
                              <CheckCircle2 size={13} />
                            </span>
                            <div className="min-w-0">
                              <div className="text-xs font-bold text-[var(--tx)] group-hover:text-blue-600 dark:group-hover:text-blue-400 truncate">
                                #{job.id} · {job.niche}
                              </div>
                              <div className="text-[11px] text-[var(--mu)] font-mono mt-0.5">
                                {job.config?.format || '9:16'} · {(job.config?.genre || 'crime_doc').replace('_', ' ')} · {createdStr}
                              </div>
                              {hasDossier && (
                                <span className="inline-block mt-1 text-[10px] font-semibold text-emerald-600 dark:text-emerald-400">
                                  Wikipedia Fact Dossier Verified
                                </span>
                              )}
                            </div>
                          </div>
                          <ArrowRight
                            size={13}
                            className="text-[var(--mu)] group-hover:text-blue-500 shrink-0 mt-1"
                          />
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* =================================================================== */}
      {/* TAB 3: 5-HOUSE KNOWLEDGE MATRIX                                     */}
      {/* =================================================================== */}
      <div
        role="tabpanel"
        aria-label="5-House Knowledge Matrix"
        hidden={activeTab !== '5-House Knowledge Matrix'}
      >
        {activeTab === '5-House Knowledge Matrix' && (
          <div className="space-y-5">
            {/* Truthful Harvester Control Bar */}
            <div className="glass-panel p-4 flex flex-col md:flex-row md:items-center justify-between gap-3">
              <div className="space-y-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <Radio
                    size={14}
                    className={isHarvesterLive ? 'text-emerald-500 animate-pulse' : 'text-[var(--mu)]'}
                  />
                  <span className="text-xs font-bold text-[var(--tx)]">
                    5-House Dataset Harvester Telemetry
                  </span>
                  <Badge
                    variant={
                      isAtMilestone
                        ? 'warning'
                        : isPausedForRender
                        ? 'warning'
                        : isHarvesterLive
                        ? 'success'
                        : 'neutral'
                    }
                  >
                    {isAtMilestone
                      ? 'CHECKPOINT REACHED'
                      : isPausedForRender
                      ? 'PAUSED FOR RENDER'
                      : isHarvesterLive
                      ? 'LIVE HARVESTING'
                      : 'IDLE'}
                  </Badge>
                  <span className="text-[11px] font-mono text-[var(--mu)]">
                    {qData ? totalRecords.toLocaleString() : '--'} /{' '}
                    {masterTarget > 0 ? masterTarget.toLocaleString() : '--'} total target
                  </span>
                </div>
                {lastHarvested && (
                  <div className="text-[11px] text-[var(--mu)] truncate max-w-3xl">
                    Latest record: <b className="text-[var(--tx)]">{lastHarvested.house}</b> /{' '}
                    {lastHarvested.sub_room} · "{lastHarvested.preview}"
                  </div>
                )}
              </div>

              {isAtMilestone && (
                <Button
                  type="button"
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

            {/* 5-House ProgressRing Bento Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {Object.entries(houses).map(([houseKey, houseVal]: [string, any], hIdx) => {
                const count = houseVal?.count ?? 0;
                const housePhaseTarget = Math.max(1, Math.round(milestoneCap / 5));
                const masterHouseTarget = houseVal?.target ?? housePhaseTarget;
                const isFull = houseVal?.status === 'FULL' || (masterHouseTarget > 0 && count >= masterHouseTarget);
                const subRooms = houseVal?.sub_rooms || {};
                const title = houseKey.replace(/^HOUSE_\d+_/, '').replace(/_/g, ' ');

                return (
                  <div key={houseKey} className="glass-panel p-5 flex flex-col justify-between gap-4">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-[10px] font-bold px-2 py-0.5 rounded-md bg-blue-600/15 text-blue-600 dark:text-blue-400 border border-blue-500/30">
                            H0{hIdx + 1}
                          </span>
                          <Badge variant={isFull ? 'warning' : 'success'}>
                            {isFull ? 'FULL' : 'OPEN'}
                          </Badge>
                        </div>
                        <h3 className="text-sm font-bold uppercase tracking-wide text-[var(--tx)] mt-2 truncate">
                          {title}
                        </h3>
                        <div className="font-mono text-xs text-[var(--mu)] mt-1">
                          <b className="text-base text-[var(--tx)]">{count.toLocaleString()}</b> /{' '}
                          {housePhaseTarget.toLocaleString()} phase cap
                        </div>
                      </div>

                      <ProgressRing
                        value={count}
                        max={housePhaseTarget}
                        size={56}
                        color={isFull ? 'var(--wa)' : 'var(--ac)'}
                        label={`${title} phase quota progress`}
                      />
                    </div>

                    {Object.keys(subRooms).length > 0 && (
                      <div className="pt-3 border-t border-[var(--ln-subtle)] pill-row-balance gap-1.5">
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
          </div>
        )}
      </div>

      {/* Native Confirm Dialogs */}
      <ConfirmDialog
        isOpen={isConfirmClearOpen}
        title="Clear All Archived Videos?"
        description="This clears all rendered job records from the Director Vault while keeping your 5-House training dataset and Reflexion rules intact."
        confirmLabel="Clear Archive"
        onConfirm={() => {
          setIsConfirmClearOpen(false);
          clearAllMutation.mutate();
        }}
        onCancel={() => setIsConfirmClearOpen(false)}
      />

      <ConfirmDialog
        isOpen={Boolean(jobPendingDelete)}
        title={jobPendingDelete ? `Delete Master #${jobPendingDelete.id}?` : 'Delete Master?'}
        description={
          jobPendingDelete
            ? `Remove "${jobPendingDelete.niche}" from the Director Vault?`
            : 'Remove this video from the Director Vault?'
        }
        confirmLabel="Delete Video"
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
