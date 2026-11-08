import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Zap, Loader2 } from 'lucide-react';
import { Button, Card, EmptyState } from '../components/ui';
import { useCreateInstantJob, api } from '../api/client';

const creationModes = [
  { id: 'idea', title: 'From idea', desc: 'Turn your idea into a video', bg: 'https://images.unsplash.com/photo-1522202176988-66273c2fd55f?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80' },
  { id: 'clone', title: 'Clone a video', desc: 'Reuse a reference video\'s structure', bg: 'https://images.unsplash.com/photo-1611162617474-5b21e879e113?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80' },
  { id: 'shorts', title: 'Create shorts', desc: 'YouTube Shorts, TikTok, Reels', bg: 'https://images.unsplash.com/photo-1551288049-bebda4e38f71?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80' },
  { id: 'ugc', title: 'Create UGC', desc: 'Creator-style product videos', bg: 'https://images.unsplash.com/photo-1516321318423-f06f85e504b3?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80' },
  { id: 'url', title: 'From URL', desc: 'Turn a blog post into a video', bg: 'https://images.unsplash.com/photo-1432821596592-e2c18b78144f?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80' },
  { id: 'clip', title: 'Clip a long video', desc: 'Cut your own footage into shorts', bg: 'https://images.unsplash.com/photo-1536440136628-849c177e76a1?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80' }
];

const voices = [
  { id: 'en-US-AriaNeural', label: 'Aria (Female, Clear)' },
  { id: 'en-US-ChristopherNeural', label: 'Christopher (Male, Storytelling)' },
  { id: 'en-US-GuyNeural', label: 'Guy (Male, Conversational)' },
  { id: 'en-US-JennyNeural', label: 'Jenny (Female, Energetic)' }
];

export default function Create() {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(true);
  const [instantTopic, setInstantTopic] = useState('');
  const [selectedVoice, setSelectedVoice] = useState('en-US-AriaNeural');
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationStep, setGenerationStep] = useState('');

  const instantMutation = useCreateInstantJob();

  useEffect(() => {
    const timer = setTimeout(() => setIsLoading(false), 200);
    return () => clearTimeout(timer);
  }, []);

  const handleInstantGenerate = async () => {
    if (!instantTopic.trim() || isGenerating) return;
    setIsGenerating(true);
    setGenerationStep('Initiating pipeline...');

    try {
      const res = await instantMutation.mutateAsync({
        topic: instantTopic.trim(),
        voice: selectedVoice
      });

      const jobId = res.id;
      setGenerationStep('Building audio, subtitles, and scene plates...');

      // Real active polling
      const startTime = Date.now();
      const interval = setInterval(async () => {
        try {
          const jobs = await api.get('/api/jobs');
          const currentJob = jobs.find((j: any) => j.id === jobId);
          
          if (currentJob) {
            if (currentJob.current_stage === 'QC1' || currentJob.status === 'AWAITING_APPROVAL') {
              clearInterval(interval);
              setGenerationStep('Render complete. Directing to Studio Review...');
              setTimeout(() => navigate(`/qc1/${jobId}`), 500);
            } else if (currentJob.status === 'FAILED') {
              clearInterval(interval);
              setIsGenerating(false);
              setGenerationStep('Pipeline failed. Check server logs.');
            } else {
              setGenerationStep(`Active stage: ${currentJob.current_stage || 'Rendering'}`);
            }
          }
        } catch {
          // Ignore transient poll failures
        }

        // Timeout safeguard after 60s
        if (Date.now() - startTime > 60000) {
          clearInterval(interval);
          navigate(`/qc1/${jobId}`);
        }
      }, 1500);

    } catch (e) {
      console.error(e);
      setIsGenerating(false);
      setGenerationStep('Generation failed. Please try again.');
    }
  };

  return (
    <div className="animate-in fade-in min-h-full flex flex-col pb-8 space-y-6">
      <div className="flex justify-between items-center flex-wrap gap-3">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight">Create a New Video</h1>
          <div className="text-[var(--mu)] text-[13px]">Enter a topic for instant generation or choose an advanced method.</div>
        </div>
      </div>

      {/* Instant 1-Click Video Generator Card */}
      <Card className="!p-6 bg-slate-900/60 border-slate-700/70 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white">
              <Zap size={18} />
            </div>
            <div>
              <h2 className="text-base font-semibold text-white">Instant 1-Click Video (Zero Cost)</h2>
              <p className="text-xs text-[var(--mu)]">Direct 4-step pipeline: Script + Edge-TTS Voice + Subtitles + 9:16 Render straight to QC1</p>
            </div>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row gap-3 pt-1">
          <input
            type="text"
            placeholder='Enter topic, e.g. "3 psychological tricks people use on you" or "Why the Roman Empire fell"'
            value={instantTopic}
            onChange={(e) => setInstantTopic(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleInstantGenerate()}
            disabled={isGenerating}
            className="flex-1 px-4 py-2.5 rounded-lg bg-[var(--gl)] border border-[var(--ln)] text-[var(--tx)] text-sm outline-none focus:border-blue-500 transition-colors"
          />

          <select
            value={selectedVoice}
            onChange={(e) => setSelectedVoice(e.target.value)}
            disabled={isGenerating}
            className="px-3 py-2.5 rounded-lg bg-[var(--bg)] border border-[var(--ln)] text-xs text-[var(--tx)] outline-none focus:border-blue-500"
          >
            {voices.map((v) => (
              <option key={v.id} value={v.id}>{v.label}</option>
            ))}
          </select>

          <Button
            onClick={handleInstantGenerate}
            disabled={!instantTopic.trim() || isGenerating}
            className="flex items-center gap-2 whitespace-nowrap !px-5"
          >
            {isGenerating ? <Loader2 size={16} className="animate-spin" /> : <Zap size={16} />}
            {isGenerating ? 'Building Video...' : 'Generate Video'}
          </Button>
        </div>

        {isGenerating && (
          <div className="flex items-center gap-3 pt-2 text-xs text-blue-400">
            <Loader2 size={14} className="animate-spin shrink-0" />
            <span>{generationStep}</span>
          </div>
        )}
      </Card>

      {/* Alternative Advanced Modes Header */}
      <div className="pt-2">
        <h2 className="text-sm font-semibold text-slate-300 mb-1">Advanced Multi-Agent Workflows</h2>
        <p className="text-xs text-[var(--mu)] mb-3">Optional deep exploration pipelines with research scraping and character bibles.</p>

        {isLoading ? (
          <div className="grid grid-cols-[repeat(auto-fit,minmax(230px,1fr))] gap-4">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="glass-panel overflow-hidden animate-pulse h-[200px]" />
            ))}
          </div>
        ) : creationModes.length === 0 ? (
          <EmptyState title="No creation modes" description="There are no creation methods available right now." />
        ) : (
          <div className="grid grid-cols-[repeat(auto-fit,minmax(230px,1fr))] gap-4">
            {creationModes.map((mode) => (
              <div 
                key={mode.id}
                onClick={() => navigate(`/copilot/${mode.id}`)}
                className="glass-panel overflow-hidden cursor-pointer group hover:border-blue-500/50 hover:shadow-lg transition-all flex flex-col h-[260px] !p-0"
              >
                <div className="h-[130px] w-full bg-cover bg-center relative" style={{backgroundImage: `url('${mode.bg}')`}}>
                  <div className="absolute inset-0 bg-gradient-to-t from-[var(--bg)] to-transparent" />
                </div>
                <div className="p-4 flex-1 flex flex-col">
                  <h3 className="text-[15px] font-semibold mb-1 group-hover:text-blue-400 transition-colors">{mode.title}</h3>
                  <p className="text-[12px] text-[var(--mu)] leading-relaxed flex-1">{mode.desc}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
