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
  EyeOff,
  Mic,
  Sun,
  Moon,
  RotateCcw
} from 'lucide-react';
import {
  useSettings,
  useUpdateSettings,
  useClearAllJobs,
  useClearCache,
  useCacheStatus
} from '../api/client';
import { Button, Badge, ConfirmDialog, Tabs, Progress, ProgressRing } from '../components/ui';
import type { StudioTheme } from '../App';

const VOICE_PROFILES = [
  {
    id: 'en-US-AndrewMultilingualNeural',
    name: 'Andrew Multilingual',
    role: 'Warm Trailer Narrator',
    engine: 'Edge-TTS Neural ($0)',
    desc: 'Deep authoritative documentary baritone mastered to -14 LUFS'
  },
  {
    id: 'en-US-AvaMultilingualNeural',
    name: 'Ava Multilingual',
    role: 'Expressive Documentary',
    engine: 'Edge-TTS Neural ($0)',
    desc: 'Natural investigative pacing ideal for mystery & history essays'
  },
  {
    id: 'en-US-BrianMultilingualNeural',
    name: 'Brian Multilingual',
    role: 'Crisp Editorial',
    engine: 'Edge-TTS Neural ($0)',
    desc: 'Fast articulate cadence built for Viral Edu & explainers'
  },
  {
    id: 'am_michael',
    name: 'Kokoro-82M Michael',
    role: '100% Offline Local CPU',
    engine: 'ONNX int8 (88 MB)',
    desc: 'Runs locally with zero Wi-Fi or external network calls required'
  }
];

const THEME_MODES: Array<{ id: StudioTheme; label: string; desc: string; Icon: any }> = [
  {
    id: 'light-glass',
    label: 'Light Frosted Glass',
    desc: 'Daylight acrylic surfaces with crisp slate typography',
    Icon: Sun
  },
  {
    id: 'dark-glass',
    label: 'Dark Obsidian Glass',
    desc: 'Low-glare cinema grading suite with cobalt & cyan accents',
    Icon: Moon
  },
  {
    id: 'classic-dark',
    label: 'Classic Studio Dark',
    desc: 'Flat matte dark layout with zero backdrop blur overhead',
    Icon: RotateCcw
  }
];

export default function Settings() {
  const { data: initialSettings, isLoading } = useSettings();
  const { data: cache } = useCacheStatus();
  const updateMutation = useUpdateSettings();
  const clearJobsMutation = useClearAllJobs();
  const clearCacheMutation = useClearCache();

  const [activeTab, setActiveTab] = useState('Models & Credentials');
  const [isConfirmResetOpen, setIsConfirmResetOpen] = useState(false);
  const [showSecrets, setShowSecrets] = useState(false);
  const [activeTheme, setActiveTheme] = useState<StudioTheme>(() => {
    try {
      return (localStorage.getItem('cf_studio_theme') as StudioTheme) || 'light-glass';
    } catch {
      return 'light-glass';
    }
  });

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

  const applyThemeFromSettings = (nextTheme: StudioTheme) => {
    setActiveTheme(nextTheme);
    try {
      localStorage.setItem('cf_studio_theme', nextTheme);
      window.dispatchEvent(
        new StorageEvent('storage', { key: 'cf_studio_theme', newValue: nextTheme })
      );
    } catch {
      // ignore storage errors
    }
  };

  const handleSave = async (e?: FormEvent) => {
    if (e) e.preventDefault();
    setSaveError(false);
    try {
      await updateMutation.mutateAsync(settings);
      setSaveStatus('Preferences saved and secrets masked safely.');
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
  const activeStorageRoot = initialSettings?.storage_root || 'Workspace Storage';
  const activeModelsRoot = initialSettings?.models_root || 'Local Models Root';
  const tempMb = Number(cache?.temp_mb ?? 0);

  const providerReadiness = [
    { name: 'Gemini AI Studio', ready: Boolean(settings.gemini_key) },
    { name: 'Pexels HD B-Roll', ready: Boolean(initialSettings?.pexels_key) },
    { name: 'YouTube Data v3', ready: Boolean(initialSettings?.youtube_key) },
    { name: 'OpenRouter :free', ready: Boolean(settings.openrouter_api_key) },
    { name: 'HF ZeroGPU Video', ready: Boolean(settings.hf_token) },
    { name: 'Kokoro-82M Offline', ready: true }
  ];
  const readyCount = providerReadiness.filter((p) => p.ready).length;

  return (
    <form
      onSubmit={handleSave}
      action="/api/settings"
      method="POST"
      className="animate-in fade-in min-h-full flex flex-col max-w-6xl mx-auto w-full pb-10 space-y-5"
    >
      {/* Sticky Studio Preferences Header */}
      <div className="flex justify-between items-center flex-wrap gap-3 shrink-0">
        <div>
          <div className="flex items-center gap-2.5 flex-wrap">
            <h1 className="text-2xl font-bold tracking-tight text-[var(--tx)]">
              Studio Control Center
            </h1>
            <Badge variant="success">$0.00 Strictly Free Lock</Badge>
          </div>
          <p className="text-[var(--mu)] text-xs mt-0.5">
            Manage free-tier provider keys, narrator voice defaults, theme mode, and dynamic storage guardrails.
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
            <span>{updateMutation.isPending ? 'Saving...' : 'Save Preferences'}</span>
          </Button>
        </div>
      </div>

      {/* Live Provider Readiness Matrix Banner */}
      <div className="glass-panel p-4 flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <ProgressRing
            value={readyCount}
            max={providerReadiness.length}
            size={50}
            color="var(--ok)"
            centerText={`${readyCount}/${providerReadiness.length}`}
            label="Configured zero-cost studio providers"
          />
          <div>
            <h2 className="text-xs font-bold uppercase tracking-wider text-[var(--tx)]">
              Live Provider &amp; Local Engine Readiness
            </h2>
            <p className="text-[11px] text-[var(--mu)]">
              Active credentials detected in `.env` (secrets remain masked in all API responses)
            </p>
          </div>
        </div>

        <div className="pill-row-balance items-center gap-2">
          {providerReadiness.map((prov) => (
            <span
              key={prov.name}
              className={`px-2.5 py-1 rounded-xl text-[11px] font-semibold border inline-flex items-center gap-1.5 ${
                prov.ready
                  ? 'bg-emerald-500/12 border-emerald-500/35 text-emerald-700 dark:text-emerald-300'
                  : 'bg-[var(--gl2)] border-[var(--ln-subtle)] text-[var(--mu)]'
              }`}
            >
              <span
                className={`w-1.5 h-1.5 rounded-xs ${
                  prov.ready ? 'bg-emerald-500' : 'bg-slate-400'
                }`}
              />
              <span>{prov.name}</span>
            </span>
          ))}
        </div>
      </div>

      {/* Accessible Single-Row Settings Tablist */}
      <div className="-mb-2">
        <Tabs
          tabs={['Models & Credentials', 'Audio & Appearance', 'Network & Storage']}
          activeTab={activeTab}
          onChange={setActiveTab}
          ariaLabel="System settings categories"
        />
      </div>

      {/* =================================================================== */}
      {/* TAB 1: MODELS & MASKED CREDENTIALS                                  */}
      {/* =================================================================== */}
      <div
        role="tabpanel"
        aria-label="Models & Credentials"
        hidden={activeTab !== 'Models & Credentials'}
      >
        {activeTab === 'Models & Credentials' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
            {/* Left (5/12): Local CPU Brain & Offline Mode */}
            <div className="lg:col-span-5 glass-panel p-5 space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-[var(--ln-subtle)]">
                <div className="flex items-center gap-2.5">
                  <div className="p-2 rounded-xl bg-blue-600/15 text-blue-600 dark:text-blue-400 border border-blue-500/25">
                    <Cpu size={16} />
                  </div>
                  <div>
                    <h2 className="font-bold text-[var(--tx)] text-sm">Local CPU Brain</h2>
                    <p className="text-[11px] text-[var(--mu)]">16 GB RAM Sequencer Protected</p>
                  </div>
                </div>
                <Badge variant="info">{activeModelsRoot}</Badge>
              </div>

              <div className="space-y-1.5 text-xs">
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
                  className="glass-input px-3 py-2.5 font-mono text-xs w-full"
                  placeholder="SparkLLM/Spark-X2.5-4B"
                />
                <p className="text-[var(--mu)] text-[11px] leading-relaxed">
                  Wakes on demand with `-c 8192` KV-cache cap, sleeps after 75s idle, and unloads before Pass 2 FFmpeg encoding.
                </p>
              </div>

              <label
                htmlFor="setting-force-offline"
                className="glass-subcard p-3.5 flex items-center justify-between gap-3 cursor-pointer select-none"
              >
                <div>
                  <span className="text-xs font-bold text-[var(--tx)] block">
                    Force 100% Offline Execution
                  </span>
                  <span className="text-[11px] text-[var(--mu)]">
                    Disables outbound cloud calls and routes strictly to local weights
                  </span>
                </div>
                <input
                  id="setting-force-offline"
                  name="force_offline"
                  type="checkbox"
                  checked={Boolean(settings.force_offline)}
                  onChange={(e) => setSettings({ ...settings, force_offline: e.target.checked })}
                  className="w-4 h-4 accent-blue-600 rounded cursor-pointer shrink-0"
                />
              </label>
            </div>

            {/* Right (7/12): Free-Tier API Key Vault */}
            <div className="lg:col-span-7 glass-panel p-5 space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-[var(--ln-subtle)] flex-wrap gap-2">
                <div className="flex items-center gap-2.5">
                  <div className="p-2 rounded-xl bg-amber-500/15 text-amber-600 dark:text-amber-400 border border-amber-500/25">
                    <KeyRound size={16} />
                  </div>
                  <div>
                    <h2 className="font-bold text-[var(--tx)] text-sm">Free-Tier API Vault</h2>
                    <p className="text-[11px] text-[var(--mu)]">
                      Paste keys to unlock cloud acceleration at $0.00 billing
                    </p>
                  </div>
                </div>

                <button
                  type="button"
                  aria-pressed={showSecrets}
                  onClick={() => setShowSecrets((prev) => !prev)}
                  className="px-2.5 py-1 rounded-lg bg-[var(--gl2)] border border-[var(--input-border)] text-[11px] font-semibold text-[var(--tx)] flex items-center gap-1.5 cursor-pointer"
                >
                  {showSecrets ? <EyeOff size={12} /> : <Eye size={12} />}
                  <span>{showSecrets ? 'Hide Keys' : 'Reveal Typed Keys'}</span>
                </button>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
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
                    className="glass-input px-3 py-2.5 font-mono text-xs w-full"
                    placeholder="AIza..."
                  />
                  <p className="text-[var(--mu)] text-[11px]">Primary free-tier script &amp; vision router.</p>
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
                    className="glass-input px-3 py-2.5 font-mono text-xs w-full"
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
                    className="glass-input px-3 py-2.5 font-mono text-xs w-full"
                    placeholder="hf_..."
                  />
                  <p className="text-[var(--mu)] text-[11px]">Free ZeroGPU `LTX-2.5` &amp; `Wan 2.2` video clips.</p>
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
                    className="glass-input px-3 py-2.5 font-mono text-xs w-full"
                    placeholder="sk-..."
                  />
                  <p className="text-[var(--mu)] text-[11px]">Optional frontier MoE script routing.</p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* =================================================================== */}
      {/* TAB 2: AUDIO ARCHETYPES & STUDIO APPEARANCE                         */}
      {/* =================================================================== */}
      <div
        role="tabpanel"
        aria-label="Audio & Appearance"
        hidden={activeTab !== 'Audio & Appearance'}
      >
        {activeTab === 'Audio & Appearance' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
            {/* Narrator Voice Radio Cards (7/12) */}
            <fieldset className="lg:col-span-7 glass-panel p-5 border-0 m-0 space-y-3">
              <div className="flex items-center justify-between pb-3 border-b border-[var(--ln-subtle)]">
                <legend className="text-sm font-bold text-[var(--tx)] flex items-center gap-2 p-0">
                  <Mic size={16} className="text-emerald-600 dark:text-emerald-400" />
                  <span>Default Narrator Voice (-14 LUFS Mastered)</span>
                </legend>
                <Badge variant="success">Sidechain Ducking Active</Badge>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {VOICE_PROFILES.map((vp) => {
                  const selected = (settings.default_voice || 'en-US-AndrewMultilingualNeural') === vp.id;
                  const inputId = `settings-voice-${vp.id}`;
                  return (
                    <div key={vp.id} className="relative">
                      <input
                        id={inputId}
                        type="radio"
                        name="default_voice"
                        value={vp.id}
                        checked={selected}
                        onChange={() => setSettings({ ...settings, default_voice: vp.id })}
                        className="visually-hidden-input"
                      />
                      <label
                        htmlFor={inputId}
                        className={`h-full p-3.5 rounded-xl border flex flex-col justify-between gap-2 cursor-pointer transition-all select-none ${
                          selected
                            ? 'bg-blue-600/12 border-blue-500 ring-1 ring-blue-500/35'
                            : 'bg-[var(--gl2)] border-[var(--ln)] hover:border-blue-500/45'
                        }`}
                      >
                        <div>
                          <div className="flex items-center justify-between gap-2">
                            <span className="text-xs font-bold text-[var(--tx)]">{vp.name}</span>
                            {selected && (
                              <CheckCircle2 size={14} className="text-blue-600 dark:text-blue-400 shrink-0" />
                            )}
                          </div>
                          <span className="inline-block mt-1 text-[10px] font-mono px-2 py-0.5 rounded bg-[var(--input-bg)] border border-[var(--ln-subtle)] text-[var(--mu)]">
                            {vp.engine}
                          </span>
                          <p className="text-[11px] text-[var(--mu)] mt-2 leading-snug">{vp.desc}</p>
                        </div>
                      </label>
                    </div>
                  );
                })}
              </div>
            </fieldset>

            {/* Studio Theme Surface Selector (5/12) */}
            <fieldset className="lg:col-span-5 glass-panel p-5 border-0 m-0 space-y-3">
              <div className="flex items-center justify-between pb-3 border-b border-[var(--ln-subtle)]">
                <legend className="text-sm font-bold text-[var(--tx)] flex items-center gap-2 p-0">
                  <Shield size={16} className="text-blue-600 dark:text-blue-400" />
                  <span>Studio Surface Theme</span>
                </legend>
                <Badge variant="info">Live Sync</Badge>
              </div>

              <div className="space-y-2.5">
                {THEME_MODES.map((tm) => {
                  const TIcon = tm.Icon;
                  const isCurrent = activeTheme === tm.id;
                  const inputId = `settings-theme-${tm.id}`;
                  return (
                    <div key={tm.id} className="relative">
                      <input
                        id={inputId}
                        type="radio"
                        name="studio_surface_theme"
                        value={tm.id}
                        checked={isCurrent}
                        onChange={() => applyThemeFromSettings(tm.id)}
                        className="visually-hidden-input"
                      />
                      <label
                        htmlFor={inputId}
                        className={`p-3.5 rounded-xl border flex items-center gap-3 cursor-pointer transition-all select-none ${
                          isCurrent
                            ? 'bg-blue-600/12 border-blue-500 ring-1 ring-blue-500/35'
                            : 'bg-[var(--gl2)] border-[var(--ln)] hover:border-blue-500/45'
                        }`}
                      >
                        <div
                          className={`w-9 h-9 rounded-xl border flex items-center justify-center shrink-0 ${
                            isCurrent
                              ? 'bg-blue-600 text-white border-blue-500'
                              : 'bg-[var(--input-bg)] text-[var(--mu)] border-[var(--input-border)]'
                          }`}
                        >
                          <TIcon size={16} />
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="text-xs font-bold text-[var(--tx)]">{tm.label}</div>
                          <div className="text-[11px] text-[var(--mu)] leading-snug">{tm.desc}</div>
                        </div>
                      </label>
                    </div>
                  );
                })}
              </div>
            </fieldset>
          </div>
        )}
      </div>

      {/* =================================================================== */}
      {/* TAB 3: DYNAMIC NETWORK & STORAGE MAINTENANCE                        */}
      {/* =================================================================== */}
      <div
        role="tabpanel"
        aria-label="Network & Storage"
        hidden={activeTab !== 'Network & Storage'}
      >
        {activeTab === 'Network & Storage' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
            {/* Dynamic Network Routing (6/12) */}
            <div className="lg:col-span-6 glass-panel p-5 space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-[var(--ln-subtle)]">
                <div className="flex items-center gap-2.5">
                  <div className="p-2 rounded-xl bg-blue-600/15 text-blue-600 dark:text-blue-400 border border-blue-500/25">
                    <Globe size={16} />
                  </div>
                  <h2 className="font-bold text-[var(--tx)] text-sm">Dynamic Host &amp; API Routing</h2>
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
                    className="glass-input px-3 py-2.5 font-mono text-xs w-full"
                    placeholder={runtimeHost || 'studio.example.com'}
                  />
                  <p className="text-[var(--mu)] text-[11px]">
                    Used dynamically for CORS allowlisting and OpenRouter HTTP-Referer headers.
                  </p>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                  <div className="glass-subcard p-3 min-w-0">
                    <div className="text-[var(--mu)] text-[11px]">Active UI Origin</div>
                    <div className="text-[var(--tx)] font-mono font-bold text-xs mt-0.5 truncate">
                      {activeFrontendHost}
                    </div>
                  </div>
                  <div className="glass-subcard p-3 min-w-0">
                    <div className="text-[var(--mu)] text-[11px]">Backend API Host</div>
                    <div className="text-[var(--tx)] font-mono font-bold text-xs mt-0.5 truncate">
                      {activeApiHost}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Storage Footprint & LRU Maintenance (6/12) */}
            <div className="lg:col-span-6 glass-panel p-5 space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-[var(--ln-subtle)] gap-2 flex-wrap">
                <div className="flex items-center gap-2.5 min-w-0">
                  <div className="p-2 rounded-xl bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/25 shrink-0">
                    <HardDrive size={16} />
                  </div>
                  <div className="min-w-0">
                    <h2 className="font-bold text-[var(--tx)] text-sm">Scratch &amp; LRU Cache Maintenance</h2>
                    <p className="text-[11px] text-[var(--mu)] truncate">
                      Output archive: <b className="font-mono text-[var(--tx)]">{cache?.output_mb ?? '0.0'} MB</b> ({cache?.output_count ?? 0} renders)
                    </p>
                  </div>
                </div>
                <Badge variant="info">{activeStorageRoot}</Badge>
              </div>

              <div className="space-y-1.5">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-[var(--mu)] font-medium">Scratch &amp; Beat Cache Usage</span>
                  <span className="font-mono font-bold text-[var(--tx)]">
                    {tempMb.toFixed(1)} / 300.0 MB LRU Cap
                  </span>
                </div>
                <Progress
                  value={tempMb}
                  max={300}
                  color={tempMb > 240 ? 'var(--wa)' : 'var(--ac)'}
                  label="Scratch cache usage out of 300 MB cap"
                />
              </div>

              <div className="space-y-2.5 pt-1">
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
                        {clearCacheMutation.isPending
                          ? 'Purging Scratch Cache...'
                          : 'Purge Temp, Beat & AI Clip Cache'}
                      </div>
                      <div className="text-[11px] text-[var(--mu)]">
                        Frees scratch space while preserving finished MP4s and 5-House dataset records.
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
                        {clearJobsMutation.isPending
                          ? 'Resetting Job Records...'
                          : 'Reset Studio Job History'}
                      </div>
                      <div className="text-[11px] text-[var(--mu)]">
                        Deletes SQLite job rows and intermediate caches.
                      </div>
                    </div>
                  </div>
                  <ChevronRight size={15} className="text-red-500 shrink-0" />
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

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
    </form>
  );
}
