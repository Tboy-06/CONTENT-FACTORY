import { useState, useEffect, type FormEvent } from 'react';
import {
  Shield,
  HardDrive,
  Trash2,
  Cpu,
  CheckCircle2,
  Globe,
  ChevronRight,
  KeyRound,
  Save,
  Eye,
  EyeOff
} from 'lucide-react';
import {
  useSettings,
  useUpdateSettings,
  useClearAllJobs,
  useClearCache,
  useCacheStatus
} from '../api/client';
import { Button, Badge, ConfirmDialog } from '../components/ui';

export default function Settings() {
  const { data: initialSettings, isLoading } = useSettings();
  const { data: cache } = useCacheStatus();
  const updateMutation = useUpdateSettings();
  const clearJobsMutation = useClearAllJobs();
  const clearCacheMutation = useClearCache();
  const [isConfirmResetOpen, setIsConfirmResetOpen] = useState(false);
  const [showSecrets, setShowSecrets] = useState(false);

  const runtimeHost = typeof window !== 'undefined' ? window.location.host : '';

  const [settings, setSettings] = useState<any>({
    ollama_model: 'SparkLLM/Spark-X2.5-4B',
    default_voice: 'en-US-AndrewMultilingualNeural',
    force_offline: false,
    custom_domain: runtimeHost,
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

  const handleSave = async (e?: FormEvent) => {
    if (e) e.preventDefault();
    setSaveError(false);
    try {
      await updateMutation.mutateAsync(settings);
      setSaveStatus('Settings saved and secrets masked safely.');
      setTimeout(() => setSaveStatus(null), 3500);
    } catch {
      setSaveError(true);
      setSaveStatus('Failed to save settings.');
    }
  };

  if (isLoading) {
    return <div className="p-10 text-center text-xs text-[var(--mu)]">Loading studio settings...</div>;
  }

  const activeFrontendHost = settings.custom_domain || runtimeHost || 'Active Browser Host';
  const activeApiHost = initialSettings?.api_host || 'Configured Backend Proxy';
  const activeStorageRoot = initialSettings?.storage_root || 'External Scratch Root';

  return (
    <form
      onSubmit={handleSave}
      action="/api/settings"
      method="POST"
      className="animate-in fade-in min-h-full flex flex-col max-w-6xl mx-auto w-full pb-10 space-y-5"
    >
      {/* Header */}
      <div className="flex justify-between items-center flex-wrap gap-3 shrink-0">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-[var(--tx)]">System Settings</h1>
          <p className="text-[var(--mu)] text-xs mt-0.5">
            Configure local offline models, free-tier API credentials, dynamic network routing, and workspace storage.
          </p>
        </div>
        <div className="flex items-center gap-2.5">
          {saveStatus && (
            <span
              role="status"
              className={`text-xs font-semibold ${
                saveError ? 'text-red-600 dark:text-red-400' : 'text-emerald-600 dark:text-emerald-400'
              }`}
            >
              {saveStatus}
            </span>
          )}
          <Button type="submit" variant="primary" disabled={updateMutation.isPending}>
            <Save size={13} />
            <span>{updateMutation.isPending ? 'Saving...' : 'Save Settings'}</span>
          </Button>
        </div>
      </div>

      {/* Zero-Cost Architecture Banner */}
      <div className="glass-panel p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="p-2.5 rounded-xl bg-blue-600/15 text-blue-600 dark:text-blue-400 border border-blue-500/25 shrink-0">
            <Shield size={18} />
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h2 className="font-bold text-[var(--tx)] text-sm">Zero-Cost Studio Architecture</h2>
              <Badge variant="success">$0.00 Strictly Free Lock</Badge>
            </div>
            <p className="text-xs text-[var(--mu)] mt-1 leading-relaxed">
              Scriptwriting routes across strictly-free OpenRouter `:free` endpoints, Gemini AI Studio free tier, and local Spark-X2.5-4B (`llama-server`), while Edge-TTS, Kokoro-82M ONNX, Pillow, and FFmpeg assemble video locally with dynamic workspace storage paths.
            </p>
          </div>
        </div>
      </div>

      {/* 2-Column Bento Settings Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
        {/* LEFT COLUMN (7/12): Script Engine, Masked API Keys & Voice Profile */}
        <div className="lg:col-span-7 glass-panel p-5 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-[var(--ln-subtle)] flex-wrap gap-2">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-xl bg-amber-500/15 text-amber-600 dark:text-amber-400 border border-amber-500/25">
                <Cpu size={16} />
              </div>
              <div>
                <h2 className="font-bold text-[var(--tx)] text-sm">Models, Free-Tier Keys &amp; Voice</h2>
                <p className="text-[11px] text-[var(--mu)]">Stored locally in `.env` and masked in API responses</p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                aria-pressed={showSecrets}
                onClick={() => setShowSecrets((prev) => !prev)}
                className="px-2.5 py-1 rounded-lg bg-[var(--gl2)] border border-[var(--input-border)] text-[11px] font-semibold text-[var(--tx)] flex items-center gap-1.5 cursor-pointer"
              >
                {showSecrets ? <EyeOff size={12} /> : <Eye size={12} />}
                <span>{showSecrets ? 'Hide Keys' : 'Reveal Typed Keys'}</span>
              </button>
              <Badge variant="neutral">
                <KeyRound size={11} />
                <span>Masked</span>
              </Badge>
            </div>
          </div>

          <div className="space-y-3.5 text-xs">
            <div className="space-y-1">
              <label htmlFor="setting-ollama-model" className="text-[var(--tx)] font-semibold block">
                Local GGUF / Ollama Model Identifier
              </label>
              <input
                id="setting-ollama-model"
                name="ollama_model"
                type="text"
                autoCorrect="off"
                autoCapitalize="none"
                spellCheck={false}
                value={settings.ollama_model || 'SparkLLM/Spark-X2.5-4B'}
                onChange={(e) => setSettings({ ...settings, ollama_model: e.target.value })}
                className="glass-input px-3 py-2 font-mono text-xs w-full"
                placeholder="SparkLLM/Spark-X2.5-4B"
              />
              <p className="text-[var(--mu)] text-[11px]">
                On-demand local CPU inference engine; automatically unloaded before Pass 2 FFmpeg encoding to protect 16 GB RAM.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 pt-1">
              <div className="space-y-1">
                <label htmlFor="setting-gemini-key" className="text-[var(--tx)] font-semibold block">
                  Gemini AI Studio Key
                </label>
                <input
                  id="setting-gemini-key"
                  name="gemini_key"
                  type={showSecrets ? 'text' : 'password'}
                  autoComplete="off"
                  autoCorrect="off"
                  autoCapitalize="none"
                  spellCheck={false}
                  value={settings.gemini_key || ''}
                  onChange={(e) => setSettings({ ...settings, gemini_key: e.target.value })}
                  className="glass-input px-3 py-2 font-mono text-xs w-full"
                  placeholder="AIza..."
                />
                <p className="text-[var(--mu)] text-[11px]">Free-tier script &amp; multimodal fallback.</p>
              </div>

              <div className="space-y-1">
                <label htmlFor="setting-openrouter-key" className="text-[var(--tx)] font-semibold block">
                  OpenRouter Key (`:free` Locked)
                </label>
                <input
                  id="setting-openrouter-key"
                  name="openrouter_api_key"
                  type={showSecrets ? 'text' : 'password'}
                  autoComplete="off"
                  autoCorrect="off"
                  autoCapitalize="none"
                  spellCheck={false}
                  value={settings.openrouter_api_key || ''}
                  onChange={(e) => setSettings({ ...settings, openrouter_api_key: e.target.value })}
                  className="glass-input px-3 py-2 font-mono text-xs w-full"
                  placeholder="sk-or-v1-..."
                />
                <p className="text-[var(--mu)] text-[11px]">Double-locked to `$0.00` `:free` models.</p>
              </div>

              <div className="space-y-1">
                <label htmlFor="setting-hf-token" className="text-[var(--tx)] font-semibold block">
                  Hugging Face Token (`HF_TOKEN`)
                </label>
                <input
                  id="setting-hf-token"
                  name="hf_token"
                  type={showSecrets ? 'text' : 'password'}
                  autoComplete="off"
                  autoCorrect="off"
                  autoCapitalize="none"
                  spellCheck={false}
                  value={settings.hf_token || ''}
                  onChange={(e) => setSettings({ ...settings, hf_token: e.target.value })}
                  className="glass-input px-3 py-2 font-mono text-xs w-full"
                  placeholder="hf_..."
                />
                <p className="text-[var(--mu)] text-[11px]">Unlocks free ZeroGPU `LTX-2.5` &amp; `Wan 2.2` clips.</p>
              </div>

              <div className="space-y-1">
                <label htmlFor="setting-moonshot-key" className="text-[var(--tx)] font-semibold block">
                  Kimi K3 / Moonshot Key (Optional)
                </label>
                <input
                  id="setting-moonshot-key"
                  name="moonshot_api_key"
                  type={showSecrets ? 'text' : 'password'}
                  autoComplete="off"
                  autoCorrect="off"
                  autoCapitalize="none"
                  spellCheck={false}
                  value={settings.moonshot_api_key || ''}
                  onChange={(e) => setSettings({ ...settings, moonshot_api_key: e.target.value })}
                  className="glass-input px-3 py-2 font-mono text-xs w-full"
                  placeholder="sk-..."
                />
                <p className="text-[var(--mu)] text-[11px]">Optional cloud MoE script routing.</p>
              </div>
            </div>

            <div className="pt-2 border-t border-[var(--ln-subtle)] space-y-1.5">
              <label htmlFor="setting-default-voice" className="text-[var(--tx)] font-semibold block">
                Default Narrator Voice (-14 LUFS Broadcast EQ)
              </label>
              <select
                id="setting-default-voice"
                name="default_voice"
                value={settings.default_voice || 'en-US-AndrewMultilingualNeural'}
                onChange={(e) => setSettings({ ...settings, default_voice: e.target.value })}
                className="glass-input px-3 py-2.5 text-xs w-full cursor-pointer"
              >
                <option value="en-US-AndrewMultilingualNeural">Andrew Multilingual (Male, Warm Trailer Narrator)</option>
                <option value="en-US-AvaMultilingualNeural">Ava Multilingual (Female, Expressive Documentary)</option>
                <option value="en-US-BrianMultilingualNeural">Brian Multilingual (Male, Crisp Editorial)</option>
                <option value="am_michael">Kokoro-82M Michael (Local Offline CPU Narrator)</option>
              </select>
            </div>

            <div className="pt-2 border-t border-[var(--ln-subtle)] flex items-center justify-between gap-3">
              <div>
                <label htmlFor="setting-force-offline" className="text-[var(--tx)] font-semibold cursor-pointer">
                  Force 100% Offline Processing
                </label>
                <p className="text-[var(--mu)] text-[11px]">
                  Routes scriptwriting and voice synthesis strictly through local CPU weights without outbound calls.
                </p>
              </div>
              <input
                id="setting-force-offline"
                name="force_offline"
                type="checkbox"
                checked={Boolean(settings.force_offline)}
                onChange={(e) => setSettings({ ...settings, force_offline: e.target.checked })}
                className="w-4 h-4 accent-blue-600 rounded cursor-pointer shrink-0"
              />
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN (5/12): Dynamic Network Routing & Storage Maintenance */}
        <div className="lg:col-span-5 flex flex-col gap-5">
          {/* Dynamic Network Configuration */}
          <div className="glass-panel p-5 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-[var(--ln-subtle)]">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-xl bg-blue-600/15 text-blue-600 dark:text-blue-400 border border-blue-500/25">
                  <Globe size={16} />
                </div>
                <h2 className="font-bold text-[var(--tx)] text-sm">Dynamic Host &amp; Network</h2>
              </div>
              <Badge variant="success">
                <CheckCircle2 size={12} />
                <span>Connected</span>
              </Badge>
            </div>

            <div className="space-y-3 text-xs">
              <div className="space-y-1">
                <label htmlFor="setting-custom-domain" className="text-[var(--tx)] font-semibold block">
                  Studio Host / Public Domain
                </label>
                <input
                  id="setting-custom-domain"
                  name="custom_domain"
                  type="text"
                  autoCorrect="off"
                  autoCapitalize="none"
                  spellCheck={false}
                  value={settings.custom_domain || runtimeHost}
                  onChange={(e) => setSettings({ ...settings, custom_domain: e.target.value })}
                  className="glass-input px-3 py-2 font-mono text-xs w-full"
                  placeholder={runtimeHost || 'studio.example.com'}
                />
                <p className="text-[var(--mu)] text-[11px]">
                  Resolved dynamically from environment or active browser host.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 pt-1">
                <div className="glass-subcard p-3 min-w-0">
                  <div className="text-[var(--mu)] text-[11px]">Active UI Origin</div>
                  <div className="text-[var(--tx)] font-mono font-semibold text-xs mt-0.5 truncate">
                    {activeFrontendHost}
                  </div>
                </div>
                <div className="glass-subcard p-3 min-w-0">
                  <div className="text-[var(--mu)] text-[11px]">Backend API Host</div>
                  <div className="text-[var(--tx)] font-mono font-semibold text-xs mt-0.5 truncate">
                    {activeApiHost}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Storage & Cache Maintenance */}
          <div className="glass-panel p-5 space-y-3.5">
            <div className="flex items-center justify-between pb-2.5 border-b border-[var(--ln-subtle)] gap-2 flex-wrap">
              <div className="flex items-center gap-2.5 min-w-0">
                <div className="p-2 rounded-xl bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/25 shrink-0">
                  <HardDrive size={16} />
                </div>
                <div className="min-w-0">
                  <h2 className="font-bold text-[var(--tx)] text-sm">Workspace Storage &amp; LRU Cache</h2>
                  <p className="text-[11px] text-[var(--mu)] truncate">
                    Scratch footprint: <b className="font-mono text-[var(--tx)]">{cache?.temp_mb ?? '0.0'} MB</b> ({cache?.temp_count ?? 0} files · 300 MB LRU cap)
                  </p>
                </div>
              </div>
              <Badge variant="info">{activeStorageRoot}</Badge>
            </div>

            <div className="space-y-2.5">
              <button
                type="button"
                onClick={() => clearCacheMutation.mutate()}
                disabled={clearCacheMutation.isPending}
                className="glass-subcard w-full p-3.5 flex items-center justify-between text-left cursor-pointer disabled:opacity-50"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-8 h-8 rounded-lg bg-amber-500/15 text-amber-600 dark:text-amber-400 border border-amber-500/30 flex items-center justify-center shrink-0">
                    <Trash2 size={14} />
                  </div>
                  <div className="min-w-0">
                    <div className="text-xs font-bold text-[var(--tx)]">
                      {clearCacheMutation.isPending ? 'Purging Scratch Cache...' : 'Purge Temp, Beat & AI Clip Cache'}
                    </div>
                    <div className="text-[11px] text-[var(--mu)]">
                      Clears scratch clips while preserving finished MP4 exports and training records.
                    </div>
                  </div>
                </div>
                <ChevronRight size={15} className="text-[var(--mu)] shrink-0" />
              </button>

              <button
                type="button"
                onClick={() => setIsConfirmResetOpen(true)}
                disabled={clearJobsMutation.isPending}
                className="glass-subcard w-full p-3.5 flex items-center justify-between text-left cursor-pointer hover:!border-red-500/50 disabled:opacity-50"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-8 h-8 rounded-lg bg-red-500/15 text-red-600 dark:text-red-400 border border-red-500/30 flex items-center justify-center shrink-0">
                    <Trash2 size={14} />
                  </div>
                  <div className="min-w-0">
                    <div className="text-xs font-bold text-red-600 dark:text-red-400">
                      {clearJobsMutation.isPending ? 'Resetting Job Records...' : 'Reset Studio Job History'}
                    </div>
                    <div className="text-[11px] text-[var(--mu)]">
                      Deletes SQLite job rows and intermediate caches.
                    </div>
                  </div>
                </div>
                <ChevronRight size={15} className="text-red-500 shrink-0" />
              </button>

              <ConfirmDialog
                isOpen={isConfirmResetOpen}
                title="Reset Studio Job History?"
                description="This removes all SQLite job records and intermediate render artifacts while preserving your 5-House training dataset."
                confirmLabel="Reset Records"
                onConfirm={() => {
                  setIsConfirmResetOpen(false);
                  clearJobsMutation.mutate();
                  clearCacheMutation.mutate();
                }}
                onCancel={() => setIsConfirmResetOpen(false)}
              />
            </div>
          </div>
        </div>
      </div>
    </form>
  );
}
