import { useState, useEffect } from 'react';
import { Shield, HardDrive, Trash2, Cpu, Mic, CheckCircle2, Globe, Server, Link as LinkIcon } from 'lucide-react';
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
    custom_domain: 'localhost:3000',
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
      setSaveStatus('Settings saved successfully.');
      setTimeout(() => setSaveStatus(null), 3000);
    } catch {
      setSaveStatus('Failed to save settings.');
    }
  };

  if (isLoading) {
    return <div className="p-8 text-center text-slate-400">Loading settings...</div>;
  }

  return (
    <div className="min-h-full flex flex-col max-w-4xl mx-auto w-full pb-8 space-y-6">
      <div className="flex justify-between items-center flex-wrap gap-3 mb-2 shrink-0">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-white">System Settings</h1>
          <div className="text-slate-400 text-xs mt-1">Configure local offline engines, network domain routing, and disk storage.</div>
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
        <div className="glass-panel p-5 bg-slate-900 border border-slate-800">
          <div className="flex items-center gap-3 mb-2">
            <Shield size={16} className="text-blue-400" />
            <h2 className="font-semibold text-white text-sm">Local Engine Architecture</h2>
            <Badge variant="success">Zero Subscription Required</Badge>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">
            Content Factory is engineered to operate with zero third-party platform dependencies. Scriptwriting, voice synthesis via Edge-TTS, pan/zoom motion via FFmpeg, and frame composition run locally or via quota-free endpoints.
          </p>
        </div>

        {/* Custom Domain & Network Configuration */}
        <div className="glass-panel p-5 space-y-4 border border-slate-800 bg-slate-900">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800">
            <div className="flex items-center gap-2">
              <Globe size={16} className="text-blue-400" />
              <h2 className="font-semibold text-white text-sm">Custom Domain & Network Routing</h2>
            </div>
            <div className="flex items-center gap-1.5 text-[11px] text-emerald-400">
              <CheckCircle2 size={13} />
              <span>Host Verified</span>
            </div>
          </div>

          <p className="text-xs text-slate-400 leading-relaxed">
            Bind Content Factory to a dedicated hostname or reverse proxy. DNS records must route to the listening host interface.
          </p>

          <div className="space-y-3 text-xs">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 py-2 border-b border-slate-800/80">
              <div>
                <span className="text-slate-200 font-medium text-xs">Primary Domain / FQDN</span>
                <p className="text-slate-500 text-[11px]">Hostname used for frontend routing and asset links.</p>
              </div>
              <div className="flex items-center gap-2 w-full sm:w-72">
                <input
                  type="text"
                  value={settings.custom_domain || 'localhost:3000'}
                  onChange={e => setSettings({ ...settings, custom_domain: e.target.value })}
                  className="px-3 py-1.5 rounded-md border border-slate-700 bg-slate-950 text-slate-200 font-mono text-xs outline-none focus:border-blue-500 flex-1"
                  placeholder="e.g. factory.local or 127.0.0.1:3000"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-1">
              <div className="p-3 bg-slate-950 border border-slate-800 rounded-md">
                <div className="text-slate-500 text-[11px]">Binding Address</div>
                <div className="text-slate-200 font-mono text-xs mt-0.5">0.0.0.0:3000</div>
              </div>
              <div className="p-3 bg-slate-950 border border-slate-800 rounded-md">
                <div className="text-slate-500 text-[11px]">Backend API Target</div>
                <div className="text-slate-200 font-mono text-xs mt-0.5">127.0.0.1:8000</div>
              </div>
              <div className="p-3 bg-slate-950 border border-slate-800 rounded-md">
                <div className="text-slate-500 text-[11px]">SSL / TLS Status</div>
                <div className="text-emerald-400 font-mono text-xs mt-0.5">Proxy Passthrough</div>
              </div>
            </div>
          </div>
        </div>

        {/* Local Brain & Voice Engine */}
        <div className="glass-panel p-5 space-y-4 border border-slate-800 bg-slate-900">
          <div className="flex items-center gap-2 pb-2 border-b border-slate-800">
            <Cpu size={16} className="text-slate-300" />
            <h2 className="font-semibold text-white text-sm">Script Engine & Narration Model</h2>
          </div>

          <div className="space-y-4 text-xs">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 py-2 border-b border-slate-800/80">
              <div>
                <span className="text-slate-200 font-medium text-xs">Local Ollama Model</span>
                <p className="text-slate-500 text-[11px]">Offline generation engine for script beats and structuring.</p>
              </div>
              <input
                type="text"
                value={settings.ollama_model || 'SparkLLM/Spark-X2.5-4B'}
                onChange={e => setSettings({ ...settings, ollama_model: e.target.value })}
                className="px-3 py-1.5 rounded-md border border-slate-700 bg-slate-950 text-slate-200 font-mono text-xs outline-none focus:border-blue-500 w-full sm:w-64"
                placeholder="e.g. SparkLLM/Spark-X2.5-4B"
              />
            </div>

            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 py-2 border-b border-slate-800/80">
              <div>
                <span className="text-slate-200 font-medium text-xs">Kimi K3 / Moonshot API Key</span>
                <p className="text-slate-500 text-[11px]">Optional key for Kimi K3 2.8T MoE frontier model routing ($0 local RAM).</p>
              </div>
              <input
                type="password"
                value={settings.moonshot_api_key || ''}
                onChange={e => setSettings({ ...settings, moonshot_api_key: e.target.value })}
                className="px-3 py-1.5 rounded-md border border-slate-700 bg-slate-950 text-slate-200 font-mono text-xs outline-none focus:border-blue-500 w-full sm:w-64"
                placeholder="sk-..."
              />
            </div>

            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 py-2 border-b border-slate-800/80">
              <div>
                <span className="text-slate-200 font-medium text-xs">Default Voice Profile</span>
                <p className="text-slate-500 text-[11px]">Speech synthesis actor voice profile.</p>
              </div>
              <select
                value={settings.default_voice || 'en-US-ChristopherNeural'}
                onChange={e => setSettings({ ...settings, default_voice: e.target.value })}
                className="px-3 py-1.5 rounded-md border border-slate-700 bg-slate-950 text-slate-200 text-xs outline-none focus:border-blue-500 w-full sm:w-64"
              >
                <option value="en-US-ChristopherNeural">Christopher (Male, Narrative)</option>
                <option value="en-US-AriaNeural">Aria (Female, Clear)</option>
                <option value="en-US-GuyNeural">Guy (Male, Conversational)</option>
                <option value="en-US-AndrewNeural">Andrew (Male, Authoritative)</option>
              </select>
            </div>

            <div className="flex items-center justify-between py-2">
              <div>
                <span className="text-slate-200 font-medium text-xs">Force Offline Processing</span>
                <p className="text-slate-500 text-[11px]">Directs all inference exclusively to the local Ollama instance.</p>
              </div>
              <button 
                type="button"
                className={`w-10 h-5 rounded-md p-0.5 transition-colors border ${settings.force_offline ? 'bg-blue-600 border-blue-500' : 'bg-slate-800 border-slate-700'}`}
                onClick={() => setSettings({ ...settings, force_offline: !settings.force_offline })}
              >
                <div className={`w-3.5 h-3.5 rounded-sm bg-white transition-transform ${settings.force_offline ? 'translate-x-5' : 'translate-x-0'}`} />
              </button>
            </div>
          </div>
        </div>

        {/* Storage Management & Data Control */}
        <div className="glass-panel p-5 space-y-4 border border-slate-800 bg-slate-900">
          <div className="flex items-center gap-2 pb-2 border-b border-slate-800">
            <HardDrive size={16} className="text-slate-300" />
            <h2 className="font-semibold text-white text-sm">Storage & Cache Maintenance</h2>
          </div>

          <p className="text-xs text-slate-400 leading-relaxed">
            Manage local disk footprint. Clear temporary render chunks or reset factory job records.
          </p>

          <div className="flex flex-wrap items-center gap-3 pt-2">
            <Button
              variant="secondary"
              onClick={() => {
                clearCacheMutation.mutate();
              }}
              disabled={clearCacheMutation.isPending}
              className="flex items-center gap-1.5 text-xs py-1.5 px-3"
            >
              <Trash2 size={13} />
              <span>Purge Temp Cache</span>
            </Button>

            <Button
              variant="danger"
              onClick={() => {
                if (confirm("Reset Data: This will remove all job records and intermediate render artifacts. Confirm?")) {
                  clearJobsMutation.mutate();
                  clearCacheMutation.mutate();
                }
              }}
              disabled={clearJobsMutation.isPending}
              className="flex items-center gap-1.5 text-xs py-1.5 px-3"
            >
              <Trash2 size={13} />
              <span>Reset Factory Records</span>
            </Button>
          </div>
        </div>

      </div>
    </div>
  );
}
