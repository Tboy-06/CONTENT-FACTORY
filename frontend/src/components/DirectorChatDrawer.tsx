import React, { useState, useRef, useEffect, ChangeEvent } from 'react';
import { 
  Sparkles, 
  X, 
  Send, 
  Upload, 
  Film, 
  Sliders, 
  Cpu, 
  Cloud, 
  Zap, 
  Loader2, 
  CheckCircle2, 
  AlertCircle, 
  RefreshCw, 
  ChevronDown, 
  ChevronUp, 
  Volume2, 
  Layers, 
  FileText,
  Play,
  Download,
  Scissors,
  Link as LinkIcon
} from 'lucide-react';
import { Button, Badge, Card } from './ui';
import { 
  useAnalyzeVideo, 
  useDirectorChat, 
  VideoContext, 
  DirectorChatResponse 
} from '../api/client';
import { useNavigate } from 'react-router-dom';

interface Message {
  id: string;
  role: 'user' | 'director';
  content: string;
  actions?: any[];
  executedActions?: any[];
  videoUrl?: string;
  newJobId?: number;
  timestamp: Date;
}

interface DirectorChatDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  jobId?: number;
  onVideoUpdated?: (newVideoUrl: string) => void;
}

export default function DirectorChatDrawer({
  isOpen,
  onClose,
  jobId,
  onVideoUpdated
}: DirectorChatDrawerProps) {
  const navigate = useNavigate();
  const [engineMode, setEngineMode] = useState<'auto' | 'offline_spark' | 'cloud'>('auto');
  const [prompt, setPrompt] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [videoContext, setVideoContext] = useState<VideoContext | null>(null);
  const [showTranscript, setShowTranscript] = useState(false);
  const [showUrlInput, setShowUrlInput] = useState(false);
  const [ytUrl, setYtUrl] = useState('');
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const analyzeMutation = useAnalyzeVideo();
  const chatMutation = useDirectorChat();

  // Scroll to bottom on new message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, chatMutation.isPending]);

  // Initial welcome message if conversation is empty
  useEffect(() => {
    if (messages.length === 0) {
      setMessages([
        {
          id: 'welcome',
          role: 'director',
          content: jobId 
            ? `AI Creative Director standing by for **Job #${jobId}**. You can instruct me in natural language to re-render timeline beats, swap forensic document styles, change pacing, or re-grade shots.`
            : `AI Creative Director standing by. Upload any reference or raw video to deconstruct its pacing and edit it, or type your creative instructions.`,
          timestamp: new Date()
        }
      ]);
    }
  }, [jobId]);

  if (!isOpen) return null;

  // Handle Video Upload & Deconstruction
  const handleFileUpload = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setStatusMsg(`Ingesting & analyzing ${file.name}...`);
    try {
      const res = await analyzeMutation.mutateAsync({ file });
      setVideoContext(res);
      setStatusMsg(null);
      setMessages(prev => [
        ...prev,
        {
          id: String(Date.now()),
          role: 'director',
          content: `🎬 **Video Deconstructed Successfully**: \`${file.name}\`\n\n` +
            `• **Pacing**: ${res.pacing?.cuts_per_minute || 0} cuts/min (cut every ${res.pacing?.avg_cut_interval || 0}s)\n` +
            `• **Dialogue**: ${res.audio?.words_per_minute || 0} WPM (${res.audio?.total_words || 0} spoken words)\n` +
            `• **Dead Air**: ${res.audio?.total_silence_seconds || 0}s silence detected\n` +
            `• **Dimensions**: ${res.dimensions?.width}x${res.dimensions?.height} (${res.dimensions?.aspect_ratio})`,
          timestamp: new Date()
        }
      ]);
    } catch (err: any) {
      setStatusMsg(`Analysis failed: ${err.message || err}`);
    }
  };

  // Handle Deconstructing Current Job Video
  const handleDeconstructCurrentJob = async () => {
    if (!jobId) return;
    setStatusMsg(`Deconstructing Job #${jobId} video...`);
    try {
      const res = await analyzeMutation.mutateAsync({ jobId });
      setVideoContext(res);
      setStatusMsg(null);
      setMessages(prev => [
        ...prev,
        {
          id: String(Date.now()),
          role: 'director',
          content: `📊 **Job #${jobId} Storyboard Deconstructed**:\n\n` +
            `• **Pacing**: ${res.pacing?.cuts_per_minute || 0} cuts/min (avg cut ${res.pacing?.avg_cut_interval || 0}s)\n` +
            `• **Pacing Rhythm**: 16 beats across ${res.duration || 50}s (${res.dimensions?.aspect_ratio})\n` +
            `• **Narration**: ${res.audio?.words_per_minute || 0} WPM (${res.audio?.total_words || 0} words)\n` +
            `What modifications would you like me to execute?`,
          timestamp: new Date()
        }
      ]);
    } catch (err: any) {
      setStatusMsg(`Job analysis failed: ${err.message || err}`);
    }
  };

  // Send Director Chat Command
  const handleSendMessage = async (textToSend?: string) => {
    const text = (textToSend || prompt).trim();
    if (!text || chatMutation.isPending) return;

    const userMsg: Message = {
      id: String(Date.now()),
      role: 'user',
      content: text,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMsg]);
    if (!textToSend) setPrompt('');

    try {
      const historyPayload = messages.map(m => ({
        role: m.role === 'user' ? 'user' : 'assistant',
        content: m.content
      }));

      const res: DirectorChatResponse = await chatMutation.mutateAsync({
        prompt: text,
        jobId,
        videoContext,
        engineMode,
        history: historyPayload
      });

      const directorMsg: Message = {
        id: String(Date.now() + 1),
        role: 'director',
        content: res.message || 'Operation executed.',
        actions: res.actions,
        executedActions: res.executed_actions,
        videoUrl: res.video_url,
        newJobId: res.job_id,
        timestamp: new Date()
      };

      setMessages(prev => [...prev, directorMsg]);

      // If video was updated, notify parent player
      if (res.video_url && onVideoUpdated) {
        onVideoUpdated(res.video_url);
      }
    } catch (err: any) {
      setMessages(prev => [
        ...prev,
        {
          id: String(Date.now() + 1),
          role: 'director',
          content: `⚠️ Error executing director instruction: ${err.message || err}`,
          timestamp: new Date()
        }
      ]);
    }
  };

  const quickPrompts = jobId ? [
    "✂️ Extract top 3 viral shorts from this",
    "🗺️ Change Beat 3 to radar map flyover with headline TARGET DETECTED",
    "🎨 Switch Beat 5 to grade teal_split",
    "⚡ Boost pacing: tighten timeline cuts",
    "📋 Swap Beat 7 to declassified dossier with yellow highlighter"
  ] : [
    "✂️ Extract top 3 viral shorts from this video",
    "🎬 Clone this pacing into a video about CIA Project Azorian",
    "✂️ Cut dead air pauses and burn yellow subtitles",
    "🎨 Apply 35mm hard black-and-white film grade"
  ];

  return (
    <div className="fixed inset-y-0 right-0 z-50 w-full sm:w-[500px] md:w-[560px] bg-slate-950/95 border-l border-slate-800 shadow-2xl flex flex-col backdrop-blur-xl animate-in slide-in-from-right duration-200">
      
      {/* Top Header */}
      <div className="p-4 border-b border-slate-800/80 flex items-center justify-between bg-slate-900/40">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-400">
            <Sparkles size={18} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-bold text-white tracking-wide">AI Director Studio</h2>
              {jobId && (
                <span className="text-[10px] uppercase font-semibold px-2 py-0.5 rounded-full bg-blue-900/60 border border-blue-600/40 text-blue-300">
                  Job #{jobId}
                </span>
              )}
            </div>
            <p className="text-[11px] text-slate-400">Agentic timeline commands & video deconstruction</p>
          </div>
        </div>

        <button 
          onClick={onClose}
          className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800/60 transition-colors"
          title="Close Director Studio"
        >
          <X size={18} />
        </button>
      </div>

      {/* Model Engine Selector */}
      <div className="px-4 py-2.5 border-b border-slate-800/60 bg-slate-900/20 flex items-center justify-between text-xs">
        <span className="text-slate-400 font-medium flex items-center gap-1.5">
          <Sliders size={13} className="text-slate-400" />
          Model Router:
        </span>
        <div className="flex items-center gap-1 bg-slate-900/90 p-0.5 rounded-lg border border-slate-800">
          <button
            onClick={() => setEngineMode('offline_spark')}
            className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-all flex items-center gap-1.5 ${
              engineMode === 'offline_spark'
                ? 'bg-emerald-950 border border-emerald-500/50 text-emerald-300 shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
            title="Local Ollama Spark-X2.5-4B (0 MB VRAM, 100% Offline, $0 Spend)"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
            Offline Spark
          </button>

          <button
            onClick={() => setEngineMode('auto')}
            className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-all flex items-center gap-1.5 ${
              engineMode === 'auto'
                ? 'bg-blue-950 border border-blue-500/50 text-blue-300 shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
            title="Auto Hybrid Router (Gemini Free Tier -> Local Failover)"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-blue-400"></span>
            Auto Hybrid
          </button>

          <button
            onClick={() => setEngineMode('cloud')}
            className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-all flex items-center gap-1.5 ${
              engineMode === 'cloud'
                ? 'bg-violet-950 border border-violet-500/50 text-violet-300 shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
            title="Cloud Models (Gemini / Kimi K3)"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-violet-400"></span>
            Cloud
          </button>
        </div>
      </div>

      {/* Video Deconstruction Bar */}
      <div className="px-4 py-2 border-b border-slate-800/60 bg-slate-900/30 flex items-center justify-between gap-2 text-xs">
        <input 
          type="file"
          ref={fileInputRef}
          onChange={handleFileUpload}
          accept="video/mp4,video/quicktime,video/webm"
          className="hidden"
        />

        <div className="flex items-center gap-2 overflow-x-auto py-0.5">
          <Button
            variant="ghost"
            onClick={() => fileInputRef.current?.click()}
            disabled={analyzeMutation.isPending}
            className="!py-1 !px-2.5 text-[11px] bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 flex items-center gap-1.5 rounded-lg"
            title="Upload reference video (.mp4/.mov) stored safely on C:\cf_training\temp\uploads"
          >
            {analyzeMutation.isPending ? <Loader2 size={12} className="animate-spin text-amber-400" /> : <Upload size={12} className="text-amber-400" />}
            <span>Upload Video</span>
          </Button>

          <Button
            variant="ghost"
            onClick={() => setShowUrlInput(prev => !prev)}
            className="!py-1 !px-2.5 text-[11px] bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 flex items-center gap-1.5 rounded-lg"
            title="Paste YouTube link to extract viral shorts"
          >
            <LinkIcon size={12} className="text-red-400" />
            <span>YouTube URL</span>
          </Button>

          {jobId && (
            <Button
              variant="ghost"
              onClick={handleDeconstructCurrentJob}
              disabled={analyzeMutation.isPending}
              className="!py-1 !px-2.5 text-[11px] bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 flex items-center gap-1.5 rounded-lg"
              title="Deconstruct the current active job's video pacing and speech telemetry"
            >
              <Film size={12} className="text-blue-400" />
              <span>Deconstruct Job</span>
            </Button>
          )}
        </div>

        {videoContext && (
          <button
            onClick={() => setShowTranscript(prev => !prev)}
            className="text-[11px] text-slate-400 hover:text-white flex items-center gap-1 shrink-0 px-2 py-1 rounded bg-slate-800/40 border border-slate-700/50"
          >
            <FileText size={11} className="text-emerald-400" />
            <span>Telemetry</span>
            {showTranscript ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          </button>
        )}
      </div>

      {/* YouTube URL Quick Clipper Bar */}
      {showUrlInput && (
        <div className="px-4 py-2 bg-slate-900/60 border-b border-slate-800/80 flex items-center gap-2 text-xs animate-in fade-in">
          <input
            type="url"
            value={ytUrl}
            onChange={(e) => setYtUrl(e.target.value)}
            placeholder="Paste YouTube URL: https://youtube.com/watch?v=..."
            className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-slate-200 text-xs focus:outline-none focus:border-red-500 font-mono"
            onKeyDown={(e) => {
              if (e.key === 'Enter' && ytUrl.trim()) {
                handleSendMessage(`Extract top 3 viral shorts from this: ${ytUrl.trim()}`);
                setYtUrl('');
                setShowUrlInput(false);
              }
            }}
          />
          <Button
            onClick={() => {
              if (ytUrl.trim()) {
                handleSendMessage(`Extract top 3 viral shorts from this: ${ytUrl.trim()}`);
                setYtUrl('');
                setShowUrlInput(false);
              }
            }}
            disabled={!ytUrl.trim() || chatMutation.isPending}
            className="!py-1.5 !px-3 text-xs bg-red-600 hover:bg-red-500 text-white rounded-lg flex items-center gap-1 font-semibold"
          >
            <Scissors size={12} />
            <span>Extract Shorts</span>
          </Button>
        </div>
      )}

      {/* Video Telemetry Dropdown */}
      {videoContext && showTranscript && (
        <div className="p-3 bg-slate-900/90 border-b border-slate-800 text-xs space-y-2 animate-in fade-in">
          <div className="grid grid-cols-4 gap-2 text-center">
            <div className="p-2 rounded-lg bg-slate-950/80 border border-slate-800">
              <span className="block text-[10px] text-slate-400 uppercase">Pacing</span>
              <span className="text-xs font-bold text-amber-400">{videoContext.pacing?.cuts_per_minute || 0} cuts/m</span>
            </div>
            <div className="p-2 rounded-lg bg-slate-950/80 border border-slate-800">
              <span className="block text-[10px] text-slate-400 uppercase">Avg Cut</span>
              <span className="text-xs font-bold text-blue-400">{videoContext.pacing?.avg_cut_interval || 0}s</span>
            </div>
            <div className="p-2 rounded-lg bg-slate-950/80 border border-slate-800">
              <span className="block text-[10px] text-slate-400 uppercase">Speech</span>
              <span className="text-xs font-bold text-emerald-400">{videoContext.audio?.words_per_minute || 0} WPM</span>
            </div>
            <div className="p-2 rounded-lg bg-slate-950/80 border border-slate-800">
              <span className="block text-[10px] text-slate-400 uppercase">Dead Air</span>
              <span className="text-xs font-bold text-red-400">{videoContext.audio?.total_silence_seconds || 0}s</span>
            </div>
          </div>

          {videoContext.full_text && (
            <div className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800 max-h-24 overflow-y-auto text-[11px] text-slate-300 leading-relaxed font-mono">
              <span className="text-slate-500 font-bold block mb-1">TRANSCRIPTION:</span>
              "{videoContext.full_text}"
            </div>
          )}
        </div>
      )}

      {/* Status banner */}
      {statusMsg && (
        <div className="px-4 py-2 bg-blue-950/60 border-b border-blue-900/50 text-blue-300 text-xs flex items-center gap-2">
          <Loader2 size={13} className="animate-spin shrink-0" />
          <span>{statusMsg}</span>
        </div>
      )}

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((m) => {
          const isUser = m.role === 'user';
          return (
            <div key={m.id} className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>
              <div
                className={`max-w-[88%] rounded-2xl p-3.5 text-xs leading-relaxed ${
                  isUser
                    ? 'bg-blue-600 text-white rounded-br-sm shadow-md'
                    : 'bg-slate-900/90 border border-slate-800 text-slate-200 rounded-bl-sm shadow-lg'
                }`}
              >
                {!isUser && (
                  <div className="flex items-center gap-1.5 mb-2 pb-1.5 border-b border-slate-800/80 text-[10px] font-semibold text-amber-400 uppercase tracking-wider">
                    <Sparkles size={11} />
                    <span>Creative Director</span>
                  </div>
                )}

                <div className="whitespace-pre-wrap font-sans">{m.content}</div>

                {/* Executed Action Cards */}
                {m.executedActions && m.executedActions.length > 0 && (
                  <div className="mt-3 pt-2.5 border-t border-slate-800/80 space-y-2">
                    {m.executedActions.map((act: any, idx: number) => {
                      if (act.action === 'modify_timeline_beats') {
                        return (
                          <div 
                            key={idx}
                            className="p-2 rounded-lg bg-emerald-950/40 border border-emerald-500/40 flex items-center justify-between text-[11px] text-emerald-300"
                          >
                            <div className="flex items-center gap-1.5">
                              <CheckCircle2 size={13} className="text-emerald-400 shrink-0" />
                              <span>Timeline Updated: Beats #{act.modified_beats?.map((b: number) => b + 1).join(', ')} re-stitched</span>
                            </div>
                            {act.video_url && (
                              <button
                                onClick={() => onVideoUpdated?.(act.video_url)}
                                className="px-2 py-0.5 rounded bg-emerald-800/50 hover:bg-emerald-700/60 text-white font-medium text-[10px] flex items-center gap-1"
                              >
                                <Play size={10} />
                                Refresh Video
                              </button>
                            )}
                          </div>
                        );
                      }

                      if (act.action === 'clone_reference_style') {
                        return (
                          <div 
                            key={idx}
                            className="p-2 rounded-lg bg-blue-950/40 border border-blue-500/40 flex items-center justify-between text-[11px] text-blue-300"
                          >
                            <div className="flex items-center gap-1.5">
                              <Zap size={13} className="text-blue-400 shrink-0" />
                              <span>Created New Job #{act.new_job_id}</span>
                            </div>
                            <button
                              onClick={() => navigate(`/qc1/${act.new_job_id}`)}
                              className="px-2 py-0.5 rounded bg-blue-800/50 hover:bg-blue-700/60 text-white font-medium text-[10px]"
                            >
                              Open Job #{act.new_job_id}
                            </button>
                          </div>
                        );
                      }

                      if (act.action === 'edit_uploaded_video') {
                        return (
                          <div 
                            key={idx}
                            className="p-2 rounded-lg bg-amber-950/40 border border-amber-500/40 flex items-center justify-between text-[11px] text-amber-300"
                          >
                            <div className="flex items-center gap-1.5">
                              <Film size={13} className="text-amber-400 shrink-0" />
                              <span>Uploaded Video Processed</span>
                            </div>
                            {act.video_url && (
                              <a
                                href={act.video_url}
                                target="_blank"
                                rel="noreferrer"
                                className="px-2 py-0.5 rounded bg-amber-800/50 hover:bg-amber-700/60 text-white font-medium text-[10px]"
                              >
                                View Output
                              </a>
                            )}
                          </div>
                        );
                      }

                      if (act.action === 'slice_viral_shorts' || (act.shorts && act.shorts.length > 0)) {
                        const shortsList = act.shorts || [];
                        return (
                          <div 
                            key={idx}
                            className="p-3 rounded-xl bg-purple-950/40 border border-purple-500/40 space-y-3 text-purple-200 mt-2"
                          >
                            <div className="flex items-center justify-between border-b border-purple-500/30 pb-2">
                              <div className="flex items-center gap-2 font-bold text-purple-300 text-xs">
                                <Scissors size={14} className="text-purple-400 shrink-0" />
                                <span>{shortsList.length} Viral Shorts Extracted (9:16 Vertical · Karaoke Subtitles)</span>
                              </div>
                            </div>

                            <div className="space-y-3 pt-1">
                              {shortsList.map((sh: any, sIdx: number) => (
                                <div key={sIdx} className="p-2.5 rounded-lg bg-slate-950/80 border border-purple-500/30 space-y-2">
                                  <div className="flex items-center justify-between text-[11px]">
                                    <span className="font-bold text-white tracking-wide truncate max-w-[220px]">
                                      #{sh.id} · {sh.title}
                                    </span>
                                    <div className="flex items-center gap-1.5 font-mono text-[10px] text-purple-300">
                                      <span className="bg-purple-900/60 px-1.5 py-0.5 rounded border border-purple-600/40">{sh.duration}s</span>
                                      <span className="text-slate-400">{sh.start}s - {sh.end}s</span>
                                    </div>
                                  </div>

                                  {sh.hook_text && (
                                    <p className="text-[10px] text-slate-300 italic line-clamp-2 border-l-2 border-purple-400 pl-2">
                                      "{sh.hook_text}"
                                    </p>
                                  )}

                                  {sh.video_url && (
                                    <div className="relative rounded-lg overflow-hidden border border-slate-800 bg-black aspect-[9/16] max-h-[200px] mx-auto shadow-inner">
                                      <video
                                        src={sh.video_url}
                                        poster={sh.thumb_url}
                                        controls
                                        playsInline
                                        className="w-full h-full object-contain"
                                      />
                                    </div>
                                  )}

                                  <div className="flex items-center justify-end gap-2 pt-1">
                                    {sh.video_url && onVideoUpdated && (
                                      <button
                                        onClick={() => onVideoUpdated(sh.video_url)}
                                        className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[10px] flex items-center gap-1 font-medium transition-colors"
                                        title="Preview this short in QC1 player"
                                      >
                                        <Play size={10} />
                                        Preview in QC1
                                      </button>
                                    )}
                                    {sh.video_url && (
                                      <a
                                        href={sh.video_url}
                                        download={`viral_short_${sh.id}.mp4`}
                                        className="px-2.5 py-1 rounded bg-purple-600 hover:bg-purple-500 text-white font-medium text-[10px] flex items-center gap-1 transition-colors"
                                      >
                                        <Download size={10} />
                                        Download 9:16
                                      </a>
                                    )}
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        );
                      }

                      return null;
                    })}
                  </div>
                )}

              </div>
              <span className="text-[9px] text-slate-500 mt-1 px-1">
                {m.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
            </div>
          );
        })}

        {chatMutation.isPending && (
          <div className="flex items-start gap-2 text-xs text-slate-400 bg-slate-900/60 p-3 rounded-2xl border border-slate-800 w-fit">
            <Loader2 size={14} className="animate-spin text-amber-400" />
            <span>Director is analyzing timeline, re-rendering frames, and mixing audio...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Quick Prompts Bar */}
      <div className="px-4 py-2 border-t border-slate-800/60 bg-slate-900/20">
        <span className="text-[10px] uppercase font-bold text-slate-500 block mb-1.5">Director Suggestions</span>
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 no-scrollbar">
          {quickPrompts.map((qp, idx) => (
            <button
              key={idx}
              onClick={() => handleSendMessage(qp)}
              disabled={chatMutation.isPending}
              className="text-[11px] px-2.5 py-1 rounded-full bg-slate-900 hover:bg-slate-800 border border-slate-800 hover:border-slate-700 text-slate-300 hover:text-white whitespace-nowrap transition-colors shrink-0"
            >
              {qp}
            </button>
          ))}
        </div>
      </div>

      {/* Input Form */}
      <div className="p-3.5 border-t border-slate-800 bg-slate-900/60">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSendMessage();
          }}
          className="relative flex items-center gap-2"
        >
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSendMessage();
              }
            }}
            placeholder="Instruct the director: 'Change Beat 3 to a radar map flyover', 'Cut dead air'..."
            rows={2}
            className="w-full rounded-xl bg-slate-950 border border-slate-800 focus:border-amber-500/60 focus:ring-1 focus:ring-amber-500/40 text-xs text-white placeholder-slate-500 p-2.5 pr-10 resize-none outline-none leading-relaxed"
          />

          <button
            type="submit"
            disabled={!prompt.trim() || chatMutation.isPending}
            className="absolute right-2.5 bottom-2.5 p-2 rounded-lg bg-amber-500 hover:bg-amber-400 disabled:opacity-30 disabled:hover:bg-amber-500 text-slate-950 transition-all font-semibold"
            title="Execute Director Command"
          >
            {chatMutation.isPending ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <Send size={14} />
            )}
          </button>
        </form>
      </div>

    </div>
  );
}
