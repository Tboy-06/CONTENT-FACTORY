import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  useJobs,
  useCacheStatus,
  useClearCache,
  useDeleteJob,
  useHouseQuotas,
  useContinueHarvesterMilestone,
  useLearnedRules,
  useCreateInstantJob,
  useSpend,
  useOpenRouterCapabilities
} from '../api/client';
import { Button, ConfirmDialog, Progress, ProgressRing } from '../components/ui';
import {
  Trash2,
  Search,
  X,
  Plus,
  ChevronRight,
  Download,
  FileText,
  AlertTriangle,
  RefreshCw,
  CheckCircle2,
  ArrowRight,
  Cpu,
  ShieldCheck,
  Play
} from 'lucide-react';
import type { StudioTheme } from '../App';

interface DashboardProps {
  theme?: StudioTheme;
  globalSearch?: string;
}

const FILTER_PILLS = [
  { id: 'all', label: 'All Jobs' },
  { id: 'crime_doc', label: 'Crime Doc' },
  { id: 'viral_edu', label: 'Viral Edu' },
  { id: 'movie_cinema', label: 'Movie Cinema' },
  { id: 'action_hype', label: 'Action Hype' },
  { id: 'comedy_skit', label: 'Comedy Skit' },
  { id: '9:16', label: '9:16 Shorts' },
  { id: '16:9', label: '16:9 Long-Form' },
  { id: 'ready', label: 'Ready to Publish' }
];

export default function Dashboard({ theme = 'light-glass', globalSearch = '' }: DashboardProps) {
  const navigate = useNavigate();
  const { data: jobs = [], refetch: refetchJobs } = useJobs();
  const { data: cache } = useCacheStatus();
  const { data: houseQuotas } = useHouseQuotas();
  const { data: learnedRulesData } = useLearnedRules();
  const { data: liveSpend } = useSpend();
  const { data: openRouterCaps } = useOpenRouterCapabilities();
  const clearCacheMutation = useClearCache();
  const deleteJobMutation = useDeleteJob();
  const createInstantMutation = useCreateInstantJob();
  const continueMilestoneMutation = useContinueHarvesterMilestone();
  const initialRecordCountRef = useRef<number | null>(null);

  const [activeFilter, setActiveFilter] = useState<string>('all');
  const [localSearch, setLocalSearch] = useState<string>('');
  const [hoveredHouseIdx, setHoveredHouseIdx] = useState<number>(1);
  const [quickTopic, setQuickTopic] = useState<string>('');
  const [quickGenre, setQuickGenre] = useState<string>('crime_doc');
  const [jobPendingDelete, setJobPendingDelete] = useState<any | null>(null);

  useEffect(() => {
    setLocalSearch(globalSearch);
  }, [globalSearch]);

  useEffect(() => {
    const handler = (e: any) => setLocalSearch(e.detail || '');
    window.addEventListener('cf-global-search', handler);
    return () => window.removeEventListener('cf-global-search', handler);
  }, []);

  const activeJobs = jobs.filter(
    (j: any) =>
      (j.status === 'RUNNING' || j.status === 'PENDING' || j.status === 'QUEUED') &&
      j.current_stage !== 'QC1' &&
      j.current_stage !== 'PUBLISHED' &&
      j.current_stage !== 'COMPLETED'
  );
  const qcJobs = jobs.filter(
    (j: any) =>
      j.status === 'AWAITING_APPROVAL' ||
      j.current_stage === 'QC1' ||
      j.current_stage === 'READY_TO_PUBLISH'
  );
  const recentJobs = jobs
    .filter(
      (j: any) =>
        j.status === 'COMPLETED' ||
        j.status === 'PUBLISHED' ||
        j.current_stage === 'QC1' ||
        j.current_stage === 'READY_TO_PUBLISH' ||
        j.assets?.some((a: any) => a.type === 'VIDEO' || a.type === 'video')
    )
    .slice(0, 8);

  // ============================================================================
  // CLASSIC REVERT VIEW (1-Click exact previous UI when user selects "Classic")
  // ============================================================================
  if (theme === 'classic-dark') {
    return (
      <div className="animate-in fade-in min-h-full flex flex-col pb-8">
        <div className="flex justify-between items-center flex-wrap gap-3 mb-6 shrink-0">
          <div>
            <h1 className="text-xl font-semibold tracking-tight text-white">Pipeline Dashboard</h1>
            <div className="text-slate-400 text-xs mt-1">
              Real-time job queue, quality review approvals, and local cache monitoring.
            </div>
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
          <div className="glass-panel p-6 text-center text-[var(--mu)]">No finished videos yet.</div>
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
                  <div className="text-[12px] text-[var(--mu)]">
                    Finished {new Date(job.created_at || Date.now()).toLocaleDateString()}
                  </div>
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
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      setJobPendingDelete(job);
                    }}
                    className="p-1.5 rounded hover:bg-red-500/20 text-slate-400 hover:text-red-400 transition-colors cursor-pointer"
                    title="Delete Job"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
        <ConfirmDialog
          isOpen={Boolean(jobPendingDelete)}
          title={jobPendingDelete ? `Delete Video #${jobPendingDelete.id}?` : 'Delete Video?'}
          description={
            jobPendingDelete
              ? `Remove "${jobPendingDelete.niche}" from the production studio history?`
              : 'Remove this video from the production studio history?'
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

  // ============================================================================
  // FROSTED ACRYLIC / DARK OBSIDIAN GLASS STUDIO VIEW (100% REAL-TIME, ZERO HARDCODED STATS)
  // ============================================================================
  const isLight = theme === 'light-glass';
  const qData = houseQuotas?.data;
  const totalHarvesterRecords = qData?.total_records ?? 0;
  const targetHarvesterRecords = qData?.target_total ?? 0;
  const currentMilestoneCap = qData?.current_milestone_cap ?? 0;
  const milestoneStep = qData?.milestone_step ?? 1;
  const milestoneStatus = qData?.milestone_status ?? 'IDLE';
  const isHarvesterLive = Boolean(qData?.harvester_active);
  const isPausedForRender = Boolean(qData?.render_lock_active) || milestoneStatus === 'PAUSED_FOR_ACTIVE_RENDER';
  const lastHarvestedItem = qData?.last_harvested_item ?? null;
  const formatCompactCount = (n: number) =>
    n >= 1_000_000 ? `${(n / 1_000_000).toFixed(n % 1_000_000 === 0 ? 0 : 1)}M` : n >= 1_000 ? `${Math.round(n / 1_000)}k` : String(n);
  const housesMap = qData?.houses || {};
  const learnedRules = learnedRulesData?.rules || [];

  if (initialRecordCountRef.current === null && totalHarvesterRecords > 0) {
    initialRecordCountRef.current = totalHarvesterRecords;
  }
  const sessionDelta =
    initialRecordCountRef.current !== null
      ? Math.max(0, totalHarvesterRecords - initialRecordCountRef.current)
      : 0;

  // Per-house phase milestone target computed live from backend checkpoint cap
  const houseMilestoneTarget = Math.max(1, Math.round(currentMilestoneCap / 5));

  const houseDefs = [
    { key: 'HOUSE_1_HOOK_PSYCHOLOGY', id: 'HOUSE_1', short: 'HOUSE_1', name: 'Hook Psychology' },
    { key: 'HOUSE_2_SCREENWRITER_ARC', id: 'HOUSE_2', short: 'HOUSE_2', name: 'Screenwriter Arc' },
    { key: 'HOUSE_3_VISUAL_DIRECTOR', id: 'HOUSE_3', short: 'HOUSE_3', name: 'Visual Director' },
    { key: 'HOUSE_4_SOUND_AND_CUT_EDITOR', id: 'HOUSE_4', short: 'HOUSE_4', name: 'Sound & Cut Editor' },
    { key: 'HOUSE_5_COPILOT_AND_REFLEXION', id: 'HOUSE_5', short: 'HOUSE_5', name: 'Copilot & Reflexion' }
  ];

  const houseChartData = houseDefs.map((hd) => {
    const liveCount = housesMap?.[hd.key]?.count ?? 0;
    const masterHouseTarget = housesMap?.[hd.key]?.target ?? 0;
    const openSubRooms = Object.values(housesMap?.[hd.key]?.sub_rooms || {}).filter(
      (sr: any) => sr?.status === 'OPEN'
    ).length;
    const phasePct =
      currentMilestoneCap > 0
        ? Math.min(100, Number(((liveCount / houseMilestoneTarget) * 100).toFixed(1)))
        : 0;
    return {
      ...hd,
      count: liveCount,
      masterTarget: masterHouseTarget,
      phaseTarget: houseMilestoneTarget,
      openSubRooms,
      retention: phasePct
    };
  });

  const maxHouseCount = Math.max(...houseChartData.map((h) => h.count), 100);

  // Filter jobs based on segmented filter pill + search query
  const filteredJobs = jobs.filter((j: any) => {
    const q = localSearch.trim().toLowerCase();
    const matchesSearch =
      !q ||
      (j.niche || '').toLowerCase().includes(q) ||
      String(j.id).includes(q) ||
      (j.current_stage || '').toLowerCase().includes(q);
    if (!matchesSearch) return false;

    if (activeFilter === 'all') return true;
    const cfg = j.config || {};
    if (activeFilter === '9:16') return (cfg.format || '9:16') === '9:16';
    if (activeFilter === '16:9') return cfg.format === '16:9';
    if (activeFilter === 'ready') {
      return (
        j.current_stage === 'QC1' ||
        j.current_stage === 'READY_TO_PUBLISH' ||
        j.status === 'COMPLETED'
      );
    }
    return (cfg.genre || 'crime_doc') === activeFilter || (j.niche || '').toLowerCase().includes(activeFilter.replace('_', ' '));
  });

  const latestExportableJob = recentJobs[0] || jobs[0];

  const handleExportZip = () => {
    if (!latestExportableJob) {
      navigate('/create');
      return;
    }
    window.open(`/api/jobs/${latestExportableJob.id}/export`, '_blank');
  };

  const handleQuickLaunch = () => {
    const topicToRun = quickTopic.trim();
    if (!topicToRun) {
      navigate('/create');
      return;
    }
    createInstantMutation.mutate(
      {
        topic: topicToRun,
        genre: quickGenre,
        aspect_ratio: '9:16',
        duration: '45s',
        style_preset: 'Dark Documentary',
        voice: 'en-US-AndrewMultilingualNeural'
      },
      {
        onSuccess: () => {
          setQuickTopic('');
          refetchJobs();
        }
      }
    );
  };

  return (
    <div className="animate-in fade-in flex flex-col gap-5 pb-4">
      {/* 02 | SEGMENTED FILTER PILL BAR */}
      <search aria-label="Filter pipeline jobs" className="flex items-center justify-between flex-wrap gap-2.5">
        <div className="pill-row-balance items-center gap-2">
          {FILTER_PILLS.map((pill) => {
            const isSelected = activeFilter === pill.id;
            return (
              <button
                key={pill.id}
                onClick={() => setActiveFilter(pill.id)}
                className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all cursor-pointer border ${
                  isSelected
                    ? 'bg-blue-600 text-white border-blue-500 shadow-md shadow-blue-600/25'
                    : isLight
                    ? 'bg-white/75 text-slate-700 border-white hover:bg-white shadow-2xs'
                    : 'bg-slate-900/75 text-slate-300 border-slate-700/80 hover:bg-slate-800'
                }`}
              >
                {pill.label}
              </button>
            );
          })}
        </div>

        {/* Right Quick Search / Reset Pill */}
        <div
          className={`flex items-center gap-2 px-3 py-1.5 rounded-xl border text-xs ${
            isLight
              ? 'bg-white/75 border-white text-slate-600 shadow-2xs'
              : 'bg-slate-900/75 border-slate-700/80 text-slate-300'
          }`}
        >
          <Search size={13} className="text-slate-400" />
          <input
            type="text"
            value={localSearch}
            onChange={(e) => setLocalSearch(e.target.value)}
            placeholder="Filter table..."
            className="w-24 bg-transparent text-xs outline-none placeholder:text-slate-400"
          />
          {(localSearch || activeFilter !== 'all') && (
            <button
              onClick={() => {
                setLocalSearch('');
                setActiveFilter('all');
              }}
              className="hover:text-red-500 transition-colors cursor-pointer"
              title="Reset filters"
            >
              <X size={13} />
            </button>
          )}
        </div>
      </search>

      {/* 03 | UNIFIED 3-ZONE KPI BANNER */}
      <div className="glass-panel p-5 flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-5">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 flex-1">
          {/* Zone 1: Harvester Dataset (Live Dynamic Target & Checkpoints) */}
          <div className="flex items-center justify-between gap-3">
            <div className="flex flex-col justify-between min-w-0">
              <div className="flex items-center gap-2">
                <span className={`text-[11px] font-bold uppercase tracking-wider ${isLight ? 'text-slate-500' : 'text-slate-400'}`}>
                  Harvester Dataset {targetHarvesterRecords > 0 ? `(${formatCompactCount(targetHarvesterRecords)} Target)` : ''}
                </span>
                {sessionDelta > 0 && (
                  <span className="px-2 py-0.5 rounded-md text-[10px] font-bold bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30 animate-pulse">
                    +{sessionDelta} live
                  </span>
                )}
              </div>
              <div className="flex items-baseline gap-1.5 mt-1 flex-wrap">
                <span className={`text-3xl font-extrabold tracking-tight tabular-nums ${isLight ? 'text-slate-900' : 'text-white'}`}>
                  {qData ? totalHarvesterRecords.toLocaleString() : '--'}
                </span>
                <span className={`text-sm font-semibold tabular-nums ${isLight ? 'text-slate-500' : 'text-slate-400'}`}>
                  / {targetHarvesterRecords > 0 ? targetHarvesterRecords.toLocaleString() : '--'}
                </span>
              </div>
              <div className="flex items-center gap-2 mt-1 flex-wrap">
                <span className={`text-[11px] font-medium ${isLight ? 'text-slate-500' : 'text-slate-400'}`}>
                  Phase {currentMilestoneCap > 0 ? Math.max(1, Math.round(currentMilestoneCap / Math.max(1, milestoneStep))) : '--'} Checkpoint:{' '}
                  <b>{currentMilestoneCap > 0 ? currentMilestoneCap.toLocaleString() : '--'}</b>
                </span>
                {(milestoneStatus === 'PAUSED_AT_100K_CHECKPOINT' || (currentMilestoneCap > 0 && totalHarvesterRecords >= currentMilestoneCap)) && (
                  <button
                    type="button"
                    onClick={() => continueMilestoneMutation.mutate()}
                    disabled={continueMilestoneMutation.isPending}
                    className="px-2 py-0.5 rounded-md bg-blue-600 text-white text-[10px] font-bold hover:bg-blue-500 cursor-pointer"
                  >
                    {continueMilestoneMutation.isPending ? 'Advancing...' : 'Continue Next Milestone'}
                  </button>
                )}
              </div>
            </div>
            <ProgressRing
              value={totalHarvesterRecords}
              max={Math.max(1, currentMilestoneCap || 100000)}
              size={50}
              color="var(--ac)"
              label="Harvester phase checkpoint progress"
            />
          </div>

          {/* Zone 2: API Spend & Quota (Live from /api/jobs/spend & /api/copilot/openrouter-capabilities) */}
          <div
            className={`flex flex-col justify-between md:border-l md:pl-6 ${
              isLight ? 'border-slate-300/60' : 'border-slate-700/60'
            }`}
          >
            <span className={`text-[11px] font-bold uppercase tracking-wider ${isLight ? 'text-slate-500' : 'text-slate-400'}`}>
              API Spend &amp; Quota
            </span>
            <div className="flex items-baseline gap-2 mt-1">
              <span className={`text-3xl font-extrabold tracking-tight tabular-nums ${isLight ? 'text-slate-900' : 'text-white'}`}>
                ${(liveSpend ?? 0).toFixed(2)}
              </span>
              <span className="px-2 py-0.5 rounded-md text-[10px] font-bold uppercase bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30">
                {(liveSpend ?? 0) === 0 ? 'Strictly Free' : 'Metered'}
              </span>
            </div>
            <span className={`text-[11px] mt-1 font-medium ${isLight ? 'text-slate-500' : 'text-slate-400'}`}>
              {openRouterCaps
                ? `${openRouterCaps.catalog_strictly_free_count} live :free cloud models · Local Spark ready`
                : 'Double-Lock $0 Guard · Polling live catalog...'}
            </span>
          </div>

          {/* Zone 3: Pending Approvals & Active Queue */}
          <div
            className={`flex flex-col justify-between md:border-l md:pl-6 ${
              isLight ? 'border-slate-300/60' : 'border-slate-700/60'
            }`}
          >
            <span className={`text-[11px] font-bold uppercase tracking-wider ${isLight ? 'text-slate-500' : 'text-slate-400'}`}>
              Pending Approvals
            </span>
            <div className="flex items-baseline gap-2 mt-1">
              <span className={`text-3xl font-extrabold tracking-tight tabular-nums ${isLight ? 'text-slate-900' : 'text-white'}`}>
                {qcJobs.length}
              </span>
              <span className={`text-sm font-semibold ${isLight ? 'text-slate-600' : 'text-slate-300'}`}>
                Awaiting QC1
              </span>
            </div>
            <span className={`text-[11px] mt-1 font-medium ${isLight ? 'text-slate-500' : 'text-slate-400'}`}>
              {activeJobs.length} encoding in queue · {cache?.output_count ?? recentJobs.length} finished renders
            </span>
          </div>
        </div>

        {/* Right Action Cluster */}
        <div className="flex lg:flex-col items-center lg:items-end justify-between gap-3 shrink-0">
          <button
            onClick={() => {
              if (qcJobs.length > 0) navigate(`/qc1/${qcJobs[0].id}`);
              else if (recentJobs.length > 0) navigate(`/qc1/${recentJobs[0].id}`);
              else navigate('/pipeline');
            }}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-xl text-xs font-semibold border transition-all cursor-pointer ${
              isLight
                ? 'bg-white/90 hover:bg-white text-slate-800 border-white shadow-xs'
                : 'bg-slate-800 hover:bg-slate-700 text-slate-100 border-slate-700'
            }`}
          >
            <span className="w-2 h-2 rounded-xs bg-red-500" />
            <span>Inspect Studio QC1</span>
            <ArrowRight size={13} />
          </button>

          <div className="flex items-center gap-2">
            <button
              onClick={() => refetchJobs()}
              className={`w-8 h-8 rounded-xl border flex items-center justify-center transition-colors cursor-pointer ${
                isLight
                  ? 'bg-white/80 hover:bg-white border-white text-slate-700 shadow-2xs'
                  : 'bg-slate-800 hover:bg-slate-700 border-slate-700 text-slate-300'
              }`}
              title="Refresh Job Queue"
            >
              <RefreshCw size={13} />
            </button>
            <button
              onClick={() => navigate('/create')}
              className={`w-8 h-8 rounded-xl border flex items-center justify-center transition-colors cursor-pointer ${
                isLight
                  ? 'bg-white/80 hover:bg-white border-white text-slate-700 shadow-2xs'
                  : 'bg-slate-800 hover:bg-slate-700 border-slate-700 text-slate-300'
              }`}
              title="Create New Documentary"
            >
              <Plus size={14} />
            </button>
            <div
              onClick={() => navigate('/pipeline')}
              className="w-8 h-8 rounded-xl bg-red-600 text-white font-bold text-xs flex items-center justify-center shadow-sm cursor-pointer"
              title="Jobs ready for QC1 or active"
            >
              {qcJobs.length + activeJobs.length}
            </div>
          </div>
        </div>
      </div>

      {/* 04 | 3-COLUMN IRIDESCENT FEATURE CARDS */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {/* Card 1: CRIME / CIA DOC */}
        <div
          onClick={() => setActiveFilter(activeFilter === 'crime_doc' ? 'all' : 'crime_doc')}
          className={`iridescent-card-crime rounded-2xl p-5 text-white flex flex-col justify-between min-h-[156px] cursor-pointer transition-all hover:-translate-y-0.5 relative overflow-hidden ${
            activeFilter === 'crime_doc' ? 'ring-2 ring-cyan-300' : ''
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="px-2.5 py-0.5 rounded-lg bg-white/15 backdrop-blur-md text-[10px] font-bold uppercase tracking-wider border border-white/25">
              {activeFilter === 'crime_doc' ? 'Active Filter · 18-24 cpm' : '18-24 cuts/min · hard_bw'}
            </span>
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                navigate('/create?genre=crime_doc');
              }}
              className="w-7 h-7 rounded-lg bg-emerald-500 text-white flex items-center justify-center shadow-sm hover:bg-emerald-400 cursor-pointer"
              title="Launch Crime / CIA Documentary in Production Deck"
            >
              <Plus size={15} />
            </button>
          </div>

          <div className="my-2">
            <div className="w-9 h-6 rounded-md bg-gradient-to-br from-amber-200/80 to-amber-400/70 border border-white/50 mb-2 flex items-center justify-center">
              <div className="w-5 h-3 border border-slate-900/30 rounded-2xs" />
            </div>
            <h3 className="text-base font-extrabold tracking-wide uppercase">CRIME / CIA DOC</h3>
            <p className="text-[11px] text-sky-100/80 mt-0.5">
              Forensic dossier scans, redacted highlighters &amp; tactical radar maps
            </p>
          </div>

          <div className="flex items-center justify-between pt-1">
            <span className="font-mono text-[11px] text-sky-200/90">
              {(housesMap?.HOUSE_2_SCREENWRITER_ARC?.sub_rooms?.crime_doc?.count ?? 0).toLocaleString()} records · H2
            </span>
            <span className="px-3 py-0.5 rounded-lg bg-white text-slate-900 font-bold text-[11px] shadow-xs">
              {jobs.filter((j: any) => (j.config?.genre || 'crime_doc') === 'crime_doc').length} Jobs
            </span>
          </div>
        </div>

        {/* Card 2: VIRAL EDU */}
        <div
          onClick={() => setActiveFilter(activeFilter === 'viral_edu' ? 'all' : 'viral_edu')}
          className={`iridescent-card-edu rounded-2xl p-5 text-white flex flex-col justify-between min-h-[156px] cursor-pointer transition-all hover:-translate-y-0.5 relative overflow-hidden ${
            activeFilter === 'viral_edu' ? 'ring-2 ring-teal-200' : ''
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="px-2.5 py-0.5 rounded-lg bg-white/15 backdrop-blur-md text-[10px] font-bold uppercase tracking-wider border border-white/25">
              {activeFilter === 'viral_edu' ? 'Active Filter · 28-38 cpm' : '28-38 cuts/min · teal_split'}
            </span>
            <span className="px-2.5 py-0.5 rounded-lg bg-black/25 text-[11px] font-bold uppercase tracking-wider">
              Explainer
            </span>
          </div>

          <div className="my-2">
            <div className="w-9 h-6 rounded-md bg-gradient-to-br from-cyan-100/85 to-teal-300/75 border border-white/50 mb-2 flex items-center justify-center">
              <div className="w-5 h-3 border border-slate-900/30 rounded-2xs" />
            </div>
            <h3 className="text-base font-extrabold tracking-wide uppercase">VIRAL EDU</h3>
            <p className="text-[11px] text-teal-50/90 mt-0.5">
              Verified stat counters, workflow steppers &amp; cosine focus punch-ins
            </p>
          </div>

          <div className="flex items-center justify-between pt-1">
            <span className="font-mono text-[11px] text-teal-100/90">
              {(housesMap?.HOUSE_2_SCREENWRITER_ARC?.sub_rooms?.viral_edu?.count ?? 0).toLocaleString()} records · H2
            </span>
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                navigate('/create?genre=viral_edu');
              }}
              className="w-7 h-7 rounded-lg bg-white/20 hover:bg-white/30 border border-white/40 flex items-center justify-center cursor-pointer"
              title="Launch Viral Edu Documentary in Production Deck"
            >
              <ChevronRight size={15} />
            </button>
          </div>
        </div>

        {/* Card 3: MOVIE CINEMA */}
        <div
          onClick={() => setActiveFilter(activeFilter === 'movie_cinema' ? 'all' : 'movie_cinema')}
          className={`iridescent-card-cinema rounded-2xl p-5 text-white flex flex-col justify-between min-h-[156px] cursor-pointer transition-all hover:-translate-y-0.5 relative overflow-hidden ${
            activeFilter === 'movie_cinema' ? 'ring-2 ring-amber-200' : ''
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="px-2.5 py-0.5 rounded-lg bg-white/15 backdrop-blur-md text-[10px] font-bold uppercase tracking-wider border border-white/25">
              {activeFilter === 'movie_cinema' ? 'Active Filter · 12-18 cpm' : '12-18 cuts/min · cinema_scope'}
            </span>
            <span className="px-2.5 py-0.5 rounded-lg bg-white/20 text-[11px] font-bold uppercase tracking-wider">
              2.35:1
            </span>
          </div>

          <div className="my-2">
            <div className="w-9 h-6 rounded-md bg-gradient-to-br from-amber-100/90 to-orange-300/80 border border-white/50 mb-2 flex items-center justify-center">
              <div className="w-5 h-3 border border-slate-900/30 rounded-2xs" />
            </div>
            <h3 className="text-base font-extrabold tracking-wide uppercase">MOVIE CINEMA</h3>
            <p className="text-[11px] text-amber-50/90 mt-0.5">
              35mm Kodak grain emulation, anamorphic bars &amp; orbital depth shifts
            </p>
          </div>

          <div className="flex items-center justify-between pt-1">
            <span className="font-mono text-[11px] text-amber-100/90">
              {(housesMap?.HOUSE_2_SCREENWRITER_ARC?.sub_rooms?.movie_cinema?.count ?? 0).toLocaleString()} records · H2
            </span>
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                navigate('/create?genre=movie_cinema');
              }}
              className="w-7 h-7 rounded-lg bg-white text-slate-900 flex items-center justify-center shadow-xs hover:bg-amber-50 cursor-pointer"
              title="Launch Movie Cinema Documentary in Production Deck"
            >
              <Plus size={15} />
            </button>
          </div>
        </div>
      </div>

      {/* MIDDLE ROW (2/3 Combo Bar & Spline Chart + 1/3 Tactile Action Stack) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* 05 | COMBO BAR & SPLINE CHART CARD (Left 2/3) */}
        <div className="glass-panel p-5 lg:col-span-2 flex flex-col justify-between">
          <div className="flex items-center justify-between gap-2 mb-4 flex-wrap">
            <div>
              <h2 className={`text-sm font-bold tracking-tight ${isLight ? 'text-slate-900' : 'text-white'}`}>
                5-House Live Harvester Volume &amp; Phase {Math.round(currentMilestoneCap / milestoneStep)} Progress ({currentMilestoneCap.toLocaleString()} / {targetHarvesterRecords.toLocaleString()})
              </h2>
              <p className={`text-[11px] ${isLight ? 'text-slate-500' : 'text-slate-400'}`}>
                {lastHarvestedItem
                  ? `Latest record [${lastHarvestedItem.house.replace('HOUSE_', 'H').split('_')[0]} · ${lastHarvestedItem.sub_room}]: "${lastHarvestedItem.preview}"`
                  : 'Live telemetry synced from workspace harvest state (0 hardcoded values)'}
              </p>
            </div>
            <div className="flex items-center gap-2">
              {currentMilestoneCap < targetHarvesterRecords && (
                <button
                  type="button"
                  onClick={() => continueMilestoneMutation.mutate()}
                  disabled={continueMilestoneMutation.isPending}
                  className={`px-2.5 py-1 rounded-xl text-[10px] font-bold border cursor-pointer transition-colors ${
                    isLight
                      ? 'bg-white/80 hover:bg-white text-blue-700 border-blue-200'
                      : 'bg-slate-800 hover:bg-slate-700 text-blue-300 border-slate-700'
                  }`}
                  title={`Advance checkpoint cap by +${milestoneStep.toLocaleString()} towards ${targetHarvesterRecords.toLocaleString()}`}
                >
                  +{formatCompactCount(milestoneStep)} Cap ({Math.min(targetHarvesterRecords, currentMilestoneCap + milestoneStep).toLocaleString()})
                </button>
              )}
              {milestoneStatus === 'PAUSED_AT_100K_CHECKPOINT' ? (
                <div className="flex items-center gap-1.5 px-3 py-1 rounded-xl bg-amber-500/15 border border-amber-500/30 text-amber-700 dark:text-amber-300 text-[11px] font-bold">
                  <span className="w-2 h-2 rounded-xs bg-amber-500" />
                  <span>Checkpoint Reached</span>
                </div>
              ) : isPausedForRender ? (
                <div className="flex items-center gap-1.5 px-3 py-1 rounded-xl bg-amber-500/15 border border-amber-500/30 text-amber-700 dark:text-amber-300 text-[11px] font-bold">
                  <span className="w-2 h-2 rounded-xs bg-amber-500" />
                  <span>Paused for Render</span>
                </div>
              ) : isHarvesterLive ? (
                <div className="flex items-center gap-1.5 px-3 py-1 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-600 dark:text-emerald-400 text-[11px] font-bold">
                  <span className="w-2 h-2 rounded-xs bg-emerald-500 animate-pulse" />
                  <span>Live Harvesting</span>
                </div>
              ) : (
                <div className="flex items-center gap-1.5 px-3 py-1 rounded-xl bg-[var(--gl2)] border border-[var(--ln-subtle)] text-[var(--mu)] text-[11px] font-bold">
                  <span className="w-2 h-2 rounded-xs bg-slate-400" />
                  <span>Harvester Idle</span>
                </div>
              )}
            </div>
          </div>

          {/* Interactive SVG Combo Bar + Live Spline Chart (100% Real-Time Scaled Counts) */}
          <div className="relative w-full pt-2">
            {(() => {
              const chartMax = Math.max(500, Math.ceil(maxHouseCount / 500) * 500);
              const gridTicks = [0, 0.25, 0.5, 0.75, 1].map((f) => Math.round(chartMax * f));
              const pts = houseChartData.map((h, idx) => {
                const barH = Math.max(6, Math.min(120, (h.count / chartMax) * 120));
                return {
                  x: 100 + idx * 105,
                  y: 150 - barH,
                  barH,
                  h
                };
              });
              const splinePath = `M ${pts[0].x} ${pts[0].y} C ${pts[0].x + 48} ${pts[0].y}, ${pts[1].x - 48} ${pts[1].y}, ${pts[1].x} ${pts[1].y} C ${pts[1].x + 48} ${pts[1].y}, ${pts[2].x - 48} ${pts[2].y}, ${pts[2].x} ${pts[2].y} C ${pts[2].x + 48} ${pts[2].y}, ${pts[3].x - 48} ${pts[3].y}, ${pts[3].x} ${pts[3].y} C ${pts[3].x + 48} ${pts[3].y}, ${pts[4].x - 48} ${pts[4].y}, ${pts[4].x} ${pts[4].y}`;

              return (
                <svg viewBox="0 0 600 188" className="w-full h-44 overflow-visible">
                  <defs>
                    <linearGradient id="cfBarGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#2563eb" stopOpacity="0.85" />
                      <stop offset="100%" stopColor="#38bdf8" stopOpacity="0.2" />
                    </linearGradient>
                  </defs>

                  {/* Horizontal Grid Lines (Dynamic Record Count Scale) */}
                  {gridTicks.map((val, i) => {
                    const y = 150 - (i / 4) * 120;
                    return (
                      <g key={i}>
                        <line
                          x1="48"
                          y1={y}
                          x2="575"
                          y2={y}
                          stroke={isLight ? 'rgba(148,163,184,0.25)' : 'rgba(148,163,184,0.14)'}
                          strokeDasharray={i === 0 ? undefined : '3 3'}
                        />
                        <text
                          x="42"
                          y={y + 4}
                          textAnchor="end"
                          className="text-[10px] fill-slate-400 font-mono"
                        >
                          {val >= 1000 ? `${(val / 1000).toFixed(1)}k` : val}
                        </text>
                      </g>
                    );
                  })}

                  {/* 5 House Vertical Bars with Live Numeric Count Labels */}
                  {pts.map(({ x, y, barH, h }, idx) => {
                    const isHovered = hoveredHouseIdx === idx;
                    return (
                      <g
                        key={h.id}
                        className="cursor-pointer"
                        onMouseEnter={() => setHoveredHouseIdx(idx)}
                      >
                        <rect
                          x={x - 19}
                          y={y}
                          width="38"
                          height={barH}
                          rx="7"
                          fill="url(#cfBarGrad)"
                          opacity={isHovered ? 1 : 0.72}
                        />
                        <text
                          x={x}
                          y={Math.max(14, y - 10)}
                          textAnchor="middle"
                          className={`text-[10px] font-bold font-mono ${
                            isLight ? 'fill-slate-800' : 'fill-sky-300'
                          }`}
                        >
                          {h.count.toLocaleString()}
                        </text>
                        <text
                          x={x}
                          y="174"
                          textAnchor="middle"
                          className={`text-[10px] font-bold font-mono ${
                            isLight ? 'fill-slate-600' : 'fill-slate-400'
                          }`}
                        >
                          {h.short}
                        </text>
                      </g>
                    );
                  })}

                  {/* Smooth Live Trend Spline Curve */}
                  <path d={splinePath} fill="none" stroke="#2563eb" strokeWidth="2.5" />

                  {/* Circular Spline Nodes */}
                  {pts.map(({ x, y, h }, idx) => {
                    const isHovered = hoveredHouseIdx === idx;
                    return (
                      <g
                        key={`node-${h.id}`}
                        className="cursor-pointer"
                        onMouseEnter={() => setHoveredHouseIdx(idx)}
                      >
                        <circle
                          cx={x}
                          cy={y}
                          r={isHovered ? 6 : 4.5}
                          fill="#ffffff"
                          stroke="#2563eb"
                          strokeWidth="3"
                        />
                      </g>
                    );
                  })}
                </svg>
              );
            })()}

            {/* Floating Glass Tooltip Pill */}
            {houseChartData[hoveredHouseIdx] && (
              <div className="mt-1 flex items-center justify-between flex-wrap gap-2 px-3.5 py-2 rounded-xl glass-subcard text-xs">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-xs bg-blue-600 dark:bg-sky-400" />
                  <span className="font-bold text-[var(--tx)]">
                    {houseChartData[hoveredHouseIdx].short}: {houseChartData[hoveredHouseIdx].name}
                  </span>
                </div>
                <div className="flex items-center gap-4 font-mono text-[11px] text-[var(--mu)] flex-wrap">
                  <span>
                    Live Count: <b className="text-[var(--tx)]">{houseChartData[hoveredHouseIdx].count.toLocaleString()}</b> /{' '}
                    {houseChartData[hoveredHouseIdx].masterTarget > 0
                      ? houseChartData[hoveredHouseIdx].masterTarget.toLocaleString()
                      : '--'}
                  </span>
                  <span>
                    Phase {currentMilestoneCap > 0 ? Math.max(1, Math.round(currentMilestoneCap / Math.max(1, milestoneStep))) : '--'} Progress:{' '}
                    <b className="text-emerald-600 dark:text-emerald-400">{houseChartData[hoveredHouseIdx].retention}%</b> ({houseChartData[hoveredHouseIdx].count.toLocaleString()} / {houseChartData[hoveredHouseIdx].phaseTarget.toLocaleString()})
                  </span>
                  <span>
                    Open Sub-Rooms: <b className="text-[var(--tx)]">{houseChartData[hoveredHouseIdx].openSubRooms}</b>
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* 06 | TACTILE ACTION STACK + LATEST MASTER & SCRATCH METER (Right 1/3) */}
        <div className="glass-panel p-5 flex flex-col justify-between gap-3">
          <div className="flex items-center justify-between">
            <h2 className={`text-sm font-bold tracking-tight ${isLight ? 'text-slate-900' : 'text-white'}`}>
              Studio Controls &amp; Latest Cut
            </h2>
            <span className={`text-[11px] font-mono ${isLight ? 'text-slate-500' : 'text-slate-400'}`}>
              {cache?.output_count ?? 0} RENDERS
            </span>
          </div>

          {/* Latest Master Quick Screening Card */}
          {latestExportableJob && (
            <div
              onClick={() => navigate(`/qc1/${latestExportableJob.id}`)}
              className="glass-subcard p-2.5 flex items-center justify-between gap-3 cursor-pointer group"
            >
              <div className="flex items-center gap-2.5 min-w-0">
                <div className="relative w-12 h-9 rounded-lg iridescent-card-crime overflow-hidden shrink-0 flex items-center justify-center">
                  <img
                    src={`/output/thumb_${latestExportableJob.id}_v1_16x9.jpg`}
                    alt=""
                    className="w-full h-full object-cover"
                    onError={(e) => {
                      (e.currentTarget as HTMLImageElement).style.display = 'none';
                    }}
                  />
                  <Play size={11} className="text-white absolute drop-shadow" />
                </div>
                <div className="min-w-0">
                  <div className="text-xs font-bold text-[var(--tx)] group-hover:text-blue-600 dark:group-hover:text-blue-400 truncate">
                    {latestExportableJob.niche}
                  </div>
                  <div className="text-[10px] font-mono text-[var(--mu)]">
                    Latest #{latestExportableJob.id} · {latestExportableJob.config?.format || '9:16'}
                  </div>
                </div>
              </div>
              <ArrowRight size={14} className="text-[var(--mu)] group-hover:text-blue-500 shrink-0" />
            </div>
          )}

          {/* Scratch LRU Usage Meter */}
          <div className="space-y-1">
            <div className="flex items-center justify-between text-[10px] font-mono text-[var(--mu)]">
              <span>SCRATCH LRU CACHE</span>
              <span>{Number(cache?.temp_mb ?? 0).toFixed(1)} / 300 MB</span>
            </div>
            <Progress
              value={Number(cache?.temp_mb ?? 0)}
              max={300}
              label="Dashboard scratch cache meter"
              color={Number(cache?.temp_mb ?? 0) > 240 ? 'var(--wa)' : 'var(--ac)'}
            />
          </div>

          <div className="flex flex-col gap-2 my-auto">
            {/* Action 1: Export Publish-Ready ZIP Pack */}
            <button
              onClick={handleExportZip}
              className={`w-full flex items-center justify-between p-3 rounded-xl border transition-all cursor-pointer ${
                isLight
                  ? 'bg-white/85 hover:bg-white border-white text-slate-900 shadow-xs'
                  : 'bg-slate-900/85 hover:bg-slate-800 border-slate-700/80 text-white'
              }`}
            >
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-red-500/15 text-red-600 dark:text-red-400 border border-red-500/30 flex items-center justify-center shrink-0">
                  <Download size={15} />
                </div>
                <div className="text-left">
                  <div className="text-xs font-bold">Export Publish-Ready ZIP Pack</div>
                  <div className={`text-[10px] ${isLight ? 'text-slate-500' : 'text-slate-400'}`}>
                    {latestExportableJob
                      ? `Job #${latestExportableJob.id} · MP4 + SRT + Copy`
                      : 'Bundles MP4, SRT, ASS & Upload Copy'}
                  </div>
                </div>
              </div>
              <ChevronRight size={15} className="text-slate-400 shrink-0" />
            </button>

            {/* Action 2: Clear Temp / Beat Cache */}
            <button
              onClick={() => clearCacheMutation.mutate()}
              disabled={clearCacheMutation.isPending}
              className={`w-full flex items-center justify-between p-3 rounded-xl border transition-all cursor-pointer ${
                isLight
                  ? 'bg-white/85 hover:bg-white border-white text-slate-900 shadow-xs'
                  : 'bg-slate-900/85 hover:bg-slate-800 border-slate-700/80 text-white'
              }`}
            >
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-slate-500/15 text-slate-700 dark:text-slate-300 border border-slate-500/30 flex items-center justify-center shrink-0">
                  <Trash2 size={15} />
                </div>
                <div className="text-left">
                  <div className="text-xs font-bold">
                    {clearCacheMutation.isPending
                      ? 'Clearing Temp Cache...'
                      : `Clear Temp Cache (${cache?.temp_mb ?? '0.0'} MB)`}
                  </div>
                  <div className={`text-[10px] ${isLight ? 'text-slate-500' : 'text-slate-400'}`}>
                    Purges temp clips &amp; caches (300 MB LRU cap) while preserving master MP4s
                  </div>
                </div>
              </div>
              <ChevronRight size={15} className="text-slate-400 shrink-0" />
            </button>

            {/* Action 3: View Reflexion Audit Log */}
            <button
              onClick={() => navigate('/vault')}
              className={`w-full flex items-center justify-between p-3 rounded-xl border transition-all cursor-pointer ${
                isLight
                  ? 'bg-white/85 hover:bg-white border-white text-slate-900 shadow-xs'
                  : 'bg-slate-900/85 hover:bg-slate-800 border-slate-700/80 text-white'
              }`}
            >
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30 flex items-center justify-center shrink-0">
                  <FileText size={15} />
                </div>
                <div className="text-left">
                  <div className="text-xs font-bold">View Reflexion Audit Log</div>
                  <div className={`text-[10px] ${isLight ? 'text-slate-500' : 'text-slate-400'}`}>
                    {learnedRules.length} active self-healing editorial rules
                  </div>
                </div>
              </div>
              <ChevronRight size={15} className="text-slate-400 shrink-0" />
            </button>
          </div>
        </div>
      </div>

      {/* BOTTOM ROW (2/3 Reflexion & Job Audit Log Table + 1/3 Prismatic Instant Launch Card) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* 07A | REFLEXION & PIPELINE AUDIT LOG TABLE (Left 2/3) */}
        <div className="glass-panel p-5 lg:col-span-2 flex flex-col justify-between">
          <div className="flex items-center justify-between gap-2 mb-3">
            <div>
              <h2 className={`text-sm font-bold tracking-tight ${isLight ? 'text-slate-900' : 'text-white'}`}>
                Pipeline &amp; Reflexion Audit Log
              </h2>
              <p className={`text-[11px] ${isLight ? 'text-slate-500' : 'text-slate-400'}`}>
                Click any documentary job to inspect in QC1 Studio, export its .ZIP bundle, or review verification status
              </p>
            </div>
            <div className="flex items-center gap-2">
              <span
                className={`px-2.5 py-1 rounded-lg text-[10px] font-bold border ${
                  isLight
                    ? 'bg-blue-600 text-white border-blue-500'
                    : 'bg-blue-600/20 text-blue-400 border-blue-500/30'
                }`}
              >
                {filteredJobs.length} Jobs
              </span>
              <button
                onClick={() => navigate('/pipeline')}
                className={`px-2.5 py-1 rounded-lg text-[10px] font-semibold border cursor-pointer ${
                  isLight
                    ? 'bg-white/80 border-white text-slate-700 hover:bg-white'
                    : 'bg-slate-800 border-slate-700 text-slate-300 hover:text-white'
                }`}
              >
                Full Queue
              </button>
            </div>
          </div>

          <div
            role="region"
            aria-label="Pipeline and Reflexion audit log table"
            tabIndex={0}
            className="studio-table-region"
          >
            <table className="w-full text-left border-collapse">
              <thead className="bg-[var(--table-head)]">
                <tr
                  className={`border-b text-[11px] font-bold uppercase tracking-wider ${
                    isLight ? 'border-slate-300/60 text-slate-500' : 'border-slate-800 text-slate-400'
                  }`}
                >
                  <th scope="col" className="py-2 pr-3">Subject / Event</th>
                  <th scope="col" className="py-2 px-3">Stage</th>
                  <th scope="col" className="py-2 px-3">Engine</th>
                  <th scope="col" className="py-2 pl-3 text-right">Time / Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-300/40 dark:divide-slate-800/70 text-xs">
                {filteredJobs.slice(0, 5).map((job: any) => {
                  const isReady =
                    job.current_stage === 'QC1' ||
                    job.current_stage === 'READY_TO_PUBLISH' ||
                    job.status === 'COMPLETED';
                  const createdDate = job.created_at ? new Date(job.created_at) : new Date();
                  const timeStr = createdDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                  return (
                    <tr
                      key={job.id}
                      onClick={() => navigate(`/qc1/${job.id}`)}
                      className={`cursor-pointer transition-colors ${
                        isLight ? 'hover:bg-white/70' : 'hover:bg-slate-800/50'
                      }`}
                    >
                      <td className="py-2.5 pr-3 font-semibold flex items-center gap-2.5">
                        <div className="relative w-9 h-6 rounded-md iridescent-card-crime overflow-hidden shrink-0 flex items-center justify-center">
                          <img
                            src={`/output/thumb_${job.id}_v1_16x9.jpg`}
                            alt=""
                            className="w-full h-full object-cover"
                            onError={(e) => {
                              (e.currentTarget as HTMLImageElement).style.display = 'none';
                            }}
                          />
                          {isReady ? (
                            <CheckCircle2 size={11} className="text-emerald-300" />
                          ) : (
                            <AlertTriangle size={11} className="text-amber-300" />
                          )}
                        </div>
                        <span className="truncate max-w-[230px]">{job.niche}</span>
                      </td>
                      <td className="py-2.5 px-3">
                        <span
                          className={`px-2 py-0.5 rounded-md text-[10px] font-bold uppercase ${
                            isReady
                              ? 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border border-emerald-500/30'
                              : 'bg-amber-500/15 text-amber-700 dark:text-amber-300 border border-amber-500/30'
                          }`}
                        >
                          {job.current_stage || job.status}
                        </span>
                      </td>
                      <td className={`py-2.5 px-3 font-mono text-[11px] ${isLight ? 'text-slate-600' : 'text-slate-400'}`}>
                        {(job.config?.format || '9:16')} · {(job.config?.genre || 'crime_doc')}
                      </td>
                      <td className="py-2.5 pl-3 text-right font-mono text-[11px]">
                        <div className="flex items-center justify-end gap-2">
                          <span className={isLight ? 'text-slate-600' : 'text-slate-400'}>{timeStr}</span>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              window.open(`/api/jobs/${job.id}/export`, '_blank');
                            }}
                            className="p-1 rounded hover:bg-blue-500/15 text-blue-600 dark:text-blue-400 cursor-pointer"
                            title="Download Publish-Ready .ZIP Bundle"
                          >
                            <Download size={13} />
                          </button>
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              setJobPendingDelete(job);
                            }}
                            className="p-1 rounded hover:bg-red-500/15 text-slate-400 hover:text-red-500 cursor-pointer"
                            title="Delete Job"
                          >
                            <Trash2 size={13} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}

                {/* Also display top learned Reflexion verification rules if table has room */}
                {learnedRules.slice(0, Math.max(1, 4 - filteredJobs.slice(0, 4).length)).map((rule, rIdx) => (
                  <tr
                    key={`rule-${rIdx}`}
                    onClick={() => navigate('/vault')}
                    className={`cursor-pointer transition-colors ${
                      isLight ? 'hover:bg-white/70' : 'hover:bg-slate-800/50'
                    }`}
                  >
                    <td className="py-2.5 pr-3 font-medium flex items-center gap-2.5">
                      <span className="w-5 h-5 rounded-md bg-blue-500/15 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0">
                        <ShieldCheck size={13} />
                      </span>
                      <span className="truncate max-w-[230px]">{rule.lesson}</span>
                    </td>
                    <td className="py-2.5 px-3">
                      <span className="px-2 py-0.5 rounded-md text-[10px] font-bold uppercase bg-blue-500/15 text-blue-700 dark:text-blue-300 border border-blue-500/30">
                        Reflexion
                      </span>
                    </td>
                    <td className={`py-2.5 px-3 font-mono text-[11px] ${isLight ? 'text-slate-600' : 'text-slate-400'}`}>
                      {rule.category}
                    </td>
                    <td className={`py-2.5 pl-3 text-right font-mono text-[11px] ${isLight ? 'text-slate-600' : 'text-slate-400'}`}>
                      Verified
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <ConfirmDialog
            isOpen={Boolean(jobPendingDelete)}
            title={jobPendingDelete ? `Delete Video #${jobPendingDelete.id}?` : 'Delete Video?'}
            description={
              jobPendingDelete
                ? `Remove "${jobPendingDelete.niche}" from the production studio history?`
                : 'Remove this video from the production studio history?'
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

        {/* 07B | PRISMATIC RIM-LIT "LAUNCH INSTANT DOCUMENTARY" CARD (Right 1/3) */}
        <div className="prismatic-launch-card p-5 text-white flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <span className="px-2.5 py-0.5 rounded-md bg-cyan-500/20 text-cyan-300 border border-cyan-400/30 text-[10px] font-bold uppercase tracking-wider">
                2-Pass Engine · SHA-256 Cache
              </span>
              <Cpu size={16} className="text-cyan-300" />
            </div>
            <h3 className="text-lg font-extrabold tracking-tight leading-snug">
              Launch Instant Documentary.
            </h3>
            <p className="text-[11px] text-slate-300 mt-1">
              Grounded Wikipedia + yt-dlp fact dossier, 35mm optical plates, and -14 LUFS audio.
            </p>
          </div>

          <div className="my-3 flex flex-col gap-2">
            <input
              type="text"
              value={quickTopic}
              onChange={(e) => setQuickTopic(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  if (e.nativeEvent.isComposing || e.nativeEvent.keyCode === 229) return;
                  handleQuickLaunch();
                }
              }}
              placeholder="Enter topic (e.g. CIA Project Azorian)..."
              className="w-full px-3 py-2 rounded-xl bg-white/10 border border-white/20 text-xs text-white placeholder:text-slate-400 outline-none focus:border-cyan-400"
            />
            <div className="flex items-center gap-1.5">
              {(['crime_doc', 'viral_edu', 'movie_cinema'] as const).map((g) => (
                <button
                  key={g}
                  onClick={() => setQuickGenre(g)}
                  className={`px-2 py-1 rounded-lg text-[10px] font-bold uppercase cursor-pointer border transition-all ${
                    quickGenre === g
                      ? 'bg-cyan-500 text-slate-950 border-cyan-300'
                      : 'bg-white/10 text-slate-300 border-white/15 hover:bg-white/20'
                  }`}
                >
                  {g.replace('_', ' ')}
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center justify-between gap-2 pt-1">
            <button
              onClick={handleQuickLaunch}
              disabled={createInstantMutation.isPending}
              className="flex-1 py-2 px-3 rounded-xl bg-white text-slate-950 font-extrabold text-xs hover:bg-cyan-50 transition-colors cursor-pointer shadow-sm"
            >
              {createInstantMutation.isPending ? 'Launching...' : quickTopic.trim() ? 'Generate Now' : 'Open Studio'}
            </button>
            <button
              onClick={() => navigate('/create')}
              className="w-9 h-9 rounded-xl bg-white/15 hover:bg-white/25 border border-white/25 flex items-center justify-center cursor-pointer"
              title="Advanced Create Options"
            >
              <Plus size={15} />
            </button>
            <button
              onClick={() => navigate('/agents')}
              className="px-2.5 h-9 rounded-xl bg-white/10 hover:bg-white/20 border border-white/20 font-mono text-[11px] flex items-center justify-center cursor-pointer"
              title="Total Studio Jobs"
            >
              {jobs.length}J
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
