import { useState, useEffect, useRef, useCallback } from 'react';
import { Routes, Route, useNavigate, useLocation, Link } from 'react-router-dom';
import {
  LayoutDashboard,
  PlusCircle,
  AlignEndHorizontal,
  Vault as VaultIcon,
  Bot,
  Settings as SettingsIcon,
  Menu,
  HardDrive,
  Trash2,
  Search,
  Sun,
  Moon,
  RotateCcw,
  SlidersHorizontal,
  Target,
  X
} from 'lucide-react';
import { useConnectivity } from './lib/connectivity';
import { useCacheStatus, useClearCache, useJobs } from './api/client';
import Create from './pages/Create';
import Copilot from './pages/Copilot';
import Pipeline from './pages/Pipeline';
import QC1 from './pages/QC1';
import Vault from './pages/Vault';
import Settings from './pages/Settings';
import Dashboard from './pages/Dashboard';
import Agents from './pages/Agents';
import Privacy from './pages/Privacy';
import Terms from './pages/Terms';

export type StudioTheme = 'light-glass' | 'dark-glass' | 'classic-dark';

const NavItem = ({ to, icon: Icon, label, badgeCount, isCollapsed, isLightGlass, onNavigate }: any) => {
  const location = useLocation();
  const isActive =
    to === '/'
      ? location.pathname === '/'
      : location.pathname === to || location.pathname.startsWith(`${to}/`);
  return (
    <button
      type="button"
      aria-current={isActive ? 'page' : undefined}
      onClick={() => onNavigate(to)}
      title={isCollapsed ? label : undefined}
      className={`w-full text-left flex items-center justify-between gap-2 px-3 py-2 rounded-xl cursor-pointer transition-all border ${
        isActive
          ? isLightGlass
            ? 'bg-blue-600 text-white border-blue-500 shadow-sm'
            : 'bg-slate-800/90 text-white border-slate-700 shadow-sm'
          : isLightGlass
          ? 'text-slate-600 hover:text-slate-900 hover:bg-white/60 border-transparent'
          : 'text-slate-400 hover:text-white hover:bg-slate-900/60 border-transparent'
      }`}
    >
      <span className="flex items-center gap-3 min-w-0">
        <Icon size={17} className="shrink-0" />
        {!isCollapsed && <span className="whitespace-nowrap font-medium text-xs truncate">{label}</span>}
      </span>
      {!isCollapsed && badgeCount !== undefined && badgeCount > 0 && (
        <span
          className={`font-mono text-[10px] font-bold px-1.5 py-0.2 rounded-md shrink-0 ${
            isActive
              ? 'bg-white/20 text-white'
              : isLightGlass
              ? 'bg-slate-200/90 text-slate-700'
              : 'bg-slate-800 text-slate-300 border border-slate-700'
          }`}
        >
          {badgeCount}
        </span>
      )}
    </button>
  );
};

function syncColorSchemeMeta(activeTheme: StudioTheme) {
  const scheme = activeTheme === 'light-glass' ? 'light' : 'dark';
  let meta = document.querySelector('meta[name="color-scheme"]') as HTMLMetaElement | null;
  if (!meta) {
    meta = document.createElement('meta');
    meta.name = 'color-scheme';
    document.head.appendChild(meta);
  }
  meta.content = scheme;
  document.documentElement.dataset.studioMode = activeTheme;
  try {
    localStorage.setItem('cf_studio_theme', activeTheme);
    localStorage.setItem('color-scheme', scheme);
  } catch {}
}

export default function App() {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [theme, setTheme] = useState<StudioTheme>(() => {
    try {
      const saved = localStorage.getItem('cf_studio_theme') as StudioTheme | null;
      return saved || 'light-glass';
    } catch {
      return 'light-glass';
    }
  });
  const [globalSearch, setGlobalSearch] = useState('');
  const mainWorkspaceRef = useRef<HTMLElement | null>(null);
  const navigate = useNavigate();
  const location = useLocation();
  const isOnline = useConnectivity();
  const { data: cache } = useCacheStatus();
  const { data: navJobs = [] } = useJobs();
  const clearCacheMutation = useClearCache();

  const pipelineAlertCount = navJobs.filter(
    (j: any) =>
      j.current_stage === 'QC1' ||
      j.status === 'AWAITING_APPROVAL' ||
      j.status === 'RUNNING'
  ).length;
  const vaultReadyCount = navJobs.filter(
    (j: any) =>
      j.status === 'COMPLETED' ||
      j.status === 'PUBLISHED' ||
      j.current_stage === 'QC1' ||
      j.current_stage === 'READY_TO_PUBLISH'
  ).length;

  const activeRoomName = location.pathname.startsWith('/create')
    ? 'Production Deck'
    : location.pathname.startsWith('/copilot')
    ? 'Niche Scorer'
    : location.pathname.startsWith('/pipeline')
    ? 'Render Pipeline'
    : location.pathname.startsWith('/qc1')
    ? 'QC1 Studio'
    : location.pathname.startsWith('/vault')
    ? 'Director Vault'
    : location.pathname.startsWith('/agents')
    ? 'Signal Topology'
    : location.pathname.startsWith('/settings')
    ? 'Control Center'
    : 'Command Center';

  useEffect(() => {
    syncColorSchemeMeta(theme);
  }, [theme]);

  useEffect(() => {
    const onStorage = (e: StorageEvent) => {
      if (e.key === 'cf_studio_theme' && e.newValue) {
        const next = e.newValue as StudioTheme;
        setTheme(next);
        syncColorSchemeMeta(next);
      }
    };
    window.addEventListener('storage', onStorage);
    return () => window.removeEventListener('storage', onStorage);
  }, []);

  const transitionNavigate = useCallback(
    (to: string) => {
      if (location.pathname === to) return;
      const doc = document as Document & {
        startViewTransition?: (cb: () => void) => { finished: Promise<void> };
      };
      if (!doc.startViewTransition) {
        navigate(to);
        mainWorkspaceRef.current?.focus({ preventScroll: true });
        return;
      }
      const transition = doc.startViewTransition(() => {
        navigate(to);
      });
      transition.finished.finally(() => {
        mainWorkspaceRef.current?.focus({ preventScroll: true });
      });
    },
    [location.pathname, navigate]
  );

  const handleThemeSwitch = useCallback((nextTheme: StudioTheme) => {
    const doc = document as Document & {
      startViewTransition?: (cb: () => void) => { finished: Promise<void> };
    };
    if (!doc.startViewTransition) {
      setTheme(nextTheme);
      return;
    }
    doc.startViewTransition(() => {
      syncColorSchemeMeta(nextTheme);
      setTheme(nextTheme);
    });
  }, []);

  const isLightGlass = theme === 'light-glass';
  const isClassic = theme === 'classic-dark';

  return (
    <div
      className={`grid h-screen w-full overflow-hidden transition-all duration-200 ${
        isCollapsed ? 'grid-cols-[68px_1fr]' : 'grid-cols-[216px_1fr]'
      }`}
    >
      {/* Sidebar */}
      <aside
        className={`p-3 flex flex-col gap-1.5 overflow-y-auto h-full z-20 transition-colors ${
          isLightGlass
            ? 'border-r border-white/80 bg-white/55 backdrop-blur-2xl text-slate-800'
            : 'border-r border-slate-800/80 bg-[#090d16]/90 backdrop-blur-2xl text-slate-200'
        }`}
      >
        <div
          onClick={() => setIsCollapsed(!isCollapsed)}
          className={`flex items-center gap-2.5 p-2 rounded-xl cursor-pointer mb-2 transition-colors ${
            isLightGlass ? 'hover:bg-white/70' : 'hover:bg-slate-900'
          }`}
          title="Toggle sidebar"
        >
          <div className="w-7 h-7 rounded-lg bg-blue-600 flex items-center justify-center shrink-0 shadow-sm">
            <Menu size={15} color="white" />
          </div>
          {!isCollapsed && (
            <div className="flex items-center gap-1.5">
              <span
                className={`font-bold text-xs tracking-wider uppercase whitespace-nowrap ${
                  isLightGlass ? 'text-slate-900' : 'text-white'
                }`}
              >
                Content Factory
              </span>
            </div>
          )}
        </div>

        <NavItem to="/" icon={LayoutDashboard} label="Dashboard" isCollapsed={isCollapsed} isLightGlass={isLightGlass} onNavigate={transitionNavigate} />
        <NavItem to="/create" icon={PlusCircle} label="Create Video" isCollapsed={isCollapsed} isLightGlass={isLightGlass} onNavigate={transitionNavigate} />
        <NavItem to="/copilot" icon={Target} label="Niche Scorer" isCollapsed={isCollapsed} isLightGlass={isLightGlass} onNavigate={transitionNavigate} />
        <NavItem to="/pipeline" icon={AlignEndHorizontal} label="Pipeline" badgeCount={pipelineAlertCount} isCollapsed={isCollapsed} isLightGlass={isLightGlass} onNavigate={transitionNavigate} />
        <NavItem to="/vault" icon={VaultIcon} label="Director Vault" badgeCount={vaultReadyCount} isCollapsed={isCollapsed} isLightGlass={isLightGlass} onNavigate={transitionNavigate} />
        <NavItem to="/agents" icon={Bot} label="Agents" isCollapsed={isCollapsed} isLightGlass={isLightGlass} onNavigate={transitionNavigate} />
        <NavItem to="/settings" icon={SettingsIcon} label="Settings" isCollapsed={isCollapsed} isLightGlass={isLightGlass} onNavigate={transitionNavigate} />

        <div
          className={`mt-auto flex flex-col gap-2 pt-3 border-t text-[11px] ${
            isLightGlass ? 'border-slate-200/80 text-slate-500' : 'border-slate-800 text-slate-500'
          }`}
        >
          {!isCollapsed && (
            <div className="flex items-center justify-between px-1">
              <Link to="/privacy" className="hover:underline">Privacy</Link>
              <span>·</span>
              <Link to="/terms" className="hover:underline">Terms & Conditions</Link>
            </div>
          )}
          <div className="flex gap-2 items-center p-1 whitespace-nowrap">
            <div
              className={`w-6 h-6 rounded-lg border flex items-center justify-center font-bold text-[10px] shrink-0 ${
                isLightGlass
                  ? 'bg-white border-slate-200 text-slate-800 shadow-2xs'
                  : 'bg-slate-800 border-slate-700 text-slate-200'
              }`}
            >
              CF
            </div>
            {!isCollapsed && (
              <div className={`truncate text-[11px] font-medium ${isLightGlass ? 'text-slate-700' : 'text-slate-400'}`}>
                Production Studio
              </div>
            )}
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex flex-col min-w-0 h-full overflow-hidden relative">
        {/* 01 | TOP COMMAND HEADER */}
        <header
          className={`flex items-center justify-between gap-4 px-6 py-3 z-20 shrink-0 transition-colors ${
            isLightGlass
              ? 'border-b border-white/80 bg-white/60 backdrop-blur-xl'
              : 'border-b border-slate-800/80 bg-[#090d16]/85 backdrop-blur-xl'
          }`}
        >
          {/* Left: Brand Title & Micro Badge */}
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-red-600 flex items-center justify-center text-white font-bold text-xs shadow-xs">
              CF
            </div>
            <span className={`font-bold text-sm tracking-tight ${isLightGlass ? 'text-slate-900' : 'text-white'}`}>
              CONTENT-FACTORY
            </span>
            <span
              className={`px-2 py-0.5 rounded-md text-[10px] font-semibold uppercase tracking-wider border ${
                isLightGlass
                  ? 'bg-slate-200/80 text-slate-700 border-white'
                  : 'bg-slate-800 text-slate-300 border-slate-700'
              }`}
            >
              {activeRoomName}
            </span>
          </div>

          {/* Center: Global Frosted Search Input */}
          <search aria-label="Global studio search" className="flex-1 max-w-md mx-2">
            <div
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-xl border transition-all ${
                isLightGlass
                  ? 'bg-white/75 border-white shadow-inner text-slate-800 focus-within:bg-white focus-within:border-blue-400'
                  : 'bg-slate-900/80 border-slate-700/80 text-slate-200 focus-within:border-blue-500'
              }`}
            >
              <Search size={14} className={isLightGlass ? 'text-slate-400' : 'text-slate-500'} />
              <input
                type="search"
                value={globalSearch}
                onChange={(e) => {
                  setGlobalSearch(e.target.value);
                  window.dispatchEvent(new CustomEvent('cf-global-search', { detail: e.target.value }));
                  if (location.pathname !== '/') navigate('/');
                }}
                placeholder="Search jobs, assets or reflexion rules..."
                className="w-full bg-transparent text-xs outline-none placeholder:text-slate-400"
              />
              {globalSearch && (
                <button
                  type="button"
                  onClick={() => {
                    setGlobalSearch('');
                    window.dispatchEvent(new CustomEvent('cf-global-search', { detail: '' }));
                  }}
                  className="text-slate-400 hover:text-slate-600 cursor-pointer"
                  title="Clear search"
                >
                  <X size={13} />
                </button>
              )}
            </div>
          </search>

          {/* Right: Theme Switcher (Light Glass / Dark Glass / Classic Revert) + Telemetry + Avatar */}
          <div className="flex items-center gap-2.5 text-xs">
            {/* 3-Way Theme Toggle Pill */}
            <div
              className={`flex items-center p-0.5 rounded-xl border ${
                isLightGlass ? 'bg-slate-200/75 border-white' : 'bg-slate-900 border-slate-800'
              }`}
              title="Switch between Light Frosted Glass, Dark Obsidian Glass, or revert to Classic Dark UI"
            >
              <button
                type="button"
                onClick={() => handleThemeSwitch('light-glass')}
                className={`flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-medium transition-all cursor-pointer ${
                  theme === 'light-glass'
                    ? 'bg-white text-slate-900 shadow-xs'
                    : 'text-slate-500 hover:text-slate-300'
                }`}
              >
                <Sun size={12} />
                <span>Light Glass</span>
              </button>
              <button
                type="button"
                onClick={() => handleThemeSwitch('dark-glass')}
                className={`flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-medium transition-all cursor-pointer ${
                  theme === 'dark-glass'
                    ? 'bg-blue-600 text-white shadow-xs'
                    : isLightGlass
                    ? 'text-slate-600 hover:text-slate-900'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                <Moon size={12} />
                <span>Dark Glass</span>
              </button>
              <button
                type="button"
                onClick={() => handleThemeSwitch('classic-dark')}
                className={`flex items-center gap-1 px-2 py-1 rounded-lg text-[11px] font-medium transition-all cursor-pointer ${
                  theme === 'classic-dark'
                    ? 'bg-amber-600 text-white shadow-xs'
                    : isLightGlass
                    ? 'text-slate-600 hover:text-slate-900'
                    : 'text-slate-400 hover:text-white'
                }`}
                title="Instant 1-Click Revert to Previous Classic UI"
              >
                <RotateCcw size={11} />
                <span>Classic</span>
              </button>
            </div>

            {/* Online/Offline Status */}
            <div
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-xl border text-xs font-medium ${
                isLightGlass
                  ? 'bg-white/80 border-white text-slate-700 shadow-2xs'
                  : 'bg-slate-900 border-slate-800 text-slate-300'
              }`}
            >
              <div className={`w-2 h-2 rounded-xs ${isOnline ? 'bg-emerald-500' : 'bg-amber-500'}`} />
              <span>{isOnline ? 'Online' : 'Offline'}</span>
            </div>

            {/* Cache Counter */}
            <div
              className={`hidden xl:flex items-center gap-2 px-2.5 py-1 rounded-xl border text-xs ${
                isLightGlass
                  ? 'bg-white/80 border-white text-slate-600 shadow-2xs'
                  : 'bg-slate-900 border-slate-800 text-slate-400'
              }`}
            >
              <HardDrive size={13} className="text-blue-500 shrink-0" />
              <span>
                Cache: <b className={`font-mono ${isLightGlass ? 'text-slate-900' : 'text-slate-200'}`}>{cache?.temp_mb ?? '0.0'} MB</b>
              </span>
              <button
                onClick={() => clearCacheMutation.mutate()}
                disabled={clearCacheMutation.isPending || !(cache?.temp_mb > 0)}
                title="Clear temporary frames and cache"
                className="ml-1 text-[11px] hover:text-red-500 flex items-center gap-1 transition-colors disabled:opacity-40 cursor-pointer"
              >
                <Trash2 size={12} />
              </button>
            </div>

            {/* Studio Director Avatar & Utility Button */}
            <div className="flex items-center gap-1.5 pl-1">
              <div
                onClick={() => navigate('/settings')}
                className={`w-8 h-8 rounded-xl border flex items-center justify-center font-bold text-xs cursor-pointer shadow-xs transition-transform hover:scale-105 ${
                  isLightGlass
                    ? 'bg-gradient-to-br from-slate-800 to-slate-950 text-white border-white'
                    : 'bg-gradient-to-br from-blue-600 to-cyan-600 text-white border-slate-700'
                }`}
                title="Director Profile & Studio Settings"
              >
                DR
              </div>
              <button
                onClick={() => navigate('/settings')}
                className={`p-1.5 rounded-lg border cursor-pointer transition-colors ${
                  isLightGlass
                    ? 'bg-white/70 border-white text-slate-600 hover:text-slate-900'
                    : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-white'
                }`}
                title="System Preferences"
              >
                <SlidersHorizontal size={14} />
              </button>
            </div>
          </div>
        </header>

        {/* Offline Notice */}
        {!isOnline && (
          <div className="px-6 py-2 bg-amber-500/15 border-b border-amber-500/30 text-amber-600 dark:text-amber-300 text-xs shrink-0">
            System is offline. Cloud requests are suspended. Jobs will execute using local engines.
          </div>
        )}

        {/* Main Workspace Container */}
        <main
          id="main-workspace-container"
          ref={mainWorkspaceRef}
          tabIndex={-1}
          className={`flex-1 overflow-y-auto outline-none ${isClassic ? 'p-5' : 'p-4 md:p-6'} relative`}
        >
          <div className={isClassic ? 'min-h-full' : 'acrylic-shell min-h-full p-5 md:p-7'}>
            <Routes>
              <Route path="/" element={<Dashboard theme={theme} globalSearch={globalSearch} />} />
              <Route path="/create" element={<Create />} />
              <Route path="/copilot" element={<Copilot />} />
              <Route path="/copilot/:mode" element={<Copilot />} />
              <Route path="/pipeline" element={<Pipeline />} />
              <Route path="/qc1/:id" element={<QC1 />} />
              <Route path="/vault" element={<Vault />} />
              <Route path="/agents" element={<Agents />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="/privacy" element={<Privacy />} />
              <Route path="/terms" element={<Terms />} />
            </Routes>
          </div>
        </main>
      </div>
    </div>
  );
}
