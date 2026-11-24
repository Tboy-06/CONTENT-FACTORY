import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Send, Upload, Sparkles } from 'lucide-react';
import { Button, Badge } from '../components/ui';
import { useConnectivity } from '../lib/connectivity';
import { useChat, useScoreNiche, useCreateJob, useCapabilities } from '../api/client';

export default function Copilot() {
  const { mode } = useParams();
  const navigate = useNavigate();
  const isOnline = useConnectivity();

  const [isAdvanced, setIsAdvanced] = useState(false);
  const [tier, setTier] = useState<'free' | 'premium'>('free');

  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      text: `Standing by in "${mode || 'studio'}" mode. Describe your niche or documentary idea and I will score it and draft the plan.`
    }
  ]);
  const [input, setInput] = useState('');

  const [jobConfig, setJobConfig] = useState({
    format: '9:16',
    duration: '60s',
    platforms: ['YouTube', 'TikTok'],
    voice: 'en-US-AriaNeural',
    visualStyle: 'Dark Documentary',
    quality: '1080p',
    referenceUrl: ''
  });

  const chatMutation = useChat();
  const scoreMutation = useScoreNiche();
  const createMutation = useCreateJob();
  const { data: capabilities = [] } = useCapabilities();

  const handleSend = async () => {
    if (!input.trim()) return;
    const userMsg = { role: 'user', text: input };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');

    try {
      const scoreRes = await scoreMutation.mutateAsync(userMsg.text);
      const scoreObj = scoreRes?.data || scoreRes;
      if (scoreObj && typeof scoreObj === 'object' && scoreObj.total_score !== undefined) {
        const recSuffix = scoreObj.recommendation ? ` (${scoreObj.recommendation})` : '';
        setMessages((prev) => [
          ...prev,
          { role: 'assistant', text: `Niche Score: ${scoreObj.total_score}/50${recSuffix}` }
        ]);
      }
    } catch {
      // silent score error fallback
    }

    try {
      const res = await chatMutation.mutateAsync({ prompt: userMsg.text });
      const replyText =
        typeof res === 'object' ? res.response || JSON.stringify(res) : String(res);
      setMessages((prev) => [...prev, { role: 'assistant', text: replyText }]);
    } catch {
      setMessages((prev) => [...prev, { role: 'assistant', text: 'Failed to connect to Copilot.' }]);
    }
  };

  const handleGenerate = async (_runNow: boolean) => {
    const niche = messages.find((m) => m.role === 'user')?.text || 'Unknown niche';
    await createMutation.mutateAsync({
      niche,
      referenceUrl: jobConfig.referenceUrl,
      duration: jobConfig.duration,
      format: jobConfig.format,
      voice: jobConfig.voice,
      style_preset: jobConfig.visualStyle,
      premium: tier === 'premium',
      manual_approval: isAdvanced,
      pipelineMode: mode,
      platforms: jobConfig.platforms
    });
    navigate('/pipeline');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      if (e.nativeEvent.isComposing || e.nativeEvent.keyCode === 229) return;
      handleSend();
    }
  };

  const isPremiumDisabled = !isOnline;

  return (
    <div className="animate-in fade-in min-h-full flex flex-col pb-8 space-y-5">
      <div className="flex justify-between items-center flex-wrap gap-3 shrink-0">
        <div>
          <div className="flex items-center gap-2">
            <Sparkles size={18} className="text-blue-600 dark:text-blue-400" />
            <h1 className="text-2xl font-bold tracking-tight text-[var(--tx)]">AI Copilot</h1>
          </div>
          <div className="text-[var(--mu)] text-xs mt-0.5">
            Describe what you want to produce, inspect niche scores, and configure pipeline parameters.
          </div>
        </div>
        <Button variant="secondary" onClick={() => navigate('/create')}>
          <ArrowLeft size={13} />
          <span>Back to Launchpad</span>
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1.25fr_1fr] gap-5 flex-1 min-h-[500px]">
        {/* Chat Area */}
        <div className="glass-panel flex flex-col p-4 !pb-0 min-h-0">
          <div className="flex-1 overflow-auto flex flex-col gap-3 pr-1 mb-4">
            {messages.map((m, i) => (
              <div
                key={i}
                className={`max-w-[85%] p-3 rounded-xl text-xs leading-relaxed ${
                  m.role === 'user'
                    ? 'self-end bg-blue-600 border border-blue-500/40 text-white shadow-sm'
                    : 'glass-subcard text-[var(--tx)]'
                }`}
              >
                {m.text}
              </div>
            ))}
            {chatMutation.isPending && (
              <div className="max-w-[85%] p-3 rounded-xl text-xs glass-subcard text-[var(--mu)]">
                Processing request...
              </div>
            )}
          </div>

          <div className="flex gap-2 p-1.5 pl-3.5 rounded-xl border border-[var(--input-border)] bg-[var(--input-bg)] items-center text-xs mb-4">
            <input
              type="text"
              className="flex-1 bg-transparent outline-none text-[var(--tx)] placeholder:text-[var(--mu)]"
              placeholder="Describe your topic or documentary angle..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
            />
            <Button onClick={handleSend} disabled={!input.trim() || chatMutation.isPending}>
              <Send size={13} />
              <span>Send</span>
            </Button>
          </div>
        </div>

        {/* Configuration Area */}
        <div className="glass-panel p-5 flex flex-col overflow-auto min-h-0">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-bold text-sm text-[var(--tx)]">Job Configuration</h2>
            <div className="flex gap-1 p-0.5 rounded-xl bg-[var(--gl2)] border border-[var(--ln-subtle)]">
              <button
                className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                  !isAdvanced
                    ? 'bg-blue-600 text-white shadow-xs'
                    : 'text-[var(--mu)] hover:text-[var(--tx)]'
                }`}
                onClick={() => setIsAdvanced(false)}
              >
                Basic
              </button>
              <button
                className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                  isAdvanced
                    ? 'bg-blue-600 text-white shadow-xs'
                    : 'text-[var(--mu)] hover:text-[var(--tx)]'
                }`}
                onClick={() => setIsAdvanced(true)}
              >
                Advanced
              </button>
            </div>
          </div>

          <div className="flex justify-between items-center py-2.5 border-b border-[var(--ln-subtle)] text-xs">
            <span className="text-[var(--mu)] font-medium">Format</span>
            <select
              value={jobConfig.format}
              onChange={(e) => setJobConfig({ ...jobConfig, format: e.target.value })}
              className="glass-input px-2.5 py-1.5 text-xs min-w-[140px] cursor-pointer"
            >
              <option value="9:16">9:16 Vertical</option>
              <option value="16:9">16:9 Horizontal</option>
            </select>
          </div>

          <div className="flex justify-between items-center py-2.5 border-b border-[var(--ln-subtle)] text-xs">
            <span className="text-[var(--mu)] font-medium">Duration</span>
            <select
              value={jobConfig.duration}
              onChange={(e) => setJobConfig({ ...jobConfig, duration: e.target.value })}
              className="glass-input px-2.5 py-1.5 text-xs min-w-[140px] cursor-pointer"
            >
              <option value="60s">60 seconds</option>
              <option value="120s">120 seconds</option>
            </select>
          </div>

          <div className="flex justify-between items-center py-2.5 border-b border-[var(--ln-subtle)] text-xs">
            <span className="text-[var(--mu)] font-medium">Target Platforms</span>
            <div className="flex gap-1.5">
              <Badge variant="danger">YouTube</Badge>
              <Badge variant="info">TikTok</Badge>
            </div>
          </div>

          <div className="flex justify-between items-center py-2.5 border-b border-[var(--ln-subtle)] text-xs">
            <span className="text-[var(--mu)] font-medium">AI Engine Tier</span>
            <div className="flex gap-1 p-0.5 rounded-xl bg-[var(--gl2)] border border-[var(--ln-subtle)]">
              <button
                className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                  tier === 'free' || isPremiumDisabled
                    ? 'bg-blue-600 text-white shadow-xs'
                    : 'text-[var(--mu)] hover:text-[var(--tx)]'
                }`}
                onClick={() => setTier('free')}
              >
                Free ($0)
              </button>
              <button
                className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                  !isPremiumDisabled && tier === 'premium'
                    ? 'bg-blue-600 text-white shadow-xs cursor-pointer'
                    : isPremiumDisabled
                    ? 'text-[var(--mu)] opacity-40 cursor-not-allowed line-through'
                    : 'text-[var(--mu)] hover:text-[var(--tx)] cursor-pointer'
                }`}
                onClick={() => !isPremiumDisabled && setTier('premium')}
                disabled={isPremiumDisabled}
              >
                Premium
              </button>
            </div>
          </div>

          <div className="text-[11px] text-[var(--mu)] py-2">
            {isOnline
              ? 'Online. Free uses strictly-free cloud and local workstation engines.'
              : 'Offline. Cloud requests paused. Free runs locally.'}
          </div>

          {isAdvanced && (
            <div className="animate-in fade-in space-y-2 pt-1">
              {capabilities.length > 0 && (
                <div className="py-2 border-b border-[var(--ln-subtle)]">
                  <div className="text-[var(--mu)] text-[11px] font-semibold mb-1.5">
                    Stage Engines
                  </div>
                  <table className="w-full text-[11px] text-left">
                    <thead>
                      <tr className="text-[var(--mu)]">
                        <th className="py-1">Stage</th>
                        <th className="py-1">Offline</th>
                        <th className="py-1">Free</th>
                      </tr>
                    </thead>
                    <tbody>
                      {capabilities.map((c: any) => (
                        <tr key={c.stage} className="border-t border-[var(--ln-subtle)] text-[var(--tx)]">
                          <td className="py-1.5 font-semibold">{c.stage}</td>
                          <td className="py-1.5 text-[var(--mu)]">{c.offline}</td>
                          <td className="py-1.5">{c.free}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {mode === 'clone' && (
                <div className="py-2 border-b border-[var(--ln-subtle)] space-y-2">
                  <div className="text-[var(--mu)] text-[11px] font-semibold">Reference Video</div>
                  <div className="border border-dashed border-[var(--input-border)] rounded-xl p-5 flex flex-col items-center justify-center text-center bg-[var(--input-bg)] hover:border-blue-500/60 transition-colors cursor-pointer">
                    <Upload size={18} className="text-blue-600 dark:text-blue-400 mb-1.5" />
                    <div className="text-xs font-semibold text-[var(--tx)]">
                      Select reference video file to analyze
                    </div>
                    <div className="text-[11px] text-[var(--mu)] mt-0.5">MP4, MOV up to 50MB</div>
                  </div>
                  <input
                    type="text"
                    value={jobConfig.referenceUrl}
                    onChange={(e) => setJobConfig({ ...jobConfig, referenceUrl: e.target.value })}
                    placeholder="Or paste reference URL: https://..."
                    className="glass-input w-full px-3 py-2 text-xs"
                  />
                </div>
              )}

              <div className="flex justify-between items-center py-2 border-b border-[var(--ln-subtle)] text-xs">
                <span className="text-[var(--mu)] font-medium">Voice</span>
                <select
                  value={jobConfig.voice}
                  onChange={(e) => setJobConfig({ ...jobConfig, voice: e.target.value })}
                  className="glass-input px-2.5 py-1.5 text-xs min-w-[160px] cursor-pointer"
                >
                  <option value="en-US-AriaNeural">Aria (Female)</option>
                  <option value="en-US-ChristopherNeural">Christopher (Male)</option>
                  <option value="en-US-GuyNeural">Guy (Male)</option>
                  <option value="en-US-AndrewNeural">Andrew (Male)</option>
                </select>
              </div>

              <div className="flex justify-between items-center py-2 border-b border-[var(--ln-subtle)] text-xs">
                <span className="text-[var(--mu)] font-medium">Visual Style</span>
                <select
                  value={jobConfig.visualStyle}
                  onChange={(e) => setJobConfig({ ...jobConfig, visualStyle: e.target.value })}
                  className="glass-input px-2.5 py-1.5 text-xs min-w-[160px] cursor-pointer"
                >
                  <option value="Dark Documentary">Dark Documentary</option>
                  <option value="Vintage 35mm">Vintage 35mm</option>
                  <option value="Cyberpunk Neo-Noir">Cyberpunk Neo-Noir</option>
                  <option value="Minimalist Studio">Minimalist Studio</option>
                </select>
              </div>
            </div>
          )}

          <div className="mt-auto pt-4 flex flex-col gap-3">
            <div className="glass-subcard flex justify-between items-center p-3.5">
              <span className="text-[var(--mu)] text-xs font-medium">Estimated API Cost</span>
              <b className="font-bold font-mono text-lg text-emerald-600 dark:text-emerald-400">
                {tier === 'free' || isPremiumDisabled ? '$0.00' : 'Unavailable'}
              </b>
            </div>

            {isOnline ? (
              <Button className="w-full !py-2.5" onClick={() => handleGenerate(true)}>
                Generate Production Plan
              </Button>
            ) : (
              <div className="flex gap-2">
                <Button className="flex-1" variant="secondary" onClick={() => handleGenerate(true)}>
                  Run Locally Now
                </Button>
                <Button className="flex-1" onClick={() => handleGenerate(false)}>
                  Queue Until Online
                </Button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
