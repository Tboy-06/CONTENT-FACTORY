import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Zap, Loader2, Sparkles } from 'lucide-react';
import { Button, Card } from '../components/ui';
import { useCreateInstantJob } from '../api/client';

const styles = [
  { id: 'dark_doc', label: 'Dark Documentary' },
  { id: 'vintage_35', label: 'Vintage 35mm' },
  { id: 'cyberpunk', label: 'Cyberpunk' },
  { id: 'minimalist', label: 'Minimalist' }
];

const voices = [
  { id: 'en-US-ChristopherNeural', label: 'Christopher (Male, Storytelling)' },
  { id: 'en-US-AndrewNeural', label: 'Andrew (Male, Serious)' },
  { id: 'en-US-GuyNeural', label: 'Guy (Male, Conversational)' },
  { id: 'en-US-AriaNeural', label: 'Aria (Female, Clear)' }
];

export default function Create() {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(true);
  const [instantTopic, setInstantTopic] = useState('');
  const [selectedVoice, setSelectedVoice] = useState('en-US-ChristopherNeural');
  const [selectedStyle, setSelectedStyle] = useState('dark_doc');
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
    setGenerationStep('1/4: Writing Script...');

    try {
      const res = await instantMutation.mutateAsync({
        topic: instantTopic.trim(),
        voice: selectedVoice
      });

      setGenerationStep('2/4: Generating Voice & Subs...');
      setTimeout(() => setGenerationStep('3/4: Fetching Visuals...'), 3000);
      setTimeout(() => {
        setGenerationStep('4/4: FFmpeg Rendering...');
        setTimeout(() => {
          navigate(`/qc1/${res.id}`);
        }, 3000);
      }, 7000);
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
          <div className="text-[var(--mu)] text-[13px]">Enter a topic to launch the 4-step documentary engine.</div>
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
              <h2 className="text-base font-semibold text-white">Documentary Studio</h2>
              <p className="text-xs text-[var(--mu)]">Turn your idea into a video in 3 minutes.</p>
            </div>
          </div>
        </div>

        <div className="flex flex-col gap-3 pt-1">
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="flex-1 relative flex">
              <input
                type="text"
                placeholder='Enter topic, e.g. "How the CIA used cats as spies"'
                value={instantTopic}
                onChange={(e) => setInstantTopic(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleInstantGenerate()}
                disabled={isGenerating}
                className="flex-1 px-4 py-2.5 rounded-l-lg bg-[var(--gl)] border border-[var(--ln)] text-[var(--tx)] text-sm outline-none focus:border-blue-500 transition-colors"
              />
              <Button variant="ghost" className="rounded-l-none rounded-r-lg bg-[var(--gl2)] hover:bg-[var(--gl)] !border-l-0 text-amber-400" title="Brainstorm 3 Viral Hooks">
                <Sparkles size={16} />
              </Button>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row gap-3">
            <select
              value={selectedStyle}
              onChange={(e) => setSelectedStyle(e.target.value)}
              disabled={isGenerating}
              className="flex-1 px-3 py-2.5 rounded-lg bg-[var(--bg)] border border-[var(--ln)] text-xs text-[var(--tx)] outline-none focus:border-blue-500"
            >
              {styles.map((s) => (
                <option key={s.id} value={s.id}>{s.label}</option>
              ))}
            </select>

            <select
              value={selectedVoice}
              onChange={(e) => setSelectedVoice(e.target.value)}
              disabled={isGenerating}
              className="flex-1 px-3 py-2.5 rounded-lg bg-[var(--bg)] border border-[var(--ln)] text-xs text-[var(--tx)] outline-none focus:border-blue-500"
            >
              {voices.map((v) => (
                <option key={v.id} value={v.id}>{v.label}</option>
              ))}
            </select>

            <Button
              onClick={handleInstantGenerate}
              disabled={!instantTopic.trim() || isGenerating}
              className="flex items-center gap-2 whitespace-nowrap !px-8 h-[42px]"
            >
              {isGenerating ? <Loader2 size={16} className="animate-spin" /> : <Zap size={16} />}
              {isGenerating ? 'Building Video...' : 'Generate Short'}
            </Button>
          </div>
        </div>

        {isGenerating && (
          <div className="flex items-center gap-3 pt-2 text-xs text-blue-400">
            <Loader2 size={14} className="animate-spin shrink-0" />
            <span>{generationStep}</span>
          </div>
        )}
      </Card>

    </div>
  );
}