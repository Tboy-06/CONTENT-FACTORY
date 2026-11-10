import { useState, useEffect } from 'react';
import { Shield, HardDrive, Trash2, Cpu, Mic, CheckCircle2 } from 'lucide-react';
import { useSettings, useUpdateSettings, useClearAllJobs, useClearCache } from '../api/client';
import { Button, Badge } from '../components/ui';

export default function Settings() {
  const { data: initialSettings, isLoading } = useSettings();
  const updateMutation = useUpdateSettings();
  const clearJobsMutation = useClearAllJobs();
  const clearCacheMutation = useClearCache();

  const [settings, setSettings] = useState<any>({
    ollama_model: 'SparkLLM/Spark-X2.5-4B',
    default_voice: 'en-US-ChristopherNeural',
    force_offline: false,
    telegram_token: '',
    gemini_key: ''
  });
  const [saveStatus, setSaveStatus] = useState<string | null>(null);

  useEffect(() => {
    if (initialSettings) {
      setSettings((prev: any) => ({ ...prev, ...initialSettings }));
    }
  }, [initialSettings]);

  const handleSave = async () => {
    try {
      await updateMutation.mutateAsync(settings);
      setSaveStatus('Settings saved successfully!');
      setTimeout(() => setSaveStatus(null), 3000);
    } catch {
      setSaveStatus('Failed to save settings.');
    }
  };

  if (isLoading) {
    return <div className="p-8 text-center text-[var(--mu)]">Loading settings...</div>;
  }

  return (
    <div className="animate-in fade-in min-h-full flex flex-col max-w-4xl mx-auto w-full pb-8 space-y-6">
      <div className="flex justify-between items-center flex-wrap gap-3 mb-2 shrink-0">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight text-white">Studio Settings</h1>
          <div className="text-[var(--mu)] text-[13px]">Configure local offline engines, zero-cost AI brains, and storage management.</div>
        </div>
        <div className="flex items-center gap-2">
          {saveStatus && <span className="text-xs text-emerald-400 font-medium">{saveStatus}</span>}
          <Button variant="primary" onClick={handleSave} disabled={updateMutation.isPending}>
            {updateMutation.isPending ? 'Saving...' : 'Save Settings'}
          </Button>
        </div>
      </div>

      <div className="flex flex-col gap-6 flex-1 overflow-y-auto pb-8">
        
        {/* Zero-Cost Architecture Status */}
        <div className="glass-panel p-5 bg-gradient-to-r from-blue-950/30 to-slate-900/60 border-blue-500/20">
          <div className="flex items-center gap-3 mb-2">
            <Shield size={18} className="text-blue-400" />
            <h2 className="font-semibold text-white text-[15px]">Zero-Cost Local Architecture</h2>
            <Badge variant="success">100% Free / No Subscriptions</Badge>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">
            Content Factory is pre-configured to run with $0 API expenses. Scriptwriting, voiceover synthesis (Edge-TTS), Ken Burns zooms (FFmpeg), and motion typography operate entirely offline or keyless.
          </p>
        </div>

        {/* Local Brain & Voice Engine */}
        <div className="glass-panel p-5 space-y-4">
          <div className="flex items-center gap-2.5 pb-2 border-b border-slate-800">
            <Cpu size={16} className="text-cyan-400" />
            <h2 className="font-semibold text-white text-[15px]">Documentary AI Brain & Voice</h2>
          </div>

          <div className="space-y-4 text-xs">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 py-2 border-b border-slate-800/80">
              <div>
                <span className="text-slate-200 font-medium text-sm">Local Brain Model (Ollama)</span>
                <p className="text-slate-400 text-[11px]">Primary model for documentary script beats and structure.</p>
              </div>
              <input
                type="text"
                value={settings.ollama_model || 'SparkLLM/Spark-X2.5-4B'}
                onChange={e => setSettings({ ...settings, ollama_model: e.target.value })}
                className="px-3 py-1.5 rounded-lg border border-slate-700 bg-slate-950 text-slate-200 font-mono text-xs outline-none focus:border-blue-500 w-full sm:w-64"
                placeholder="e.g. SparkLLM/Spark-X2.5-4B"
              />
            </div>

            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 py-2 border-b border-slate-800/80">
              <div>
                <span className="text-slate-200 font-medium text-sm">Default Documentary Voice</span>
                <p className="text-slate-400 text-[11px]">High-fidelity Edge-TTS voice actor for narration.</p>
              </div>
              <select
                value={settings.default_voice || 'en-US-ChristopherNeural'}
                onChange={e => setSettings({ ...settings, default_voice: e.target.value })}
                className="px-3 py-1.5 rounded-lg border border-slate-700 bg-slate-950 text-slate-200 text-xs outline-none focus:border-blue-500 w-full sm:w-64"
              >
                <option value="en-US-ChristopherNeural">Christopher (Male, Deep Storytelling)</option>
                <option value="en-US-AriaNeural">Aria (Female, Clear & Expressive)</option>
                <option value="en-US-GuyNeural">Guy (Male, Conversational)</option>
                <option value="en-US-AndrewNeural">Andrew (Male, Warm Authority)</option>
              </select>
            </div>

            <div className="flex items-center justify-between py-2">
              <div>
                <span className="text-slate-200 font-medium text-sm">Force Local Offline Mode</span>
                <p className="text-slate-400 text-[11px]">Bypasses all network lookups and routes directly to local engines.</p>
              </div>
              <div 
                className={`w-11 h-6 rounded-full p-1 cursor-pointer transition-colors ${settings.force_offline ? 'bg-blue-600' : 'bg-slate-700'}`}
                onClick={() => setSettings({ ...settings, force_offline: !settings.force_offline })}
              >
                <div className={`w-4 h-4 rounded-full bg-white transition-transform ${settings.force_offline ? 'translate-x-5' : 'translate-x-0'}`} />
              </div>
            </div>
          </div>
        </div>

        {/* Storage Management & Danger Zone */}
        <div className="glass-panel p-5 space-y-4 border-red-500/20">
          <div className="flex items-center gap-2.5 pb-2 border-b border-slate-800">
            <HardDrive size={16} className="text-red-400" />
            <h2 className="font-semibold text-white text-[15px]">Storage & Factory Reset</h2>
          </div>

          <p className="text-xs text-slate-400 leading-relaxed">
            Manage your local SSD disk footprint. Clear intermediate render frames or wipe completed job history to reclaim storage.
          </p>

          <div className="flex flex-wrap items-center gap-3 pt-2">
            <Button
              variant="secondary"
              onClick={() => {
                clearCacheMutation.mutate();
              }}
              disabled={clearCacheMutation.isPending}
              className="flex items-center gap-1.5 text-xs !py-2 !px-3"
            >
              <Trash2 size={13} />
              <span>Purge Temp Cache</span>
            </Button>

            <Button
              variant="danger"
              onClick={() => {
                if (confirm("Reset Factory: This will delete ALL job records, rendered beats, and outputs. Continue?")) {
                  clearJobsMutation.mutate();
                  clearCacheMutation.mutate();
                }
              }}
              disabled={clearJobsMutation.isPending}
              className="flex items-center gap-1.5 text-xs !py-2 !px-3"
            >
              <Trash2 size={13} />
              <span>Reset All Factory Data</span>
            </Button>
          </div>
        </div>

      </div>
    </div>
  );
}
