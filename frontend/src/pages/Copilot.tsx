import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
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
    { role: 'assistant', text: `Got it. Let's create a video using the "${mode}" method. Describe your niche or idea.` }
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
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    
    // Check niche score
    try {
      const scoreRes = await scoreMutation.mutateAsync(userMsg.text);
      const scoreObj = scoreRes?.data || scoreRes;
      if (scoreObj && typeof scoreObj === 'object') {
        const scoreVal = scoreObj.total_score ?? 38;
        const rec = scoreObj.recommendation ?? 'GO';
        setMessages(prev => [...prev, { role: 'assistant', text: `Niche Score: ${scoreVal}/50 (${rec})` }]);
      }
    } catch (e) {
      // silent score error fallback
    }

    try {
      const res = await chatMutation.mutateAsync({ prompt: userMsg.text });
      const replyText = typeof res === 'object' ? (res.response || JSON.stringify(res)) : String(res);
      setMessages(prev => [...prev, { role: 'assistant', text: replyText }]);
    } catch (e) {
      setMessages(prev => [...prev, { role: 'assistant', text: `Failed to connect to Copilot.` }]);
    }
  };

  const handleGenerate = async (runNow: boolean) => {
    const niche = messages.find(m => m.role === 'user')?.text || 'Unknown niche';
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
      handleSend();
    }
  };

  const isPremiumDisabled = !isOnline;

  return (
    <div className="animate-in fade-in min-h-full flex flex-col pb-8">
      <div className="flex justify-between items-center flex-wrap gap-3 mb-4 shrink-0">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight">AI Copilot</h1>
          <div className="text-[var(--mu)] text-[13px]">Describe what you want to create, and I'll handle the rest.</div>
        </div>
        <Button variant="ghost" onClick={() => navigate('/create')}>Back to methods</Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1.2fr_1fr] gap-4 flex-1 min-h-[480px]">
        
        {/* Chat Area */}
        <div className="glass-panel flex flex-col p-4 !pb-0 min-h-0">
          <div className="flex-1 overflow-auto flex flex-col gap-2.5 pr-2 mb-4">
            {messages.map((m, i) => (
              <div key={i} className={`max-w-[85%] p-[10px_13px] rounded-md text-[13px] ${
                m.role === 'user' 
                  ? 'self-end bg-blue-600 border border-blue-500/40 text-white' 
                  : 'bg-slate-900 border border-slate-800 text-slate-200'
              }`}>
                {m.text}
              </div>
            ))}
            {chatMutation.isPending && (
              <div className="max-w-[85%] p-[10px_13px] rounded-md text-[13px] bg-slate-900 border border-slate-800 text-slate-400">
                Processing request...
              </div>
            )}
          </div>
          <div className="flex gap-2 p-[6px_6px_6px_12px] rounded-xl border border-[var(--ln)] bg-[var(--gl)] items-center text-[13px] mb-4">
            <input 
              type="text" 
              className="flex-1 bg-transparent outline-none text-[var(--tx)] placeholder-[var(--mu)]"
              placeholder="Type your message"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
            />
            <Button onClick={handleSend}>Send</Button>
          </div>
        </div>

        {/* Configuration Area */}
        <div className="glass-panel p-4 flex flex-col overflow-auto min-h-0">
          <h2 className="font-semibold mb-1.5 text-[15px]">Job configuration</h2>
          
          <div className="flex gap-1 p-[3px] rounded-lg bg-[var(--gl2)] w-max my-2">
            <button className={`px-3 py-1 rounded-[7px] text-xs font-medium transition-colors ${!isAdvanced ? 'bg-gradient-to-br from-[var(--ac)] to-[var(--ac2)] text-white' : 'text-[var(--mu)] hover:text-white'}`} onClick={() => setIsAdvanced(false)}>Basic</button>
            <button className={`px-3 py-1 rounded-[7px] text-xs font-medium transition-colors ${isAdvanced ? 'bg-gradient-to-br from-[var(--ac)] to-[var(--ac2)] text-white' : 'text-[var(--mu)] hover:text-white'}`} onClick={() => setIsAdvanced(true)}>Advanced</button>
          </div>

          <div className="flex justify-between items-center py-2 border-b border-[var(--ln)] text-[13px]">
            <span className="text-[var(--mu)]">Format</span>
            <select value={jobConfig.format} onChange={e => setJobConfig({...jobConfig, format: e.target.value})} className="px-2.5 py-1 rounded-lg border border-[var(--ln)] bg-[var(--gl)] outline-none min-w-[120px] text-right">
              <option value="9:16">9:16 Vertical</option>
              <option value="16:9">16:9 Horizontal</option>
            </select>
          </div>
          
          <div className="flex justify-between items-center py-2 border-b border-[var(--ln)] text-[13px]">
            <span className="text-[var(--mu)]">Duration</span>
            <select value={jobConfig.duration} onChange={e => setJobConfig({...jobConfig, duration: e.target.value})} className="px-2.5 py-1 rounded-lg border border-[var(--ln)] bg-[var(--gl)] outline-none min-w-[120px] text-right">
              <option value="60s">60 seconds</option>
              <option value="120s">120 seconds</option>
            </select>
          </div>

          <div className="flex justify-between items-center py-2 border-b border-[var(--ln)] text-[13px]">
            <span className="text-[var(--mu)]">Platform</span>
            <div className="flex gap-1">
              <Badge variant="danger">YouTube</Badge>
              <Badge variant="info">TikTok</Badge>
            </div>
          </div>

          <div className="flex justify-between items-center py-2 border-b border-[var(--ln)] text-[13px]">
            <span className="text-[var(--mu)]">AI engine</span>
            <div className="flex gap-1 p-[3px] rounded-lg bg-[var(--gl2)]">
              <button 
                className={`px-3 py-1 rounded-[7px] text-xs font-medium transition-colors ${(tier === 'free' || isPremiumDisabled) ? 'bg-gradient-to-br from-[var(--ac)] to-[var(--ac2)] text-white' : 'text-[var(--mu)] hover:text-white'}`} 
                onClick={() => setTier('free')}
              >
                Free
              </button>
              <button 
                className={`px-3 py-1 rounded-[7px] text-xs font-medium transition-colors ${(!isPremiumDisabled && tier === 'premium') ? 'bg-gradient-to-br from-[var(--ac)] to-[var(--ac2)] text-white' : isPremiumDisabled ? 'text-[var(--mu)] opacity-35 cursor-not-allowed line-through' : 'text-[var(--mu)] hover:text-white'}`} 
                onClick={() => !isPremiumDisabled && setTier('premium')}
                disabled={isPremiumDisabled}
              >
                Premium
              </button>
            </div>
          </div>
          <div className="text-xs text-[var(--mu)] py-1.5 mb-2">
            {isOnline ? 'Online. Free uses local and free-tier engines. Premium uses paid APIs.' : 'Offline. Premium is paused. Free runs on local engines only.'}
          </div>

          {isAdvanced && (
            <div className="animate-in fade-in slide-in-from-top-2">
              <div className="py-2 border-b border-[var(--ln)]">
                <div className="text-[var(--mu)] text-xs mb-1.5">Stage engines (from Capabilities)</div>
                <table className="w-full text-xs text-left">
                  <thead>
                    <tr className="text-[var(--mu)]">
                      <th className="py-1">Stage</th>
                      <th className="py-1">Offline</th>
                      <th className="py-1">Free online</th>
                      <th className="py-1">Premium</th>
                    </tr>
                  </thead>
                  <tbody>
                    {capabilities.map((c: any) => (
                      <tr key={c.stage} className="border-t border-[var(--ln)]">
                        <td className="py-1.5 font-medium">{c.stage}</td>
                        <td className="py-1.5">{c.offline}</td>
                        <td className="py-1.5">{c.free}</td>
                        <td className="py-1.5">{c.premium}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {mode === 'clone' && (
                <div className="py-2 border-b border-[var(--ln)]">
                  <div className="text-[var(--mu)] text-xs mb-2">Reference Video</div>
                  <div className="border border-dashed border-slate-700 rounded-md p-6 flex flex-col items-center justify-center text-center bg-slate-950 hover:border-slate-500 transition-colors cursor-pointer">
                    <div className="w-10 h-10 rounded-md bg-slate-900 border border-slate-800 flex items-center justify-center mb-2">
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-slate-400"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
                    </div>
                    <div className="text-[13px] font-medium text-slate-200">Select reference video file to analyze</div>
                    <div className="text-[11px] text-slate-500 mt-1">MP4, MOV up to 50MB</div>
                  </div>
                  <div className="text-center text-[var(--mu)] text-[11px] my-2">OR</div>
                  <div className="flex justify-between items-center text-[13px]">
                    <span className="text-[var(--mu)] shrink-0 mr-2">Paste URL</span>
                    <input type="text" value={jobConfig.referenceUrl} onChange={e => setJobConfig({...jobConfig, referenceUrl: e.target.value})} placeholder="https://..." className="flex-1 px-2.5 py-1.5 rounded-lg border border-[var(--ln)] bg-[var(--gl)] outline-none min-w-[120px]" />
                  </div>
                </div>
              )}
              
              <div className="flex justify-between items-center py-2 border-b border-[var(--ln)] text-[13px]">
                <span className="text-[var(--mu)]">Voice</span>
                <select 
                  value={jobConfig.voice} 
                  onChange={e => setJobConfig({...jobConfig, voice: e.target.value})}
                  className="px-2.5 py-1 rounded-lg border border-[var(--ln)] bg-[var(--gl)] outline-none min-w-[150px] text-right cursor-pointer"
                >
                  <option value="en-US-AriaNeural">Aria (Female)</option>
                  <option value="en-US-ChristopherNeural">Christopher (Male)</option>
                  <option value="en-US-GuyNeural">Guy (Male)</option>
                  <option value="en-US-AndrewNeural">Andrew (Male)</option>
                </select>
              </div>
              
              <div className="flex justify-between items-center py-2 border-b border-[var(--ln)] text-[13px]">
                <span className="text-[var(--mu)]">Visual style</span>
                <select 
                  value={jobConfig.visualStyle} 
                  onChange={e => setJobConfig({...jobConfig, visualStyle: e.target.value})}
                  className="px-2.5 py-1 rounded-lg border border-[var(--ln)] bg-[var(--gl)] outline-none min-w-[150px] text-right cursor-pointer"
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
            <div className="flex justify-between items-center p-[12px_14px] glass-panel bg-transparent">
              <span className="text-[var(--mu)] text-[13px]">Estimated cost</span>
              <b className="font-semibold text-[20px]">{tier === 'free' || isPremiumDisabled ? '$0.00' : 'unavailable'}</b>
            </div>
            
            {isOnline ? (
              <Button className="w-full" onClick={() => handleGenerate(true)}>Generate plan</Button>
            ) : (
              <div className="flex gap-2">
                <Button className="flex-1" variant="ghost" onClick={() => handleGenerate(true)}>Run locally now</Button>
                <Button className="flex-1" onClick={() => handleGenerate(false)}>Queue until online</Button>
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
