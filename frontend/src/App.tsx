import { useState } from 'react';
import { Routes, Route, useNavigate, useLocation, Link } from 'react-router-dom';
import { LayoutDashboard, PlusCircle, AlignEndHorizontal, Vault as VaultIcon, Bot, Settings as SettingsIcon, Menu, HardDrive, Trash2, Globe } from 'lucide-react';
import { useConnectivity } from './lib/connectivity';
import { useCacheStatus, useClearCache } from './api/client';
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

const NavItem = ({ to, icon: Icon, label, isCollapsed }: any) => {
  const navigate = useNavigate();
  const location = useLocation();
  const isActive = location.pathname === to;
  return (
    <div 
      onClick={() => navigate(to)}
      className={`flex items-center gap-3 px-3 py-2 rounded-md cursor-pointer transition-colors border border-transparent ${
        isActive ? 'bg-slate-800 text-white border-slate-700' : 'text-slate-400 hover:text-white hover:bg-slate-900'
      }`}
    >
      <Icon size={18} className="shrink-0" />
      {!isCollapsed && <span className="whitespace-nowrap font-medium text-xs">{label}</span>}
    </div>
  );
};

export default function App() {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const isOnline = useConnectivity();
  const { data: cache } = useCacheStatus();
  const clearCacheMutation = useClearCache();

  return (
    <div className={`grid h-screen w-full overflow-hidden transition-all duration-200 ${isCollapsed ? 'grid-cols-[64px_1fr]' : 'grid-cols-[210px_1fr]'}`}>
      
      {/* Sidebar - Clean industrial navigation */}
      <aside className="border-r border-slate-800 bg-[#090d16] p-3 flex flex-col gap-1 overflow-y-auto h-full z-20">
        <div 
          onClick={() => setIsCollapsed(!isCollapsed)} 
          className="flex items-center gap-2.5 p-2 rounded-md cursor-pointer mb-2 hover:bg-slate-900"
          title="Toggle sidebar"
        >
          <div className="w-7 h-7 rounded-md bg-blue-600 flex items-center justify-center shrink-0">
            <Menu size={15} color="white" />
          </div>
          {!isCollapsed && <div className="font-semibold text-xs tracking-wider text-white uppercase whitespace-nowrap">Content Factory</div>}
        </div>

        <NavItem to="/" icon={LayoutDashboard} label="Dashboard" isCollapsed={isCollapsed} />
        <NavItem to="/create" icon={PlusCircle} label="Create Video" isCollapsed={isCollapsed} />
        <NavItem to="/pipeline" icon={AlignEndHorizontal} label="Pipeline" isCollapsed={isCollapsed} />
        <NavItem to="/vault" icon={VaultIcon} label="Director Vault" isCollapsed={isCollapsed} />
        <NavItem to="/agents" icon={Bot} label="Agents" isCollapsed={isCollapsed} />
        <NavItem to="/settings" icon={SettingsIcon} label="Settings" isCollapsed={isCollapsed} />

        <div className="mt-auto flex flex-col gap-2 pt-3 border-t border-slate-800 text-[11px] text-slate-500">
          {!isCollapsed && (
            <div className="flex items-center justify-between px-1">
              <Link to="/privacy" className="hover:text-slate-300 transition-colors">Privacy</Link>
              <span>·</span>
              <Link to="/terms" className="hover:text-slate-300 transition-colors">Terms & Conditions</Link>
            </div>
          )}
          <div className="flex gap-2 items-center p-1 text-slate-400 whitespace-nowrap">
            <div className="w-6 h-6 rounded bg-slate-800 border border-slate-700 flex items-center justify-center font-semibold text-[10px] text-slate-200 shrink-0">CF</div>
            {!isCollapsed && <div className="truncate text-[11px]">Production Studio</div>}
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex flex-col min-w-0 h-full overflow-hidden relative bg-[#0b0f19]">
        {/* Top bar */}
        <header className="flex items-center justify-between gap-3 px-5 py-2.5 border-b border-slate-800 bg-[#090d16] z-20 shrink-0">
          <div className="text-xs text-slate-400 font-medium flex items-center gap-2">
            <span className="text-white font-semibold">Content Factory</span>
            <span className="text-slate-600">/</span>
            <span>Production Engine</span>
          </div>
          
          <div className="flex items-center gap-3 text-xs text-slate-400">
            {/* Custom Domain Badge */}
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-slate-800 bg-slate-900 text-slate-300 font-mono text-[11px]">
              <Globe size={13} className="text-blue-400" />
              <span>localhost:3000</span>
            </div>

            {/* Online/Offline Status */}
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-slate-800 bg-slate-900 text-slate-300 text-xs">
              <div className={`w-2 h-2 rounded-full ${isOnline ? 'bg-emerald-500' : 'bg-amber-500'}`} />
              <span>{isOnline ? 'Online' : 'Offline'}</span>
            </div>
            
            {/* Real Temp Folder & Cache Counter */}
            <div className="flex items-center gap-2 px-2.5 py-1 rounded-md border border-slate-800 bg-slate-900 text-xs text-slate-400">
              <HardDrive size={13} className="text-blue-400 shrink-0" />
              <span>Cache: <b className="text-slate-200 font-mono">{cache?.temp_mb ?? '0.0'} MB</b></span>
              <button
                onClick={() => clearCacheMutation.mutate()}
                disabled={clearCacheMutation.isPending || !(cache?.temp_mb > 0)}
                title="Clear temporary frames and cache"
                className="ml-1 text-[11px] text-slate-400 hover:text-red-400 flex items-center gap-1 transition-colors disabled:opacity-40 cursor-pointer"
              >
                <Trash2 size={12} />
                <span>{clearCacheMutation.isPending ? 'Clearing...' : 'Clear'}</span>
              </button>
            </div>
          </div>
        </header>

        {/* Offline Notice */}
        {!isOnline && (
          <div className="px-5 py-2 bg-amber-950/40 border-b border-amber-500/30 text-amber-300 text-xs shrink-0">
            System is offline. Cloud requests are suspended. Jobs will execute using local engines.
          </div>
        )}

        {/* Routes */}
        <main className="flex-1 overflow-y-auto p-5 relative bg-transparent">
          <Routes>
            <Route path="/" element={<Dashboard />} />
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
        </main>
      </div>
    </div>
  );
}
