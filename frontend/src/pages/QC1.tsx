import { useState, useMemo, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  Play, 
  RotateCw, 
  Mic, 
  Check, 
  Trash2, 
  Eye, 
  EyeOff, 
  ExternalLink, 
  Sparkles, 
  ShieldCheck, 
  Loader2, 
  AlertCircle,
  Download,
  Upload,
  Image as ImageIcon
} from 'lucide-react';
import { 
  useJobs, 
  useRerollVisual, 
  useRegenerateAudio, 
  usePublishJob, 
  useDeleteJobTemp,
  useUploadAnchor
} from '../api/client';
import { Button, Badge, Card } from '../components/ui';
import SafeZoneOverlay from '../components/SafeZoneOverlay';
import VideoStudioModal from '../components/VideoStudioModal';

export default function QC1() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { data: jobs = [] } = useJobs();

  const [showSafeZone, setShowSafeZone] = useState(true);
  const [isStudioOpen, setIsStudioOpen] = useState(false);
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
  const [anchorUploadMsg, setAnchorUploadMsg] = useState<string | null>(null);

  const job = useMemo(() => jobs.find((j: any) => String(j.id) === id), [jobs, id]);

  const videoAsset = job?.assets?.find((a: any) => a.type === 'VIDEO');
  const jobMeta = videoAsset?.metadata || {};
  const videoUrl = jobMeta.video_url || (videoAsset?.path ? `/output/${videoAsset.path.split(/[\\/]/).pop()}` : null);
  const rawScenes = jobMeta.scenes || [];

  // Sync scenes into editable state whenever job or video changes
  useEffect(() => {
    if (rawScenes.length > 0) {
      setEditedScenes(rawScenes);
    }
  }, [id, videoUrl]);

  if (!job) {
    return (
      <div className="p-12 text-center text-slate-400">
        <Loader2 size={24} className="animate-spin mx-auto mb-2 text-blue-500" />
        <p className="text-sm">Loading storyboard details for Job #{id}...</p>
      </div>
    );
  }

  const isPublished = publishedStatus || job.current_stage === 'PUBLISHED' || job.status === 'COMPLETED';
  const displayScenes = editedScenes.length > 0 ? editedScenes : rawScenes;
  const stylePreset = jobMeta.style_preset || job.config?.style_preset || 'Dark Documentary';
  const voiceName = jobMeta.voice || job.config?.voice || 'en-US-AriaNeural';
  const totalDuration = jobMeta.duration ? `${Math.round(jobMeta.duration)}s` : '15s';

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

  const handleRegenerateAudio = async (sceneIndex?: number) => {
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
      setPublishedStatus(res.message || 'Published');
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

  return (
    <div className="animate-in fade-in min-h-full flex flex-col pb-12 max-w-7xl mx-auto space-y-6">
      
      {/* Top Header */}
      <div className="flex justify-between items-center flex-wrap gap-3 pb-2 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-bold tracking-tight text-white">{job.niche}</h1>
            {isPublished ? (
              <Badge variant="success">Published · Active</Badge>
            ) : (
              <Badge variant="warning">QC1 Review Stage</Badge>
            )}
          </div>
          <p className="text-xs text-[var(--mu)] mt-0.5">
            Job #{job.id} · {stylePreset} · {totalDuration} · Voice: {voiceName.split('-')[2] || 'Aria'}
          </p>
        </div>

        <div className="flex items-center gap-2">
          {videoUrl && (
            <a
              href={videoUrl}
              download={`${job.niche.replace(/[^a-zA-Z0-9_-]/g, '_')}_9x16.mp4`}
              className="inline-flex items-center gap-1.5 text-xs font-medium py-2 px-3 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white shadow-sm transition-colors cursor-pointer"
              title="Download 9:16 vertical MP4 video"
            >
              <Download size={14} />
              <span>Download MP4</span>
            </a>
          )}

          <Button
            variant="secondary"
            onClick={() => setIsStudioOpen(true)}
            className="flex items-center gap-1.5 text-xs font-medium !py-2 !px-3 border-slate-700"
          >
            <ExternalLink size={14} />
            <span>Open Studio Inspector</span>
          </Button>

          <Button
            variant="ghost"
            onClick={() => navigate('/create')}
            className="text-xs text-slate-400 hover:text-white !py-2 !px-3"
          >
            + New Video
          </Button>
        </div>
      </div>

      {/* Main Grid: Left 9:16 Video Player | Right Storyboard Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-[340px_1fr] gap-6 items-start">
        
        {/* Left Column: Video Player (Responsive for 16:9 and 9:16) */}
        <div className="flex flex-col items-center space-y-3 sticky top-20">
          {(() => {
            const isWidescreen = job.config?.format === '16:9' || (job.config as any)?.aspect_ratio === '16:9';
            return (
              <>
                <div className="w-full flex items-center justify-between px-1">
                  <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                    {isWidescreen ? '16:9 Widescreen Cinema Player' : '9:16 Reel Player'}
                  </span>
                  {!isWidescreen && (
                    <button
                      onClick={() => setShowSafeZone(!showSafeZone)}
                      className={`flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded border transition-colors ${
                        showSafeZone
                          ? 'bg-cyan-950/80 text-cyan-300 border-cyan-500/50 hover:bg-cyan-900/80'
                          : 'bg-slate-800 text-slate-400 border-slate-700 hover:text-white'
                      }`}
                    >
                      {showSafeZone ? <Eye size={12} /> : <EyeOff size={12} />}
                      <span>{showSafeZone ? 'Safe Zone On' : 'Safe Zone Off'}</span>
                    </button>
                  )}
                </div>

                {isWidescreen ? (
                  /* 16:9 Widescreen Cinema Container */
                  <div className="relative w-full max-w-[560px] aspect-video rounded-2xl p-2 bg-gradient-to-b from-slate-700 via-slate-800 to-slate-900 border-2 border-slate-600 shadow-2xl flex items-center justify-center overflow-hidden">
                    <div className="relative w-full h-full rounded-xl overflow-hidden bg-black flex items-center justify-center">
                      {videoUrl ? (
                        <video
                          controls
                          playsInline
                          autoPlay
                          loop
                          key={videoUrl}
                          src={videoUrl}
                          className="w-full h-full object-contain"
                        />
                      ) : (
                        <div className="text-center p-6 text-slate-500 text-xs flex flex-col items-center gap-2">
                          <Loader2 size={24} className="animate-spin text-blue-500" />
                          <span>Assembling 16:9 widescreen video stream...</span>
                        </div>
                      )}
                    </div>
                  </div>
                ) : (
                  /* 9:16 Phone Container */
                  <div className="relative w-[320px] h-[568px] rounded-[36px] p-2.5 bg-gradient-to-b from-slate-700 via-slate-800 to-slate-900 border-2 border-slate-600 shadow-2xl flex items-center justify-center overflow-hidden">
                    {/* Dynamic Island Notch */}
                    <div className="absolute top-3.5 left-1/2 -translate-x-1/2 w-24 h-4 bg-black rounded-full z-40 border border-white/10" />

                    <div className="relative w-full h-full rounded-[26px] overflow-hidden bg-black flex items-center justify-center">
                      {videoUrl ? (
                        <video
                          controls
                          playsInline
                          autoPlay
                          loop
                          key={videoUrl}
                          src={videoUrl}
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <div className="text-center p-6 text-slate-500 text-xs flex flex-col items-center gap-2">
                          <Loader2 size={24} className="animate-spin text-blue-500" />
                          <span>Assembling 9:16 video stream...</span>
                        </div>
                      )}

                      {/* Toggleable Safe Zone Overlay */}
                      <SafeZoneOverlay
                        visible={showSafeZone}
                        caption={jobMeta.script?.hook || `The breakdown of ${job.niche}`}
                      />
                    </div>
                  </div>
                )}

                <div className="w-full flex items-center justify-between text-[11px] text-slate-500 px-2 font-mono">
                  <span>{isWidescreen ? '1920 × 1080 Widescreen MP4' : '1080 × 1920 MP4'}</span>
                  <span>-14 LUFS Audio</span>
                </div>
              </>
            );
          })()}
        </div>

        {/* Right Column: Storyboard Grid (Shot Cards) */}
        <div className="space-y-4">
          
          <div className="flex items-center justify-between pb-1">
            <div>
              <h2 className="text-base font-semibold text-white">Storyboard & Shot Inspector</h2>
              <p className="text-xs text-[var(--mu)]">
                Edit script lines, adjust image prompts, or re-roll visuals in 8 seconds.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <label className="cursor-pointer flex items-center gap-1.5 text-xs py-1.5 px-3 rounded-lg border border-slate-700 bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors">
                {uploadAnchorMutation.isPending ? <Loader2 size={13} className="animate-spin text-blue-400" /> : <Upload size={13} className="text-blue-400" />}
                <span>{uploadAnchorMutation.isPending ? 'Uploading...' : 'Upload Style Anchor'}</span>
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
                      } catch (err) {
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
                className="flex items-center gap-1.5 text-xs !py-1.5 !px-3 border-slate-700"
              >
                {audioMutation.isPending ? <Loader2 size={13} className="animate-spin" /> : <Mic size={13} className="text-emerald-400" />}
                <span>{audioMutation.isPending ? 'Syncing...' : 'Regenerate Voiceover'}</span>
              </Button>
            </div>
          </div>

          {/* Active Style Anchor Banner */}
          {(job?.config?.anchor_url || anchorUploadMsg) && (
            <div className="flex items-center justify-between p-2.5 px-3 rounded-xl bg-blue-950/30 border border-blue-500/30 text-xs">
              <div className="flex items-center gap-2.5">
                {job?.config?.anchor_url && (
                  <img src={job.config.anchor_url} alt="Style Anchor" className="w-8 h-8 rounded-lg object-cover border border-blue-500/40" />
                )}
                <div>
                  <span className="font-semibold text-blue-300">Style Reference Active: </span>
                  <span className="text-slate-300">{anchorUploadMsg || 'Reference image attached to guide visuals'}</span>
                </div>
              </div>
            </div>
          )}

          {/* Storyboard Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {displayScenes.map((sc: any, idx: number) => {
              const isRerolling = activeRerollingIndex === idx;
              const thumbUrl = sc.image_path ? `/${sc.image_path.replace(/\\/g, '/')}` : null;

              return (
                <Card
                  key={idx}
                  className="!p-4 bg-slate-900/70 border-slate-700/80 flex flex-col justify-between space-y-3 hover:border-slate-600 transition-all shadow-md"
                >
                  {/* Card Header & Badge */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="w-6 h-6 rounded-md bg-blue-600/20 border border-blue-500/30 text-blue-400 font-bold text-xs flex items-center justify-center">
                        {idx + 1}
                      </span>
                      <span className="text-xs font-bold uppercase tracking-wider text-sky-300">
                        {sc.badge || `SHOT ${idx + 1}`}
                      </span>
                    </div>
                    <span className="text-[11px] font-mono text-slate-400 bg-slate-800/80 px-2 py-0.5 rounded border border-slate-700">
                      {sc.duration ? `${sc.duration}s` : '4s'}
                    </span>
                  </div>

                  {/* Thumbnail & Prompt Preview */}
                  <div className="flex gap-3">
                    {/* Visual Plate Thumbnail */}
                    <div className="relative w-24 h-36 rounded-lg bg-slate-950 border border-slate-800 overflow-hidden shrink-0 flex items-center justify-center">
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
                        <div className="text-[10px] text-slate-500 font-mono text-center p-1">9:16 Plate</div>
                      )}
                      {isRerolling && (
                        <div className="absolute inset-0 bg-black/75 flex flex-col items-center justify-center gap-1 text-[10px] text-blue-300">
                          <Loader2 size={16} className="animate-spin text-blue-400" />
                          <span>Re-rolling...</span>
                        </div>
                      )}
                    </div>

                    {/* Editable Spoken Script & Prompt */}
                    <div className="flex-1 flex flex-col justify-between space-y-2 text-xs">
                      <div className="space-y-1">
                        <label className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                          Spoken Voiceover
                        </label>
                        <textarea
                          rows={2}
                          value={sc.text || ''}
                          onChange={(e) => handleSceneTextChange(idx, e.target.value)}
                          className="w-full p-2 rounded-lg bg-slate-950/70 border border-slate-800 text-slate-200 text-xs outline-none focus:border-blue-500 resize-none"
                          placeholder="Spoken narration for this shot..."
                        />
                      </div>

                      <div className="space-y-1">
                        <label className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                          Image Prompt
                        </label>
                        <textarea
                          rows={2}
                          value={sc.prompt || `${sc.text}, ${stylePreset}`}
                          onChange={(e) => handleScenePromptChange(idx, e.target.value)}
                          className="w-full p-2 rounded-lg bg-slate-950/70 border border-slate-800 text-slate-400 text-[11px] outline-none focus:border-blue-500 resize-none font-mono"
                          placeholder="Visual prompt for this scene..."
                        />
                      </div>
                    </div>
                  </div>

                  {/* Two Quick Buttons: Re-roll Visual & Regenerate Audio */}
                  <div className="flex items-center gap-2 pt-2 border-t border-slate-800">
                    <Button
                      variant="secondary"
                      onClick={() => handleRerollVisual(idx)}
                      disabled={isRerolling || rerollMutation.isPending}
                      className="flex-1 flex items-center justify-center gap-1.5 text-xs !py-1.5 border-slate-700 hover:border-blue-500 text-slate-200"
                    >
                      <RotateCw size={13} className={isRerolling ? 'animate-spin text-blue-400' : 'text-blue-400'} />
                      <span>{isRerolling ? 'Stitching Video...' : 'Re-roll Visual'}</span>
                    </Button>

                    <Button
                      variant="ghost"
                      onClick={() => handleRegenerateAudio(idx)}
                      disabled={audioMutation.isPending}
                      className="flex items-center justify-center gap-1 text-xs !py-1.5 text-slate-400 hover:text-white"
                      title="Regenerate voiceover for this shot"
                    >
                      <Mic size={13} className="text-emerald-400" />
                      <span>Voice</span>
                    </Button>
                  </div>

                </Card>
              );
            })}
          </div>

        </div>

      </div>

      {/* Bottom Action Bar */}
      <Card className="!p-4 bg-slate-900/90 border-slate-700/90 sticky bottom-4 z-20 shadow-2xl backdrop-blur-md">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
          
          {/* Platform Checkboxes & Cookie Status */}
          <div className="flex items-center flex-wrap gap-4 text-xs">
            <span className="font-semibold text-slate-300">Platforms:</span>
            {['TikTok', 'YouTube Shorts', 'Instagram Reels'].map((p) => {
              const isChecked = selectedPlatforms.includes(p);
              return (
                <label
                  key={p}
                  className={`flex items-center gap-2 cursor-pointer px-2.5 py-1.5 rounded-lg border transition-colors select-none ${
                    isChecked
                      ? 'bg-blue-950/60 border-blue-500/60 text-white'
                      : 'bg-slate-950/40 border-slate-800 text-slate-400 hover:text-white'
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

            {/* Cookie Status Badge */}
            <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-emerald-950/40 border border-emerald-500/40 text-emerald-300 text-xs font-medium">
              <ShieldCheck size={14} className="text-emerald-400" />
              <span>Cookie Status: Active</span>
            </div>
          </div>

          {/* Action Buttons: Approve & Publish + Clean Temp */}
          <div className="flex items-center gap-3 w-full sm:w-auto justify-end">
            <Button
              variant="ghost"
              onClick={handleDeleteTemp}
              disabled={deleteTempMutation.isPending}
              className="text-xs text-slate-400 hover:text-red-400 flex items-center gap-1.5 !py-2"
              title="Delete intermediate frames and temp files"
            >
              <Trash2 size={14} />
              <span>{deleteTempMutation.isPending ? 'Cleaning...' : 'Delete & Clean Temp Files'}</span>
            </Button>

            <Button
              onClick={handlePublish}
              disabled={isPublishing || selectedPlatforms.length === 0}
              className="bg-emerald-600 hover:bg-emerald-500 text-white flex items-center gap-2 text-xs font-semibold !py-2.5 !px-5 rounded-xl shadow-lg shadow-emerald-600/25 transition-all"
            >
              {isPublishing ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />}
              <span>{isPublishing ? 'Publishing...' : isPublished ? 'Approved & Published' : 'Approve & Publish'}</span>
            </Button>
          </div>

        </div>
      </Card>

      {/* 9:16 Studio Inspector Modal */}
      <VideoStudioModal
        isOpen={isStudioOpen}
        onClose={() => setIsStudioOpen(false)}
        job={job}
      />

    </div>
  );
}
