import { useState, useMemo, useEffect, ChangeEvent } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  RotateCw,
  RotateCcw,
  Mic,
  Check,
  Trash2,
  Eye,
  EyeOff,
  ExternalLink,
  ShieldCheck,
  Loader2,
  Download,
  Upload,
  Image as ImageIcon,
  Copy,
  ShieldAlert,
  Smile,
  Flame,
  Clapperboard,
  Zap,
  Cpu,
  Package
} from 'lucide-react';
import {
  useJobs,
  useRerollVisual,
  useRegenerateAudio,
  usePublishJob,
  useDeleteJobTemp,
  useUploadAnchor,
  useUploadCustomSceneMedia,
  useJobThumbnails,
  useRegenerateThumbnails,
  useGenerateBeatVideo,
  useManifestHistory,
  useRollbackManifest
} from '../api/client';
import { Button, Badge, Card } from '../components/ui';
import SafeZoneOverlay from '../components/SafeZoneOverlay';
import VideoStudioModal from '../components/VideoStudioModal';
import DirectorChatDrawer from '../components/DirectorChatDrawer';

export default function QC1() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { data: jobs = [] } = useJobs();

  const [showSafeZone, setShowSafeZone] = useState(true);
  const [isStudioOpen, setIsStudioOpen] = useState(false);
  const [isDirectorChatOpen, setIsDirectorChatOpen] = useState(false);
  const [overrideVideoUrl, setOverrideVideoUrl] = useState<string | null>(null);
  const [thumbAspect, setThumbAspect] = useState<'16:9' | '9:16'>('16:9');
  const [copiedTitleIdx, setCopiedTitleIdx] = useState<number | null>(null);
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>([
    'TikTok',
    'YouTube Shorts',
    'Instagram Reels'
  ]);
  const [editedScenes, setEditedScenes] = useState<any[]>([]);
  const [activeRerollingIndex, setActiveRerollingIndex] = useState<number | null>(null);
  const [isPublishing, setIsPublishing] = useState(false);
  const [publishedStatus, setPublishedStatus] = useState<string | null>(null);

  const rerollMutation = useRerollVisual();
  const audioMutation = useRegenerateAudio();
  const publishMutation = usePublishJob();
  const deleteTempMutation = useDeleteJobTemp();
  const uploadAnchorMutation = useUploadAnchor();
  const uploadCustomMediaMutation = useUploadCustomSceneMedia();
  const { data: thumbnailData, isLoading: isThumbLoading } = useJobThumbnails(id);
  const regenerateThumbsMutation = useRegenerateThumbnails();
  const generateBeatVideoMutation = useGenerateBeatVideo();
  const { data: manifestHistoryData } = useManifestHistory(id);
  const rollbackMutation = useRollbackManifest();
  const historyVersions = manifestHistoryData?.versions || [];
  const latestUndoVersion = historyVersions.length > 0 ? historyVersions[historyVersions.length - 1] : null;
  const [anchorUploadMsg, setAnchorUploadMsg] = useState<string | null>(null);
  const [activeUploadingIndex, setActiveUploadingIndex] = useState<number | null>(null);
  const [activeAiVideoIndex, setActiveAiVideoIndex] = useState<number | null>(null);
  const [flowHandoffMap, setFlowHandoffMap] = useState<Record<number, { prompt: string; image_path?: string; flow_url?: string; reason?: string }>>({});
  const [copiedFlowIdx, setCopiedFlowIdx] = useState<number | null>(null);

  const job = useMemo(() => jobs.find((j: any) => String(j.id) === id), [jobs, id]);

  const videoAsset = job?.assets?.find((a: any) => a.type === 'VIDEO' || a.type === 'video');
  const jobMeta = videoAsset?.metadata || {};
  const videoUrl =
    jobMeta.video_url ||
    (videoAsset?.path ? `/output/${videoAsset.path.split(/[\\/]/).pop()}` : null);
  const activeVideoUrl = overrideVideoUrl || videoUrl;
  const rawScenes = jobMeta.scenes || [];

  useEffect(() => {
    if (rawScenes.length > 0) {
      setEditedScenes(rawScenes);
    }
  }, [id, activeVideoUrl, job]);

  if (!job) {
    return (
      <div className="p-12 text-center text-[var(--mu)]">
        <Loader2 size={24} className="animate-spin mx-auto mb-2 text-blue-600 dark:text-blue-400" />
        <p className="text-sm font-medium">Loading storyboard details for Job #{id}...</p>
      </div>
    );
  }

  const isPublished = job.current_stage === 'PUBLISHED' || job.status === 'PUBLISHED';
  const isReadyToPublish =
    !!publishedStatus ||
    job.current_stage === 'READY_TO_PUBLISH' ||
    job.status === 'COMPLETED';
  const displayScenes = editedScenes.length > 0 ? editedScenes : rawScenes;
  const stylePreset = jobMeta.style_preset || job.config?.style_preset || 'Dark Documentary';
  const voiceName = jobMeta.voice || job.config?.voice || 'en-US-AndrewMultilingualNeural';
  const formatVoiceShort = (v: string) => {
    if (!v) return 'Andrew Multilingual';
    if (v === 'am_michael' || v.includes('kokoro')) return 'Kokoro-82M Michael';
    const seg = v.split('-')[2];
    return seg ? seg.replace('MultilingualNeural', ' Multilingual').replace('Neural', '') : v;
  };
  const totalDuration = jobMeta.duration
    ? `${Math.round(jobMeta.duration)}s`
    : job.config?.duration || 'Pending';
  const currentGenre = jobMeta.genre || job.config?.genre || 'auto';

  const genreBadgeConfig: Record<string, { label: string; Icon: any; variant: string }> = {
    crime_doc: { label: 'Crime / Doc', Icon: ShieldAlert, variant: 'danger' },
    comedy_skit: { label: 'Comedy / Skit', Icon: Smile, variant: 'warning' },
    action_hype: { label: 'Action / Hype', Icon: Flame, variant: 'warning' },
    movie_cinema: { label: 'Movie / Cinema', Icon: Clapperboard, variant: 'info' },
    viral_edu: { label: 'Viral Edu', Icon: Zap, variant: 'info' },
    auto: { label: 'Auto Detect', Icon: Cpu, variant: 'neutral' }
  };

  const handleSceneTextChange = (index: number, newText: string) => {
    setEditedScenes((prev) => {
      const updated = [...prev];
      if (updated[index]) {
        updated[index] = { ...updated[index], text: newText };
      }
      return updated;
    });
  };

  const handleScenePromptChange = (index: number, newPrompt: string) => {
    setEditedScenes((prev) => {
      const updated = [...prev];
      if (updated[index]) {
        updated[index] = { ...updated[index], prompt: newPrompt };
      }
      return updated;
    });
  };

  const handleRerollVisual = async (sceneIndex: number) => {
    if (!id || activeRerollingIndex !== null) return;
    setActiveRerollingIndex(sceneIndex);
    const targetScene = displayScenes[sceneIndex];

    try {
      const res = await rerollMutation.mutateAsync({
        jobId: id,
        sceneIndex,
        customPrompt: targetScene?.prompt,
        stylePreset
      });

      if (res?.scene) {
        setEditedScenes((prev) => {
          const updated = [...prev];
          updated[sceneIndex] = res.scene;
          return updated;
        });
      }
    } catch (e) {
      console.error('Failed to reroll visual:', e);
    } finally {
      setActiveRerollingIndex(null);
    }
  };

  const handleGenerateBeatAiVideo = async (sceneIndex: number) => {
    if (!id || activeAiVideoIndex !== null) return;
    setActiveAiVideoIndex(sceneIndex);
    const targetScene = displayScenes[sceneIndex];
    const promptToUse = targetScene?.prompt || `${targetScene?.text || job.niche}, ${stylePreset}`;

    try {
      const res = await generateBeatVideoMutation.mutateAsync({
        jobId: id,
        beatId: sceneIndex,
        prompt: promptToUse,
        imagePath: targetScene?.image_path,
        duration: Number(targetScene?.duration || 4.0),
        engine: 'hf_ltx25',
      });

      if (res?.status === 'success' && res?.scene) {
        setEditedScenes((prev) => {
          const updated = [...prev];
          updated[sceneIndex] = res.scene;
          return updated;
        });
        if (res.video_url) {
          setOverrideVideoUrl(res.video_url);
        }
        setFlowHandoffMap((prev) => {
          const next = { ...prev };
          delete next[sceneIndex];
          return next;
        });
      } else if (res?.flow_handoff) {
        setFlowHandoffMap((prev) => ({
          ...prev,
          [sceneIndex]: { ...res.flow_handoff, reason: res.reason },
        }));
      }
    } catch (e: any) {
      setFlowHandoffMap((prev) => ({
        ...prev,
        [sceneIndex]: {
          prompt: promptToUse,
          image_path: targetScene?.image_path,
          flow_url: 'https://labs.google/fx/tools/flow',
          reason: e?.message || 'ZeroGPU busy',
        },
      }));
    } finally {
      setActiveAiVideoIndex(null);
    }
  };

  const handleUploadCustomMedia = async (index: number, e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !id) return;
    setActiveUploadingIndex(index);
    try {
      const res = await uploadCustomMediaMutation.mutateAsync({
        jobId: id,
        sceneIndex: index,
        file
      });
      if (res?.scene) {
        setEditedScenes((prev) => {
          const updated = [...prev];
          updated[index] = { ...updated[index], ...res.scene };
          return updated;
        });
      }
    } catch (err) {
      console.error('Failed to upload custom media:', err);
    } finally {
      setActiveUploadingIndex(null);
      e.target.value = '';
    }
  };

  const handleRegenerateAudio = async () => {
    if (!id || audioMutation.isPending) return;
    try {
      await audioMutation.mutateAsync({
        jobId: id,
        voice: voiceName,
        scenes: displayScenes
      });
    } catch (e) {
      console.error('Failed to regenerate audio:', e);
    }
  };

  const handlePublish = async () => {
    if (!id || isPublishing || selectedPlatforms.length === 0) return;
    setIsPublishing(true);
    try {
      const res = await publishMutation.mutateAsync({
        jobId: id,
        platforms: selectedPlatforms
      });
      setPublishedStatus(res.message || 'Ready to Publish');
    } catch (e) {
      console.error(e);
    } finally {
      setIsPublishing(false);
    }
  };

  const handleDeleteTemp = async () => {
    if (!id || deleteTempMutation.isPending) return;
    try {
      await deleteTempMutation.mutateAsync(id);
    } catch (e) {
      console.error(e);
    }
  };

  const togglePlatform = (platform: string) => {
    setSelectedPlatforms((prev) =>
      prev.includes(platform) ? prev.filter((p) => p !== platform) : [...prev, platform]
    );
  };

  const abTitles: string[] =
    thumbnailData?.ab_titles && thumbnailData.ab_titles.length > 0
      ? thumbnailData.ab_titles
      : [
          `${job.niche}: The Untold Evidence File`,
          `Inside ${job.niche} (Full Documentary Breakdown)`,
          `What Really Happened During ${job.niche}`
        ];

  return (
    <div className="animate-in fade-in min-h-full flex flex-col pb-12 max-w-7xl mx-auto space-y-6">
      {/* Top Header */}
      <div className="flex justify-between items-center flex-wrap gap-3 pb-4 border-b border-[var(--ln-subtle)]">
        <div>
          <div className="flex items-center flex-wrap gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-[var(--tx)]">{job.niche}</h1>
            {isPublished ? (
              <Badge variant="success">Published</Badge>
            ) : isReadyToPublish ? (
              <Badge variant="success">Ready to Publish</Badge>
            ) : (
              <Badge variant="warning">QC1 Review Stage</Badge>
            )}
            {jobMeta.fact_dossier && (
              <Badge variant="success">
                <ShieldCheck size={11} />
                <span>Verified Fact Dossier</span>
              </Badge>
            )}
            {genreBadgeConfig[currentGenre] &&
              (() => {
                const GIcon = genreBadgeConfig[currentGenre].Icon;
                return (
                  <Badge variant={genreBadgeConfig[currentGenre].variant}>
                    <GIcon size={11} />
                    <span>{genreBadgeConfig[currentGenre].label}</span>
                  </Badge>
                );
              })()}
          </div>
          <p className="text-xs text-[var(--mu)] mt-1">
            Job #{job.id} · Genre: {genreBadgeConfig[currentGenre]?.label || currentGenre} ·{' '}
            {stylePreset} · {totalDuration} · Voice: {formatVoiceShort(voiceName)}
          </p>
        </div>

        <div className="flex items-center flex-wrap gap-2">
          <Button
            onClick={() => setIsDirectorChatOpen(true)}
            className="bg-amber-500 hover:bg-amber-400 text-slate-950 border-amber-400 shadow-sm"
            title="Open Director Command Studio"
          >
            <Clapperboard size={14} className="text-slate-950" />
            <span>Director Studio</span>
          </Button>

          {activeVideoUrl && (
            <a
              href={`/api/jobs/${id}/export`}
              className="inline-flex items-center gap-1.5 text-xs font-semibold py-2 px-3.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white border border-blue-500 shadow-sm transition-colors cursor-pointer"
              title="Download Publish-Ready .ZIP Pack (MP4 + Thumb + Captions + Upload Copy)"
            >
              <Package size={14} />
              <span>Export .ZIP Pack</span>
            </a>
          )}

          {activeVideoUrl && (
            <a
              href={activeVideoUrl}
              download={`${String(job.niche || 'video').replace(/[^a-zA-Z0-9_-]/g, '_')}_9x16.mp4`}
              className="inline-flex items-center gap-1.5 text-xs font-semibold py-2 px-3 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white border border-emerald-500 shadow-sm transition-colors cursor-pointer"
              title="Download MP4 video"
            >
              <Download size={14} />
              <span>MP4</span>
            </a>
          )}

          <Button variant="secondary" onClick={() => setIsStudioOpen(true)}>
            <ExternalLink size={14} />
            <span>Studio Inspector</span>
          </Button>

          <Button variant="ghost" onClick={() => navigate('/create')}>
            + New Video
          </Button>
        </div>
      </div>

      {/* Main Grid: Left Video Player | Right Storyboard Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-[340px_1fr] gap-6 items-start">
        {/* Left Column: Video Player */}
        <div className="flex flex-col items-center space-y-3 sticky top-6">
          {(() => {
            const isWidescreen =
              job.config?.format === '16:9' || (job.config as any)?.aspect_ratio === '16:9';
            return (
              <>
                <div className="w-full flex items-center justify-between px-1">
                  <span className="text-xs font-bold uppercase tracking-wider text-[var(--mu)]">
                    {isWidescreen ? '16:9 Cinema Player' : '9:16 Reel Player'}
                  </span>
                  {!isWidescreen && (
                    <button
                      onClick={() => setShowSafeZone(!showSafeZone)}
                      className={`flex items-center gap-1 text-[11px] font-semibold px-2.5 py-1 rounded-lg border transition-colors cursor-pointer ${
                        showSafeZone
                          ? 'bg-cyan-500/15 text-cyan-700 dark:text-cyan-300 border-cyan-500/40'
                          : 'bg-[var(--gl2)] text-[var(--mu)] border-[var(--input-border)] hover:text-[var(--tx)]'
                      }`}
                    >
                      {showSafeZone ? <Eye size={12} /> : <EyeOff size={12} />}
                      <span>{showSafeZone ? 'Safe Zone On' : 'Safe Zone Off'}</span>
                    </button>
                  )}
                </div>

                {isWidescreen ? (
                  <div className="relative w-full max-w-[560px] aspect-video rounded-2xl p-2 bg-gradient-to-b from-slate-700 via-slate-800 to-slate-900 border-2 border-slate-600 shadow-2xl flex items-center justify-center overflow-hidden">
                    <div className="relative w-full h-full rounded-xl overflow-hidden bg-black flex items-center justify-center">
                      {activeVideoUrl ? (
                        <video
                          controls
                          playsInline
                          autoPlay
                          loop
                          key={activeVideoUrl}
                          src={activeVideoUrl}
                          className="w-full h-full object-contain"
                        />
                      ) : (
                        <div className="text-center p-6 text-slate-400 text-xs flex flex-col items-center gap-2">
                          <Loader2 size={24} className="animate-spin text-blue-500" />
                          <span>Assembling 16:9 widescreen video stream...</span>
                        </div>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="relative w-[320px] h-[568px] rounded-[36px] p-2.5 bg-gradient-to-b from-slate-700 via-slate-800 to-slate-900 border-2 border-slate-600 shadow-2xl flex items-center justify-center overflow-hidden">
                    <div className="absolute top-3.5 left-1/2 -translate-x-1/2 w-24 h-4 bg-black rounded-md z-40 border border-white/10" />
                    <div className="relative w-full h-full rounded-[26px] overflow-hidden bg-black flex items-center justify-center">
                      {activeVideoUrl ? (
                        <video
                          controls
                          playsInline
                          autoPlay
                          loop
                          key={activeVideoUrl}
                          src={activeVideoUrl}
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <div className="text-center p-6 text-slate-400 text-xs flex flex-col items-center gap-2">
                          <Loader2 size={24} className="animate-spin text-blue-500" />
                          <span>Assembling 9:16 video stream...</span>
                        </div>
                      )}

                      <SafeZoneOverlay
                        visible={showSafeZone}
                        caption={jobMeta.script?.hook || `The breakdown of ${job.niche}`}
                      />
                    </div>
                  </div>
                )}

                <div className="w-full flex items-center justify-between text-[11px] text-[var(--mu)] px-2 font-mono">
                  <span>{isWidescreen ? '1920 x 1080 Widescreen MP4' : '1080 x 1920 MP4'}</span>
                  <span>-14 LUFS Audio</span>
                </div>
              </>
            );
          })()}
        </div>

        {/* Right Column: Thumbnails & Storyboard Grid */}
        <div className="space-y-5">
          {/* High-CTR Thumbnail & Title Packager */}
          <Card className="!p-5 space-y-4">
            <div className="flex items-center justify-between flex-wrap gap-2 pb-3 border-b border-[var(--ln-subtle)]">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-xl bg-amber-500/15 border border-amber-500/30 text-amber-600 dark:text-amber-400">
                  <ImageIcon size={16} />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-[var(--tx)] flex items-center gap-2">
                    <span>High-CTR Thumbnail & Title Packager</span>
                    <Badge variant="warning">3 A/B Variants</Badge>
                  </h3>
                  <p className="text-[11px] text-[var(--mu)]">
                    Generated 16:9 and 9:16 cover variants with subject cutout, contrast rim lighting, and title badges.
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <div className="flex items-center bg-[var(--gl2)] p-0.5 rounded-xl border border-[var(--input-border)] text-[11px]">
                  <button
                    onClick={() => setThumbAspect('16:9')}
                    className={`px-2.5 py-1 rounded-lg font-semibold transition-all cursor-pointer ${
                      thumbAspect === '16:9'
                        ? 'bg-blue-600 text-white shadow-xs'
                        : 'text-[var(--mu)] hover:text-[var(--tx)]'
                    }`}
                  >
                    16:9 Landscape
                  </button>
                  <button
                    onClick={() => setThumbAspect('9:16')}
                    className={`px-2.5 py-1 rounded-lg font-semibold transition-all cursor-pointer ${
                      thumbAspect === '9:16'
                        ? 'bg-blue-600 text-white shadow-xs'
                        : 'text-[var(--mu)] hover:text-[var(--tx)]'
                    }`}
                  >
                    9:16 Vertical
                  </button>
                </div>

                <Button
                  variant="secondary"
                  onClick={() => id && regenerateThumbsMutation.mutate(id)}
                  disabled={regenerateThumbsMutation.isPending || isThumbLoading}
                  className="!py-1.5 !px-3"
                  title="Re-render all 3 thumbnail variants"
                >
                  <RotateCw
                    size={12}
                    className={
                      regenerateThumbsMutation.isPending
                        ? 'animate-spin text-amber-500'
                        : 'text-amber-600 dark:text-amber-400'
                    }
                  />
                  <span>{regenerateThumbsMutation.isPending ? 'Rendering...' : 'Regen Covers'}</span>
                </Button>
              </div>
            </div>

            {/* 3 Thumbnail Variants */}
            {thumbnailData?.variants && thumbnailData.variants.length > 0 ? (
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {thumbnailData.variants.map((v: any) => {
                  const imgUrl = thumbAspect === '16:9' ? v.thumb_16x9 : v.thumb_9x16;
                  const aspectClass =
                    thumbAspect === '16:9' ? 'aspect-video' : 'aspect-[9/16] max-h-[220px] mx-auto';

                  return (
                    <div
                      key={v.id}
                      className="glass-subcard p-2.5 flex flex-col justify-between space-y-2 group"
                    >
                      <div>
                        <div className="flex items-center justify-between mb-1.5">
                          <span className="text-[11px] font-bold text-[var(--tx)] uppercase tracking-wider truncate">
                            #{v.id} · {v.name}
                          </span>
                          <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-[var(--input-bg)] text-amber-600 dark:text-amber-400 border border-[var(--input-border)]">
                            {thumbAspect}
                          </span>
                        </div>

                        <div
                          className={`relative rounded-lg overflow-hidden border border-[var(--ln-subtle)] bg-black ${aspectClass} flex items-center justify-center`}
                        >
                          <img
                            src={imgUrl}
                            alt={v.name}
                            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                            onError={(e) => {
                              (e.target as HTMLImageElement).style.display = 'none';
                            }}
                          />
                        </div>

                        <p className="text-[10px] text-[var(--mu)] mt-1.5 line-clamp-1" title={v.style}>
                          {v.style}
                        </p>
                      </div>

                      <a
                        href={imgUrl}
                        download={`thumb_job${id}_v${v.id}_${thumbAspect.replace(':', 'x')}.jpg`}
                        className="w-full flex items-center justify-center gap-1.5 text-[11px] font-semibold py-1.5 rounded-lg bg-[var(--input-bg)] border border-[var(--input-border)] hover:bg-blue-600 hover:border-blue-500 text-[var(--tx)] hover:text-white transition-colors"
                      >
                        <Download size={11} />
                        <span>Download {thumbAspect}</span>
                      </a>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="glass-subcard p-5 text-center text-xs text-[var(--mu)]">
                {isThumbLoading
                  ? 'Loading rendered thumbnail variants...'
                  : 'No thumbnail variants rendered yet for this job. Click Regen Covers to generate them.'}
              </div>
            )}

            {/* A/B Test Title Suggestions */}
            <div className="glass-subcard p-3.5 space-y-2">
              <div className="flex items-center justify-between text-xs font-bold text-[var(--tx)]">
                <span className="flex items-center gap-1.5">
                  <ShieldCheck size={13} className="text-amber-600 dark:text-amber-400" />
                  <span>Curiosity A/B Title Suggestions</span>
                </span>
                <span className="text-[10px] text-[var(--mu)] font-normal">Click to copy</span>
              </div>

              <div className="space-y-1.5">
                {abTitles.map((title: string, tIdx: number) => {
                  const isCopied = copiedTitleIdx === tIdx;
                  return (
                    <div
                      key={tIdx}
                      className="p-2 rounded-lg bg-[var(--input-bg)] border border-[var(--ln-subtle)] flex items-center justify-between gap-3 text-xs"
                    >
                      <span className="text-[11px] text-[var(--tx)] font-medium truncate">
                        <span className="text-amber-600 dark:text-amber-400 font-bold mr-1.5">
                          #{tIdx + 1}
                        </span>
                        {title}
                      </span>
                      <button
                        onClick={() => {
                          navigator.clipboard.writeText(title);
                          setCopiedTitleIdx(tIdx);
                          setTimeout(() => setCopiedTitleIdx(null), 2000);
                        }}
                        className={`px-2 py-1 rounded-lg text-[10px] font-semibold flex items-center gap-1 transition-colors shrink-0 cursor-pointer border ${
                          isCopied
                            ? 'bg-emerald-500/15 border-emerald-500/40 text-emerald-700 dark:text-emerald-300'
                            : 'bg-[var(--gl2)] border-[var(--input-border)] text-[var(--tx)] hover:border-blue-500'
                        }`}
                      >
                        {isCopied ? <Check size={11} /> : <Copy size={11} />}
                        <span>{isCopied ? 'Copied' : 'Copy'}</span>
                      </button>
                    </div>
                  );
                })}
              </div>
            </div>
          </Card>

          {/* Storyboard Header */}
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div>
              <h2 className="text-base font-bold text-[var(--tx)]">Storyboard & Shot Inspector</h2>
              <p className="text-xs text-[var(--mu)]">
                Edit narration lines, adjust image prompts, or re-roll individual cached beats.
              </p>
            </div>

            <div className="flex items-center gap-2 flex-wrap">
              {latestUndoVersion && (
                <Button
                  variant="secondary"
                  onClick={async () => {
                    if (!id || rollbackMutation.isPending) return;
                    try {
                      const res = await rollbackMutation.mutateAsync({
                        jobId: id,
                        version: latestUndoVersion.version,
                        reRender: true,
                      });
                      if (res?.video_url) {
                        setOverrideVideoUrl(res.video_url);
                      }
                    } catch (err) {
                      console.error('Rollback failed:', err);
                    }
                  }}
                  disabled={rollbackMutation.isPending}
                  title={`Revert timeline to snapshot v${latestUndoVersion.version} (${latestUndoVersion.action_label})`}
                >
                  {rollbackMutation.isPending ? (
                    <Loader2 size={13} className="animate-spin text-amber-500" />
                  ) : (
                    <RotateCcw size={13} className="text-amber-600 dark:text-amber-400" />
                  )}
                  <span>
                    {rollbackMutation.isPending ? 'Reverting...' : `Undo Edit (v${latestUndoVersion.version})`}
                  </span>
                </Button>
              )}
              <label className="cursor-pointer inline-flex items-center gap-1.5 text-xs font-semibold py-2 px-3 rounded-xl border border-[var(--input-border)] bg-[var(--gl2)] hover:border-blue-500 text-[var(--tx)] transition-colors">
                {uploadAnchorMutation.isPending ? (
                  <Loader2 size={13} className="animate-spin text-blue-500" />
                ) : (
                  <Upload size={13} className="text-blue-600 dark:text-blue-400" />
                )}
                <span>{uploadAnchorMutation.isPending ? 'Uploading...' : 'Style Anchor'}</span>
                <input
                  type="file"
                  accept="image/png,image/jpeg,image/webp"
                  className="hidden"
                  onChange={async (e) => {
                    const f = e.target.files?.[0];
                    if (f && id) {
                      try {
                        await uploadAnchorMutation.mutateAsync({ jobId: id, file: f });
                        setAnchorUploadMsg('Style anchor attached!');
                        setTimeout(() => setAnchorUploadMsg(null), 3000);
                      } catch {
                        setAnchorUploadMsg('Upload failed');
                      }
                    }
                  }}
                />
              </label>

              <Button
                variant="secondary"
                onClick={() => handleRegenerateAudio()}
                disabled={audioMutation.isPending}
              >
                {audioMutation.isPending ? (
                  <Loader2 size={13} className="animate-spin" />
                ) : (
                  <Mic size={13} className="text-emerald-600 dark:text-emerald-400" />
                )}
                <span>{audioMutation.isPending ? 'Syncing...' : 'Regenerate Voiceover'}</span>
              </Button>
            </div>
          </div>

          {/* Active Style Anchor Banner */}
          {(job?.config?.anchor_url || anchorUploadMsg) && (
            <div className="glass-subcard p-3 border-blue-500/40 flex items-center gap-2.5 text-xs">
              {job?.config?.anchor_url && (
                <img
                  src={job.config.anchor_url}
                  alt="Style Anchor"
                  className="w-8 h-8 rounded-lg object-cover border border-blue-500/40"
                />
              )}
              <div>
                <span className="font-bold text-blue-600 dark:text-blue-400">Style Reference Active: </span>
                <span className="text-[var(--tx)]">
                  {anchorUploadMsg || 'Reference image attached to guide visuals'}
                </span>
              </div>
            </div>
          )}

          {/* Storyboard Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {displayScenes.map((sc: any, idx: number) => {
              const isRerolling = activeRerollingIndex === idx;
              const cleanImgPath = sc.image_path ? sc.image_path.replace(/\\/g, '/').replace(/^\/+/, '') : '';
              const thumbUrl = cleanImgPath ? `/${cleanImgPath}` : null;

              return (
                <Card key={idx} className="!p-4 flex flex-col justify-between space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="w-6 h-6 rounded-lg bg-blue-600/15 border border-blue-500/30 text-blue-600 dark:text-blue-400 font-bold text-xs flex items-center justify-center">
                        {idx + 1}
                      </span>
                      <span className="text-xs font-bold uppercase tracking-wider text-[var(--tx)]">
                        {sc.badge || `SHOT ${idx + 1}`}
                      </span>
                    </div>
                    <span className="text-[11px] font-mono text-[var(--mu)] bg-[var(--gl2)] px-2 py-0.5 rounded-lg border border-[var(--ln-subtle)]">
                      {sc.duration ? `${sc.duration}s` : '--'}
                    </span>
                  </div>

                  <div className="flex gap-3">
                    <div className="relative w-24 h-36 rounded-xl bg-slate-950 border border-[var(--ln-subtle)] overflow-hidden shrink-0 flex items-center justify-center">
                      {sc.video_path && (
                        <span className="absolute top-1 right-1 z-10 bg-amber-500 text-slate-950 font-black text-[9px] px-1 py-0.5 rounded shadow">
                          VIDEO
                        </span>
                      )}
                      {thumbUrl ? (
                        <img
                          src={thumbUrl}
                          alt={`Shot ${idx + 1}`}
                          className="w-full h-full object-cover"
                          onError={(e) => {
                            (e.target as HTMLElement).style.display = 'none';
                          }}
                        />
                      ) : (
                        <div className="text-[10px] text-slate-400 font-mono text-center p-1">
                          9:16 Plate
                        </div>
                      )}
                      {(isRerolling || activeUploadingIndex === idx) && (
                        <div className="absolute inset-0 bg-black/75 flex flex-col items-center justify-center gap-1 text-[10px] text-blue-300 z-20">
                          <Loader2 size={16} className="animate-spin text-blue-400" />
                          <span>{activeUploadingIndex === idx ? 'Stitching...' : 'Re-rolling...'}</span>
                        </div>
                      )}
                    </div>

                    <div className="flex-1 flex flex-col justify-between space-y-2 text-xs">
                      <div className="space-y-1">
                        <label className="text-[10px] font-bold uppercase tracking-wider text-[var(--mu)]">
                          Spoken Voiceover
                        </label>
                        <textarea
                          rows={2}
                          value={sc.text || ''}
                          onChange={(e) => handleSceneTextChange(idx, e.target.value)}
                          className="glass-input w-full p-2 text-xs resize-none"
                          placeholder="Spoken narration for this shot..."
                        />
                      </div>

                      <div className="space-y-1">
                        <label className="text-[10px] font-bold uppercase tracking-wider text-[var(--mu)]">
                          Image Prompt
                        </label>
                        <textarea
                          rows={2}
                          value={sc.prompt || `${sc.text}, ${stylePreset}`}
                          onChange={(e) => handleScenePromptChange(idx, e.target.value)}
                          className="glass-input w-full p-2 text-[11px] resize-none font-mono"
                          placeholder="Visual prompt for this scene..."
                        />
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center flex-wrap gap-1.5 pt-2.5 border-t border-[var(--ln-subtle)]">
                    <Button
                      variant="secondary"
                      onClick={() => handleRerollVisual(idx)}
                      disabled={isRerolling || rerollMutation.isPending || activeUploadingIndex === idx || activeAiVideoIndex === idx}
                      className="!py-1.5 !px-2.5"
                    >
                      <RotateCw
                        size={12}
                        className={isRerolling ? 'animate-spin text-blue-500' : 'text-blue-600 dark:text-blue-400'}
                      />
                      <span>{isRerolling ? 'Stitching...' : 'Re-roll'}</span>
                    </Button>

                    <Button
                      variant="secondary"
                      onClick={() => handleGenerateBeatAiVideo(idx)}
                      disabled={activeAiVideoIndex === idx || isRerolling || activeUploadingIndex === idx}
                      className="!py-1.5 !px-2.5"
                      title="Generate real moving AI video clip via Hugging Face ZeroGPU (LTX-2.5 / Wan 2.2) at $0"
                    >
                      {activeAiVideoIndex === idx ? (
                        <Loader2 size={12} className="animate-spin text-amber-500" />
                      ) : (
                        <Clapperboard size={12} className="text-amber-600 dark:text-amber-400" />
                      )}
                      <span>{activeAiVideoIndex === idx ? 'ZeroGPU...' : 'AI Video ($0)'}</span>
                    </Button>

                    <button
                      type="button"
                      onClick={() => {
                        const promptStr = sc.prompt || `${sc.text || job.niche}, ${stylePreset}, 35mm documentary shot`;
                        const refInfo = sc.image_path ? ` [Reference Image: ${sc.image_path}]` : '';
                        navigator.clipboard.writeText(`${promptStr}${refInfo}`);
                        setCopiedFlowIdx(idx);
                        setTimeout(() => setCopiedFlowIdx(null), 2000);
                      }}
                      className="inline-flex items-center justify-center gap-1 text-xs font-semibold py-1.5 px-2.5 rounded-xl border border-[var(--input-border)] bg-[var(--gl2)] hover:border-blue-500 text-[var(--tx)] transition-all cursor-pointer"
                      title="Copy prompt + reference image spec for Google Flow"
                    >
                      {copiedFlowIdx === idx ? (
                        <Check size={12} className="text-emerald-600 dark:text-emerald-400" />
                      ) : (
                        <Copy size={12} className="text-blue-600 dark:text-blue-400" />
                      )}
                      <span>{copiedFlowIdx === idx ? 'Flow Copied' : 'Flow Copy'}</span>
                    </button>

                    <label
                      className="inline-flex items-center justify-center gap-1 text-xs font-semibold py-1.5 px-2.5 rounded-xl border border-[var(--input-border)] bg-[var(--gl2)] hover:border-blue-500 text-[var(--tx)] transition-all cursor-pointer"
                      title="Upload custom video clip (.mp4, .mov from Google Flow) or image"
                    >
                      <input
                        type="file"
                        accept="video/mp4,video/quicktime,video/webm,image/png,image/jpeg,image/webp"
                        className="hidden"
                        disabled={activeUploadingIndex === idx}
                        onChange={(e) => handleUploadCustomMedia(idx, e)}
                      />
                      {activeUploadingIndex === idx ? (
                        <Loader2 size={12} className="animate-spin text-amber-500" />
                      ) : (
                        <Upload size={12} className="text-amber-600 dark:text-amber-400" />
                      )}
                      <span>Clip</span>
                    </label>

                    <Button
                      variant="ghost"
                      onClick={() => handleRegenerateAudio()}
                      disabled={audioMutation.isPending}
                      className="!py-1.5 !px-2"
                      title="Regenerate voiceover"
                    >
                      <Mic size={12} className="text-emerald-600 dark:text-emerald-400" />
                      <span>Voice</span>
                    </Button>
                  </div>

                  {flowHandoffMap[idx] && (
                    <div className="glass-subcard p-2.5 border-amber-500/40 text-[11px] space-y-1.5">
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-bold text-amber-600 dark:text-amber-400">
                          ZeroGPU Quota / Queue Notice: Use Google Flow Handoff
                        </span>
                        <a
                          href={flowHandoffMap[idx].flow_url || 'https://labs.google/fx/tools/flow'}
                          target="_blank"
                          rel="noreferrer"
                          onClick={() => {
                            navigator.clipboard.writeText(flowHandoffMap[idx].prompt);
                          }}
                          className="px-2 py-0.5 rounded-lg bg-blue-600 text-white font-semibold text-[10px] hover:bg-blue-500"
                        >
                          Copy &amp; Open Google Flow
                        </a>
                      </div>
                      <p className="text-[10px] text-[var(--mu)]">
                        Prompt ready in clipboard. Generate your clip in Google Flow and drop the .mp4 into the Clip button above.
                      </p>
                    </div>
                  )}
                </Card>
              );
            })}
          </div>
        </div>
      </div>

      {/* Bottom Action Bar */}
      <Card className="!p-4 sticky bottom-4 z-20 shadow-xl">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center flex-wrap gap-2.5 text-xs">
            <span className="font-bold text-[var(--tx)]">Target Platforms:</span>
            {['TikTok', 'YouTube Shorts', 'Instagram Reels'].map((p) => {
              const isChecked = selectedPlatforms.includes(p);
              return (
                <label
                  key={p}
                  className={`flex items-center gap-2 cursor-pointer px-3 py-1.5 rounded-xl border transition-colors select-none font-medium ${
                    isChecked
                      ? 'bg-blue-600/15 border-blue-500/50 text-[var(--tx)]'
                      : 'bg-[var(--gl2)] border-[var(--input-border)] text-[var(--mu)] hover:text-[var(--tx)]'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={isChecked}
                    onChange={() => togglePlatform(p)}
                    className="accent-blue-600 rounded"
                  />
                  <span>{p}</span>
                </label>
              );
            })}
          </div>

          <div className="flex items-center flex-wrap gap-2.5 w-full sm:w-auto justify-end">
            <Button
              variant="ghost"
              onClick={handleDeleteTemp}
              disabled={deleteTempMutation.isPending}
              className="hover:!text-red-500"
              title="Delete intermediate frames and temp files"
            >
              <Trash2 size={14} />
              <span>{deleteTempMutation.isPending ? 'Cleaning...' : 'Clean Temp'}</span>
            </Button>

            {activeVideoUrl && (
              <a
                href={`/api/jobs/${id}/export`}
                className="inline-flex items-center gap-1.5 text-xs font-semibold py-2 px-3.5 rounded-xl bg-[var(--gl2)] border border-[var(--input-border)] text-[var(--tx)] hover:border-blue-500 transition-colors"
              >
                <Package size={14} className="text-blue-600 dark:text-blue-400" />
                <span>Download .ZIP Pack</span>
              </a>
            )}

            <Button
              onClick={handlePublish}
              disabled={isPublishing || selectedPlatforms.length === 0}
              className="!bg-emerald-600 hover:!bg-emerald-500 !border-emerald-500 text-white !py-2.5 !px-5 shadow-md shadow-emerald-600/20"
            >
              {isPublishing ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />}
              <span>
                {isPublishing
                  ? 'Preparing Pack...'
                  : isPublished
                  ? 'Published'
                  : isReadyToPublish
                  ? 'Ready to Publish'
                  : 'Approve & Prepare Pack'}
              </span>
            </Button>
          </div>
        </div>
      </Card>

      <VideoStudioModal isOpen={isStudioOpen} onClose={() => setIsStudioOpen(false)} job={job} />

      <DirectorChatDrawer
        isOpen={isDirectorChatOpen}
        onClose={() => setIsDirectorChatOpen(false)}
        jobId={Number(id)}
        onVideoUpdated={(newUrl) => {
          setOverrideVideoUrl(newUrl);
        }}
      />
    </div>
  );
}
