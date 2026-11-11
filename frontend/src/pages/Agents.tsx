import { useState } from 'react';
import { Badge, Button } from '../components/ui';
import { Cpu, Zap, Volume2, Film, CheckCircle2, Loader2, Target, Activity } from 'lucide-react';
import { api } from '../api/client';

export default function Agents() {
  const [testResult, setTestResult] = useState<string | null>(null);
  const [isTesting, setIsTesting] = useState(false);

  const agents = [
    { 
      name: 'Niche Scorer', 
      status: 'Active', 
      model: 'Gemini 3.6 Flash', 
      role: 'Evaluator', 
      desc: 'Scores volume, competition, CPM, and evergreen potential with quantitative analysis.',
      icon: Target
    },
    { 
      name: 'Viral Researcher', 
      status: 'Active', 
      model: 'Gemini 3.6 Flash', 
      role: 'Content', 
      desc: 'Generates high-retention angles, psychological hooks, and brief packages.',
      icon: Zap
    },
    { 
      name: 'Documentary Scriptwriter', 
      status: 'Active', 
      model: 'Gemini 3.6 Flash', 
      role: 'Planner', 
      desc: 'Structures 8-sentence scripts with 16 rapid visual beat cues and sound effects.',
      icon: Cpu
    },
    { 
      name: 'Art Director', 
      status: 'Active', 
      model: 'Pillow + FFmpeg', 
      role: 'Visuals', 
      desc: 'Composes archival typography plates with Hard B&W, Teal Split, and Amber grades.',
      icon: Film
    },
    { 
      name: 'Voice & Subtitle Engine', 
      status: 'Active', 
      model: 'Edge-TTS + ASS', 
      role: 'Audio', 
      desc: 'Renders Microsoft Neural voiceover and generates word-by-word highlighted captions.',
      icon: Volume2
    },
    { 
      name: 'Video Assembler', 
      status: 'Active', 
      model: 'FFmpeg H.264', 
      role: 'Renderer', 
      desc: 'Compiles vertical 9:16 videos at 30fps with synchronized SFX transitions.',
      icon: Film
    },
  ];

  const handleTestBrain = async () => {
    setIsTesting(true);
    setTestResult(null);
    const start = Date.now();
    try {
      const res = await api.post('/api/jobs/brainstorm-hooks', { topic: 'AI Content Systems' });
      const elapsed = ((Date.now() - start) / 1000).toFixed(2);
      if (res?.hooks && res.hooks.length > 0) {
        setTestResult(`Success (${elapsed}s): "${res.hooks[0]}"`);
      } else {
        setTestResult(`Operational (${elapsed}s)`);
      }
    } catch (e: any) {
      setTestResult(`Test failed: ${e.message}`);
    } finally {
      setIsTesting(false);
    }
  };

  return (
    <div className="animate-in fade-in min-h-full flex flex-col pb-8">
      {/* Header */}
      <div className="flex justify-between items-center flex-wrap gap-3 mb-6 shrink-0">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-white">Production Engines & Pipelines</h1>
          <div className="text-slate-400 text-xs mt-1">Operational status of core generation, synthesis, and rendering subsystems.</div>
        </div>

        <Button 
          variant="secondary"
          onClick={handleTestBrain}
          disabled={isTesting}
          className="flex items-center gap-2 text-xs border-slate-700"
        >
          {isTesting ? <Loader2 size={13} className="animate-spin text-blue-400" /> : <Activity size={13} className="text-blue-400" />}
          <span>{isTesting ? 'Testing Latency...' : 'Test Engine Latency'}</span>
        </Button>
      </div>

      {testResult && (
        <div className="p-3.5 bg-emerald-950/40 border border-emerald-500/40 text-emerald-300 rounded-md text-xs mb-6 flex items-center gap-2">
          <CheckCircle2 size={14} className="text-emerald-400 shrink-0" />
          <span><b>Engine Response:</b> {testResult}</span>
        </div>
      )}

      {/* Grid of Agents */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {agents.map(agent => {
          const Icon = agent.icon;
          return (
            <div key={agent.name} className="glass-panel p-5 flex flex-col justify-between gap-4 border-slate-800/80">
              <div>
                <div className="flex justify-between items-start mb-2">
                  <div className="flex items-center gap-2.5">
                    <div className="p-2 rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20">
                      <Icon size={16} />
                    </div>
                    <div>
                      <b className="font-semibold text-[14px] text-white block">{agent.name}</b>
                      <span className="text-[11px] text-[var(--mu)]">{agent.role}</span>
                    </div>
                  </div>
                  <Badge variant="success">Operational</Badge>
                </div>

                <p className="text-xs text-slate-400 mt-2 leading-relaxed">
                  {agent.desc}
                </p>
              </div>
              
              <div className="pt-3 border-t border-[var(--ln)] flex justify-between items-center text-xs">
                <span className="text-[var(--mu)]">Engine / Model:</span>
                <span className="font-mono text-slate-300 font-medium">{agent.model}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
