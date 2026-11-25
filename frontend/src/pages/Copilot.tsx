import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Send,
  Upload,
  Target,
  Bot,
  Mic,
  CheckCircle2,
  Layers,
  Film
} from 'lucide-react';
import { Button, Badge } from '../components/ui';
import { useConnectivity } from '../lib/connectivity';
import { useChat, useScoreNiche, useCreateJob, useCapabilities } from '../api/client';

const VOICE_OPTIONS = [
  { id: 'en-US-AndrewMultilingualNeural', label: 'Andrew Multilingual (Trailer Male)' },
  { id: 'en-US-AvaMultilingualNeural', label: 'Ava Multilingual (Doc Female)' },
  { id: 'en-US-BrianMultilingualNeural', label: 'Brian Multilingual (Editorial Male)' },
  { id: 'am_michael', label: 'Kokoro-82M Michael (Local Offline CPU)' }
];

const STYLE_OPTIONS = [
  'Dark Documentary',
  'Vintage 35mm',
  'Cyberpunk Neo-Noir',
  'Minimalist Studio'
];

const SAMPLE_PROMPTS = [
  'Score niche: Declassified Cold War submarine mysteries',
  'Draft a 60s hook & beat plan on Operation Mincemeat',
  'Compare retention potential: Aviation black-box vs Heist forensics'
];

export default function Copilot() {
  const { mode } = useParams();
  const navigate = useNavigate();
  const isOnline = useConnectivity();

  const [showStageMatrix, setShowStageMatrix] = useState(false);
  const [lastScore, setLastScore] = useState<{ total: number; recommendation?: string } | null>(null);

  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      text: `Standing by in "${mode || 'studio'}" mode. Describe a documentary niche or concept to evaluate its retention score and configure a production brief.`
    }
  ]);
  const [input, setInput] = useState('');

  const [jobConfig, setJobConfig] = useState({
    format: '9:16',
    duration: '60s',
    platforms: ['YouTube', 'TikTok'],
    voice: 'en-US-AndrewMultilingualNeural',
    visualStyle: 'Dark Documentary',
    quality: '1080p',
    referenceUrl: ''
  });

  const chatMutation = useChat();
  const scoreMutation = useScoreNiche();
  const createMutation = useCreateJob();
  const { data: capabilities = [] } = useCapabilities();

  const handleSend = async (customPrompt?: string) => {
    const textToSend = (customPrompt ?? input).trim();
    if (!textToSend || chatMutation.isPending) return;
    const userMsg = { role: 'user', text: textToSend };
    setMessages((prev) => [...prev, userMsg]);
    if (!customPrompt) setInput('');

    try {
      const scoreRes = await scoreMutation.mutateAsync(userMsg.text);
      const scoreObj = scoreRes?.data || scoreRes;
      if (scoreObj && typeof scoreObj === 'object' && scoreObj.total_score !== undefined) {
        setLastScore({
          total: Number(scoreObj.total_score),
          recommendation: scoreObj.recommendation
        });
        const recSuffix = scoreObj.recommendation ? ` (${scoreObj.recommendation})` : '';
        setMessages((prev) => [
          ...prev,
          { role: 'assistant', text: `Niche Evaluation: ${scoreObj.total_score}/50${recSuffix}` }
        ]);
      }
    } catch {
      // silent score fallback
    }

    try {
      const res = await chatMutation.mutateAsync({ prompt: userMsg.text });
      const replyText =
        typeof res === 'object' ? res.response || JSON.stringify(res) : String(res);
      setMessages((prev) => [...prev, { role: 'assistant', text: replyText }]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', text: 'Unable to reach brain router. Verify backend server status.' }
      ]);
    }
  };

  const handleGenerate = async () => {
    const lastUserMessage = [...messages].reverse().find((m) => m.role === 'user')?.text;
    const niche = lastUserMessage || input.trim() || 'Declassified Historical Investigation';
    await createMutation.mutateAsync({
      niche,
      referenceUrl: jobConfig.referenceUrl,
      duration: jobConfig.duration,
      format: jobConfig.format,
      voice: jobConfig.voice,
      style_preset: jobConfig.visualStyle,
      premium: false,
      manual_approval: true,
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

  const togglePlatform = (plat: string) => {
    setJobConfig((prev) => ({
      ...prev,
      platforms: prev.platforms.includes(plat)
        ? prev.platforms.filter((p) => p !== plat)
        : [...prev.platforms, plat]
    }));
  };

  return (
    <div className="animate-in fade-in min-h-full flex flex-col pb-8 space-y-5">
      {/* Studio Header */}
      <div className="flex justify-between items-center flex-wrap gap-3 shrink-0">
        <div>
          <div className="flex items-center gap-2.5 flex-wrap">
            <div className="p-2 rounded-xl bg-blue-600/15 text-blue-600 dark:text-blue-400 border border-blue-500/25">
              <Target size={17} />
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-[var(--tx)]">
              Niche Scorer &amp; Script Copilot
            </h1>
            <Badge variant={isOnline ? 'success' : 'warning'}>
              {isOnline ? 'Hybrid $0 Cloud + Local' : 'Local Spark Offline'}
            </Badge>
          </div>
          <p className="text-[var(--mu)] text-xs mt-1">
            Score documentary topics out of 50, refine narrative hooks, and queue structured pipeline jobs at $0 API spend.
          </p>
        </div>
        <Button type="button" variant="secondary" onClick={() => navigate('/create')}>
          <ArrowLeft size={13} />
          <span>Back to Production Deck</span>
        </Button>
      </div>

      {/* Main Split Studio Workspace */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-5 flex-1 min-h-[540px]">
        {/* Left Column (7/12): Interactive Brief & Niche Evaluation Stream */}
        <div className="xl:col-span-7 glass-panel p-5 flex flex-col justify-between min-h-[480px] min-w-0">
          <div className="flex items-center justify-between gap-2 pb-3 border-b border-[var(--ln-subtle)]">
            <div className="flex items-center gap-2">
              <Bot size={15} className="text-blue-600 dark:text-blue-400" />
              <span className="text-xs font-bold uppercase tracking-wider text-[var(--tx)]">
                Editorial Strategy Feed
              </span>
            </div>
            {lastScore && (
              <Badge variant={lastScore.total >= 35 ? 'success' : 'info'}>
                Last Score: {lastScore.total}/50
              </Badge>
            )}
          </div>

          <div className="scroll-panel-stable flex-1 flex flex-col gap-3 py-4 pr-1">
            {messages.map((m, i) => (
              <div
                key={i}
                className={`max-w-[88%] p-3.5 rounded-2xl text-xs leading-relaxed ${
                  m.role === 'user'
                    ? 'self-end bg-blue-600 border border-blue-500/40 text-white preserve-white shadow-sm rounded-br-sm'
                    : 'self-start glass-subcard text-[var(--tx)] rounded-bl-sm'
                }`}
              >
                {m.text}
              </div>
            ))}
            {chatMutation.isPending && (
              <div className="max-w-[85%] p-3 rounded-xl text-xs glass-subcard text-[var(--mu)]" role="status">
                Scoring niche demand and drafting editorial brief...
              </div>
            )}
          </div>

          {/* Quick Evaluation Prompts */}
          <div className="space-y-2.5 pt-2 border-t border-[var(--ln-subtle)]">
            <div className="pill-row-balance gap-1.5">
              {SAMPLE_PROMPTS.map((sp) => (
                <button
                  key={sp}
                  type="button"
                  onClick={() => handleSend(sp)}
                  disabled={chatMutation.isPending}
                  className="px-2.5 py-1 rounded-lg bg-[var(--gl2)] border border-[var(--ln-subtle)] hover:border-blue-500/50 text-[11px] text-[var(--mu)] hover:text-[var(--tx)] transition-colors cursor-pointer"
                >
                  {sp}
                </button>
              ))}
            </div>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSend();
              }}
              className="flex gap-2 p-1.5 pl-3.5 rounded-xl border border-[var(--input-border)] bg-[var(--input-bg)] items-center text-xs"
            >
              <label htmlFor="copilot-brief-input" className="visually-hidden-input">
                Topic or documentary angle
              </label>
              <input
                id="copilot-brief-input"
                name="prompt"
                type="text"
                enterKeyHint="send"
                className="flex-1 bg-transparent outline-none text-[var(--tx)] placeholder:text-[var(--mu)] min-w-0"
                placeholder="Describe your topic, niche, or documentary angle..."
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
              />
              <Button type="submit" disabled={!input.trim() || chatMutation.isPending}>
                <Send size={13} />
                <span>Evaluate</span>
              </Button>
            </form>
          </div>
        </div>

        {/* Right Column (5/12): Production Specification Deck */}
        <div className="xl:col-span-5 glass-panel p-5 flex flex-col justify-between gap-4 min-w-0">
          <div className="space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-[var(--ln-subtle)]">
              <div className="flex items-center gap-2">
                <Film size={15} className="text-amber-600 dark:text-amber-400" />
                <h2 className="font-bold text-sm text-[var(--tx)]">Production Specification</h2>
              </div>
              <button
                type="button"
                onClick={() => setShowStageMatrix((prev) => !prev)}
                className="px-2.5 py-1 rounded-lg text-[11px] font-semibold bg-[var(--gl2)] border border-[var(--ln-subtle)] text-[var(--mu)] hover:text-[var(--tx)] cursor-pointer"
              >
                {showStageMatrix ? 'Hide Stage Engines' : 'Stage Engines'}
              </button>
            </div>

            {/* Format & Duration Radio Groups */}
            <div className="grid grid-cols-2 gap-3">
              <fieldset className="border-0 m-0 p-0">
                <legend className="text-[11px] font-bold uppercase tracking-wider text-[var(--mu)] mb-1.5 p-0">
                  Aspect Ratio
                </legend>
                <div className="grid grid-cols-2 gap-1.5">
                  {['9:16', '16:9'].map((fmt) => {
                    const active = jobConfig.format === fmt;
                    const id = `copilot-fmt-${fmt.replace(':', 'x')}`;
                    return (
                      <div key={fmt} className="relative">
                        <input
                          id={id}
                          type="radio"
                          name="copilot_format"
                          value={fmt}
                          checked={active}
                          onChange={() => setJobConfig({ ...jobConfig, format: fmt })}
                          className="visually-hidden-input"
                        />
                        <label
                          htmlFor={id}
                          className={`py-2 px-2.5 rounded-xl border text-xs font-bold text-center block cursor-pointer transition-all ${
                            active
                              ? 'bg-blue-600 text-white border-blue-500'
                              : 'bg-[var(--gl2)] text-[var(--tx)] border-[var(--ln)]'
                          }`}
                        >
                          {fmt}
                        </label>
                      </div>
                    );
                  })}
                </div>
              </fieldset>

              <fieldset className="border-0 m-0 p-0">
                <legend className="text-[11px] font-bold uppercase tracking-wider text-[var(--mu)] mb-1.5 p-0">
                  Target Runtime
                </legend>
                <div className="grid grid-cols-3 gap-1.5">
                  {['45s', '60s', '3m'].map((dur) => {
                    const active = jobConfig.duration === dur;
                    const id = `copilot-dur-${dur}`;
                    return (
                      <div key={dur} className="relative">
                        <input
                          id={id}
                          type="radio"
                          name="copilot_duration"
                          value={dur}
                          checked={active}
                          onChange={() => setJobConfig({ ...jobConfig, duration: dur })}
                          className="visually-hidden-input"
                        />
                        <label
                          htmlFor={id}
                          className={`py-2 px-2 rounded-xl border text-xs font-bold font-mono text-center block cursor-pointer transition-all ${
                            active
                              ? 'bg-blue-600 text-white border-blue-500'
                              : 'bg-[var(--gl2)] text-[var(--tx)] border-[var(--ln)]'
                          }`}
                        >
                          {dur}
                        </label>
                      </div>
                    );
                  })}
                </div>
              </fieldset>
            </div>

            {/* Visual Style Radio Pills */}
            <fieldset className="border-0 m-0 p-0">
              <legend className="text-[11px] font-bold uppercase tracking-wider text-[var(--mu)] mb-1.5 p-0">
                Visual Aesthetic
              </legend>
              <div className="grid grid-cols-2 gap-2">
                {STYLE_OPTIONS.map((st) => {
                  const active = jobConfig.visualStyle === st;
                  const id = `copilot-style-${st.replace(/\s+/g, '-').toLowerCase()}`;
                  return (
                    <div key={st} className="relative">
                      <input
                        id={id}
                        type="radio"
                        name="copilot_style"
                        value={st}
                        checked={active}
                        onChange={() => setJobConfig({ ...jobConfig, visualStyle: st })}
                        className="visually-hidden-input"
                      />
                      <label
                        htmlFor={id}
                        className={`p-2 rounded-xl border text-xs font-semibold flex items-center justify-between cursor-pointer transition-all ${
                          active
                            ? 'bg-blue-600/12 border-blue-500 text-[var(--tx)]'
                            : 'bg-[var(--gl2)] border-[var(--ln)] text-[var(--mu)] hover:text-[var(--tx)]'
                        }`}
                      >
                        <span className="truncate">{st}</span>
                        {active && <CheckCircle2 size={12} className="text-blue-600 dark:text-blue-400 shrink-0" />}
                      </label>
                    </div>
                  );
                })}
              </div>
            </fieldset>

            {/* Narrator Voice Radio Stack */}
            <fieldset className="border-0 m-0 p-0">
              <legend className="text-[11px] font-bold uppercase tracking-wider text-[var(--mu)] mb-1.5 flex items-center gap-1.5 p-0">
                <Mic size={12} className="text-emerald-600 dark:text-emerald-400" />
                <span>Narrator Voice (-14 LUFS)</span>
              </legend>
              <div className="grid grid-cols-1 gap-1.5">
                {VOICE_OPTIONS.map((v) => {
                  const active = jobConfig.voice === v.id;
                  const id = `copilot-voice-${v.id}`;
                  return (
                    <div key={v.id} className="relative">
                      <input
                        id={id}
                        type="radio"
                        name="copilot_voice"
                        value={v.id}
                        checked={active}
                        onChange={() => setJobConfig({ ...jobConfig, voice: v.id })}
                        className="visually-hidden-input"
                      />
                      <label
                        htmlFor={id}
                        className={`px-3 py-2 rounded-xl border text-xs font-medium flex items-center justify-between cursor-pointer transition-all ${
                          active
                            ? 'bg-blue-600/12 border-blue-500 text-[var(--tx)] font-semibold'
                            : 'bg-[var(--gl2)] border-[var(--ln)] text-[var(--mu)] hover:text-[var(--tx)]'
                        }`}
                      >
                        <span className="truncate">{v.label}</span>
                        {active && <CheckCircle2 size={13} className="text-blue-600 dark:text-blue-400 shrink-0" />}
                      </label>
                    </div>
                  );
                })}
              </div>
            </fieldset>

            {/* Target Platforms Checkboxes */}
            <fieldset className="border-0 m-0 p-0">
              <legend className="text-[11px] font-bold uppercase tracking-wider text-[var(--mu)] mb-1.5 p-0">
                Target Export Platforms
              </legend>
              <div className="flex items-center flex-wrap gap-2">
                {['YouTube', 'TikTok', 'Instagram Reels'].map((plat) => {
                  const checked = jobConfig.platforms.includes(plat);
                  return (
                    <label
                      key={plat}
                      className={`px-3 py-1.5 rounded-xl border text-xs font-semibold flex items-center gap-2 cursor-pointer select-none transition-colors ${
                        checked
                          ? 'bg-blue-600/15 border-blue-500/50 text-[var(--tx)]'
                          : 'bg-[var(--gl2)] border-[var(--ln)] text-[var(--mu)]'
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => togglePlatform(plat)}
                        className="accent-blue-600 rounded"
                      />
                      <span>{plat}</span>
                    </label>
                  );
                })}
              </div>
            </fieldset>

            {/* Optional Reference URL */}
            <div className="space-y-1">
              <label
                htmlFor="copilot-ref-url"
                className="text-[11px] font-bold uppercase tracking-wider text-[var(--mu)] flex items-center gap-1.5"
              >
                <Upload size={12} />
                <span>Reference Video URL (Optional)</span>
              </label>
              <input
                id="copilot-ref-url"
                name="reference_url"
                type="url"
                autoCorrect="off"
                autoCapitalize="none"
                spellCheck={false}
                value={jobConfig.referenceUrl}
                onChange={(e) => setJobConfig({ ...jobConfig, referenceUrl: e.target.value })}
                placeholder="https://youtube.com/watch?v=..."
                className="glass-input w-full px-3 py-2 text-xs font-mono"
              />
            </div>

            {showStageMatrix && capabilities.length > 0 && (
              <div className="glass-subcard p-3 space-y-1.5">
                <div className="text-[11px] font-bold text-[var(--tx)] flex items-center gap-1.5">
                  <Layers size={12} className="text-blue-600 dark:text-blue-400" />
                  <span>Active Stage Engines</span>
                </div>
                <table className="w-full text-[11px] text-left">
                  <thead>
                    <tr className="text-[var(--mu)]">
                      <th className="py-1">Stage</th>
                      <th className="py-1">Offline</th>
                      <th className="py-1">Zero-Cost Cloud</th>
                    </tr>
                  </thead>
                  <tbody>
                    {capabilities.map((c: any) => (
                      <tr key={c.stage} className="border-t border-[var(--ln-subtle)] text-[var(--tx)]">
                        <td className="py-1 font-semibold">{c.stage}</td>
                        <td className="py-1 text-[var(--mu)]">{c.offline}</td>
                        <td className="py-1">{c.free}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <div className="pt-3 border-t border-[var(--ln-subtle)] space-y-3">
            <div className="glass-subcard flex justify-between items-center p-3">
              <div>
                <span className="text-[var(--tx)] text-xs font-bold block">Zero-Cost Budget Lock</span>
                <span className="text-[11px] text-[var(--mu)]">
                  {isOnline ? 'Strictly-free cloud + local engines' : 'Local offline execution'}
                </span>
              </div>
              <b className="font-bold font-mono text-lg text-emerald-600 dark:text-emerald-400">$0.00</b>
            </div>

            <Button
              type="button"
              className="w-full !py-3 justify-center font-bold"
              disabled={createMutation.isPending}
              onClick={handleGenerate}
            >
              <span>
                {createMutation.isPending ? 'Queueing Production Job...' : 'Queue Documentary Job'}
              </span>
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
