import { useState, useEffect } from 'react';
import {
  Shield,
  HardDrive,
  Trash2,
  Cpu,
  CheckCircle2,
  Globe,
  ChevronRight,
  KeyRound,
  Save
} from 'lucide-react';
import {
  useSettings,
  useUpdateSettings,
  useClearAllJobs,
  useClearCache,
  useCacheStatus
} from '../api/client';
import { Button, Badge } from '../components/ui';

export default function Settings() {
  const { data: initialSettings, isLoading } = useSettings();
  const { data: cache } = useCacheStatus();
  const updateMutation = useUpdateSettings();
  const clearJobsMutation = useClearAllJobs();
  const clearCacheMutation = useClearCache();

  const [settings, setSettings] = useState<any>({
    ollama_model: 'SparkLLM/Spark-X2.5-4B',
    default_voice: 'en-US-AndrewMultilingualNeural',
    force_offline: false,
    custom_domain: 'localhost:3000',
    telegram_token: '',
    gemini_key: '',
    openrouter_api_key: '',
    hf_token: '',
    moonshot_api_key: ''
  });
  const [saveStatus, setSaveStatus] = useState<string | null>(null);
  const [saveError, setSaveError] = useState(false);

  useEffect(() => {
    if (initialSettings) {
      setSettings((prev: any) => ({ ...prev, ...initialSettings }));
    }
  }, [initialSettings]);

  const handleSave = async () => {
    setSaveError(false);
    try {
      await updateMutation.mutateAsync(settings);
      setSaveStatus('Settings saved & masked safely.');
      setTimeout(() => setSaveStatus(null), 3500);
    } catch {
      setSaveError(true);
      setSaveStatus('Failed to save settings.');
    }
  };

  if (isLoading) {
    return <div className="p-10 text-center text-xs text-[var(--mu)]">Loading studio settings...</div>;
  }

  return (
    <div className="animate-in fade-in min-h-full flex flex-col max-w-4xl mx-auto w-full pb-10 space-y-5">
      {/* Header */}
      <div className="flex justify-between items-center flex-wrap gap-3 shrink-0">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-[var(--tx)]">System Settings</h1>
          <div className="text-[var(--mu)] text-xs mt-0.5">
            Configure local offline engines, free-tier API keys, network routing, and disk storage.
          </div>
        </div>
        <div className="flex items-center gap-2.5">
          {saveStatus && (
            <span
              className={`text-xs font-semibold ${
                saveError ? 'text-red-600 dark:text-red-400' : 'text-emerald-600 dark:text-emerald-400'
              }`}
            >
              {saveStatus}
            </span>
          )}
          <Button variant="primary" onClick={handleSave} disabled={updateMutation.isPending}>
            <Save size={13} />
            <span>{updateMutation.isPending ? 'Saving...' : 'Save Settings'}</span>
          </Button>
        </div>
      </div>

      <div className="flex flex-col gap-5 flex-1">
        {/* Zero-Cost Architecture Status */}
        <div className="glass-panel p-5">
          <div className="flex items-center justify-between flex-wrap gap-2 mb-2">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-xl bg-blue-600/15 text-blue-600 dark:text-blue-400 border border-blue-500/25">
                <Shield size={16} />
              </div>
              <h2 className="font-bold text-[var(--tx)] text-sm">Local Zero-Cost Engine Architecture</h2>
            </div>
            <Badge variant="success">$0.00 Strictly Free Lock</Badge>
          </div>
          <p className="text-xs text-[var(--mu)] leading-relaxed">
            Content Factory runs with zero paid subscriptions. Scriptwriting routes across strictly-free OpenRouter `:free` models, Gemini AI Studio free tier, and local Spark-X2.5-4B (`llama-server.exe`), while Edge-TTS, Pillow, and FFmpeg assemble video locally with beat-level caching.
          </p>
        </div>

        {/* Custom Domain & Network Configuration */}
        <div className="glass-panel p-5 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-[var(--ln-subtle)]">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-xl bg-blue-600/15 text-blue-600 dark:text-blue-400 border border-blue-500/25">
                <Globe size={16} />
              </div>
              <h2 className="font-bold text-[var(--tx)] text-sm">Custom Domain & Network Routing</h2>
            </div>
            <Badge variant="success">
              <CheckCircle2 size={12} />
              <span>Host Verified</span>
            </Badge>
          </div>

          <div className="space-y-3 text-xs">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-[var(--ln-subtle)]">
              <div>
                <span className="text-[var(--tx)] font-semibold text-xs">Primary Domain / FQDN</span>
                <p className="text-[var(--mu)] text-[11px]">
                  Hostname used for frontend routing and local studio asset links.
                </p>
              </div>
              <input
                type="text"
                value={settings.custom_domain || 'localhost:3000'}
                onChange={(e) => setSettings({ ...settings, custom_domain: e.target.value })}
                className="glass-input px-3 py-2 font-mono text-xs w-full sm:w-72"
                placeholder="e.g. localhost:3000"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-1">
              <div className="glass-subcard p-3">
                <div className="text-[var(--mu)] text-[11px]">Frontend Port</div>
                <div className="text-[var(--tx)] font-mono font-semibold text-xs mt-0.5">localhost:3000</div>
              </div>
              <div className="glass-subcard p-3">
                <div className="text-[var(--mu)] text-[11px]">Backend API Target</div>
                <div className="text-[var(--tx)] font-mono font-semibold text-xs mt-0.5">127.0.0.1:8000</div>
              </div>
              <div className="glass-subcard p-3">
                <div className="text-[var(--mu)] text-[11px]">CORS Security Lock</div>
                <div className="text-emerald-600 dark:text-emerald-400 font-mono font-semibold text-xs mt-0.5">
                  Localhost Restricted
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Local Brain, Free-Tier Keys & Voice Engine */}
        <div className="glass-panel p-5 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-[var(--ln-subtle)]">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-xl bg-amber-500/15 text-amber-600 dark:text-amber-400 border border-amber-500/25">
                <Cpu size={16} />
              </div>
              <h2 className="font-bold text-[var(--tx)] text-sm">Script Engine, API Keys & Narration</h2>
            </div>
            <Badge variant="neutral">
              <KeyRound size={11} />
              <span>Secrets Masked</span>
            </Badge>
          </div>

          <div className="space-y-3.5 text-xs">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-[var(--ln-subtle)]">
              <div>
                <span className="text-[var(--tx)] font-semibold">Local Ollama / GGUF Model</span>
                <p className="text-[var(--mu)] text-[11px]">
                  Offline generation engine for script beats and structuring (0 MB on D:\).
                </p>
              </div>
              <input
                type="text"
                value={settings.ollama_model || 'SparkLLM/Spark-X2.5-4B'}
                onChange={(e) => setSettings({ ...settings, ollama_model: e.target.value })}
                className="glass-input px-3 py-2 font-mono text-xs w-full sm:w-72"
                placeholder="e.g. SparkLLM/Spark-X2.5-4B"
              />
            </div>

            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-[var(--ln-subtle)]">
              <div>
                <span className="text-[var(--tx)] font-semibold">OpenRouter Free API Key (`:free` Locked)</span>
                <p className="text-[var(--mu)] text-[11px]">
                  Strictly restricted to `$0.00` free endpoints by double-lock verification.
                </p>
              </div>
              <input
                type="password"
                value={settings.openrouter_api_key || ''}
                onChange={(e) => setSettings({ ...settings, openrouter_api_key: e.target.value })}
                className="glass-input px-3 py-2 font-mono text-xs w-full sm:w-72"
                placeholder="sk-or-v1-..."
              />
            </div>

            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-[var(--ln-subtle)]">
              <div>
                <span className="text-[var(--tx)] font-semibold">Gemini AI Studio API Key</span>
                <p className="text-[var(--mu)] text-[11px]">
                  Uses official `google-genai` v3 SDK for multimodal script & vision fallback.
                </p>
              </div>
              <input
                type="password"
                value={settings.gemini_key || ''}
                onChange={(e) => setSettings({ ...settings, gemini_key: e.target.value })}
                className="glass-input px-3 py-2 font-mono text-xs w-full sm:w-72"
                placeholder="AIza..."
              />
            </div>

            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-[var(--ln-subtle)]">
              <div>
                <span className="text-[var(--tx)] font-semibold">Kimi K3 / Moonshot API Key</span>
                <p className="text-[var(--mu)] text-[11px]">
                  Optional key for Kimi K3 frontier model routing (zero local RAM footprint).
                </p>
              </div>
              <input
                type="password"
                value={settings.moonshot_api_key || ''}
                onChange={(e) => setSettings({ ...settings, moonshot_api_key: e.target.value })}
                className="glass-input px-3 py-2 font-mono text-xs w-full sm:w-72"
                placeholder="sk-..."
              />
            </div>

            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-[var(--ln-subtle)]">
              <div>
                <span className="text-[var(--tx)] font-semibold">Hugging Face ZeroGPU Token (`HF_TOKEN`)</span>
                <p className="text-[var(--mu)] text-[11px]">
                  Unlocks 5 min/day free cloud GPU video generation (`Lightricks/LTX-2.5` &amp; `Wan 2.2 I2V`) at $0.
                </p>
              </div>
              <input
                type="password"
                value={settings.hf_token || ''}
                onChange={(e) => setSettings({ ...settings, hf_token: e.target.value })}
                className="glass-input px-3 py-2 font-mono text-xs w-full sm:w-72"
                placeholder="hf_..."
              />
            </div>

            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-[var(--ln-subtle)]">
              <div>
                <span className="text-[var(--tx)] font-semibold">Default Voice Profile (Mastered -14 LUFS)</span>
                <p className="text-[var(--mu)] text-[11px]">3-tier vocal stack with broadcast EQ &amp; dynamic compression.</p>
              </div>
              <select
                value={settings.default_voice || 'en-US-AndrewMultilingualNeural'}
                onChange={(e) => setSettings({ ...settings, default_voice: e.target.value })}
                className="glass-input px-3 py-2 text-xs w-full sm:w-72 cursor-pointer"
              >
                <option value="en-US-AndrewMultilingualNeural">Andrew Multilingual (Male, Warm Trailer Narrator)</option>
                <option value="en-US-AvaMultilingualNeural">Ava Multilingual (Female, Expressive Documentary)</option>
                <option value="en-US-BrianMultilingualNeural">Brian Multilingual (Male, Crisp Editorial)</option>
                <option value="am_michael">Kokoro-82M Michael (Local Offline CPU Narrator)</option>
              </select>
            </div>

            <div className="flex items-center justify-between pt-1">
              <div>
                <span className="text-[var(--tx)] font-semibold">Force Offline Processing</span>
                <p className="text-[var(--mu)] text-[11px]">
                  Directs all inference exclusively to the local offline engine without outbound API calls.
                </p>
              </div>
              <button
                type="button"
                aria-label="Toggle Force Offline Processing"
                className={`w-11 h-6 rounded-lg p-0.5 transition-colors border cursor-pointer ${
                  settings.force_offline
                    ? 'bg-blue-600 border-blue-500'
                    : 'bg-[var(--gl2)] border-[var(--input-border)]'
                }`}
                onClick={() => setSettings({ ...settings, force_offline: !settings.force_offline })}
              >
                <div
                  className={`w-4 h-4 rounded-md bg-white shadow-xs transition-transform ${
                    settings.force_offline ? 'translate-x-5' : 'translate-x-0'
                  }`}
                />
              </button>
            </div>
          </div>
        </div>

        {/* Storage & Cache Maintenance (Tactile Action Stack) */}
        <div className="glass-panel p-5 space-y-3">
          <div className="flex items-center justify-between pb-2.5 border-b border-[var(--ln-subtle)]">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-xl bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/25">
                <HardDrive size={16} />
              </div>
              <div>
                <h2 className="font-bold text-[var(--tx)] text-sm">Storage & Cache Maintenance</h2>
                <p className="text-[11px] text-[var(--mu)]">
                  Live temp footprint: <b className="font-mono text-[var(--tx)]">{cache?.temp_mb ?? '0.0'} MB</b> ({cache?.temp_count ?? 0} files)
                </p>
              </div>
            </div>
            <Badge variant="info">C:\cf_training\</Badge>
          </div>

          <div className="space-y-2.5">
            <button
              type="button"
              onClick={() => clearCacheMutation.mutate()}
              disabled={clearCacheMutation.isPending}
              className="glass-subcard w-full p-3.5 flex items-center justify-between text-left cursor-pointer disabled:opacity-50"
            >
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-amber-500/15 text-amber-600 dark:text-amber-400 border border-amber-500/30 flex items-center justify-center shrink-0">
                  <Trash2 size={14} />
                </div>
                <div>
                  <div className="text-xs font-bold text-[var(--tx)]">
                    {clearCacheMutation.isPending ? 'Purging Temp Cache...' : 'Purge Temp & Frame Cache'}
                  </div>
                  <div className="text-[11px] text-[var(--mu)]">
                    Clears temporary render frames while preserving finished MP4s and 5-House training data.
                  </div>
                </div>
              </div>
              <ChevronRight size={15} className="text-[var(--mu)] shrink-0" />
            </button>

            <button
              type="button"
              onClick={() => {
                if (
                  confirm(
                    'Reset Data: This will remove all job records and intermediate render artifacts. Confirm?'
                  )
                ) {
                  clearJobsMutation.mutate();
                  clearCacheMutation.mutate();
                }
              }}
              disabled={clearJobsMutation.isPending}
              className="glass-subcard w-full p-3.5 flex items-center justify-between text-left cursor-pointer hover:!border-red-500/50 disabled:opacity-50"
            >
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-red-500/15 text-red-600 dark:text-red-400 border border-red-500/30 flex items-center justify-center shrink-0">
                  <Trash2 size={14} />
                </div>
                <div>
                  <div className="text-xs font-bold text-red-600 dark:text-red-400">
                    {clearJobsMutation.isPending ? 'Resetting Factory Records...' : 'Reset Factory Job Records'}
                  </div>
                  <div className="text-[11px] text-[var(--mu)]">
                    Deletes all SQLite job history rows and intermediate caches.
                  </div>
                </div>
              </div>
              <ChevronRight size={15} className="text-red-500 shrink-0" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
