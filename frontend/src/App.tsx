import { useState } from 'react';
import { Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import { LayoutDashboard, PlusCircle, AlignEndHorizontal, Vault as VaultIcon, Bot, Settings as SettingsIcon, Menu } from 'lucide-react';
import { useConnectivity } from './lib/connectivity';
import { useSpend } from './api/client';
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
      className={`flex items-center gap-3 px-3 py-2.5 rounded-lg cursor-pointer transition-colors border border-transparent ${
        isActive ? 'bg-blue-600/15 text-white border-blue-500/40' : 'text-[var(--mu)] hover:text-white hover:bg-[var(--gl)]'
      }`}
    >
      <Icon size={20} className="shrink-0" />
      {!isCollapsed && <span className="whitespace-nowrap font-medium text-sm">{label}</span>}
    </div>
  );
};

export default function App() {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const isOnline = useConnectivity();
  const { data: spend } = useSpend();

  return (
    <div className={`grid min-h-screen w-full transition-all duration-200 ${isCollapsed ? 'grid-cols-[68px_1fr]' : 'grid-cols-[220px_1fr]'}`}>
      
      {/* Sidebar - Sticky and scrollable if viewport is short */}
      <aside className="border-r border-[var(--ln)] bg-[rgba(11,14,23,0.85)] p-[14px_10px] flex flex-col gap-1 overflow-y-auto sticky top-0 h-screen z-20">
        <div 
          onClick={() => setIsCollapsed(!isCollapsed)} 
          className="flex items-center gap-2.5 p-[6px_8px] rounded-lg cursor-pointer mb-3 hover:bg-[var(--gl)]"
          title="Toggle sidebar"
        >
          <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center shadow-sm shrink-0">
            <Menu size={16} color="white" />
          </div>
          {!isCollapsed && <b className="font-semibold text-sm leading-tight text-white whitespace-nowrap">Content<br/>Factory</b>}
        </div>

        <NavItem to="/" icon={LayoutDashboard} label="Dashboard" isCollapsed={isCollapsed} />
        <NavItem to="/create" icon={PlusCircle} label="Create" isCollapsed={isCollapsed} />
        <NavItem to="/pipeline" icon={AlignEndHorizontal} label="Pipeline" isCollapsed={isCollapsed} />
        <NavItem to="/vault" icon={VaultIcon} label="Vault" isCollapsed={isCollapsed} />
        <NavItem to="/agents" icon={Bot} label="Agents" isCollapsed={isCollapsed} />
        <NavItem to="/settings" icon={SettingsIcon} label="Settings" isCollapsed={isCollapsed} />

        <div className="mt-auto flex flex-col gap-2 pt-2 border-t border-[var(--ln)]">
          <div className="flex gap-2.5 items-center p-1 text-xs text-[var(--mu)] whitespace-nowrap">
            <div className="w-[28px] h-[28px] rounded-md bg-slate-800 border border-slate-700 flex items-center justify-center font-semibold text-slate-200 shrink-0">TO</div>
            {!isCollapsed && <div>Tobiloba<br/>Main project</div>}
          </div>
          {!isCollapsed && (
            <div className="flex items-center gap-2 px-1 text-[11px] text-[var(--mu)]">
              <a href="/privacy" className="hover:text-white transition-colors">Privacy</a>
              <span>·</span>
              <a href="/terms" className="hover:text-white transition-colors">Terms</a>
            </div>
          )}
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex flex-col min-w-0 min-h-screen relative">
        {/* Top bar - Sticky with blur */}
        <header className="sticky top-0 flex items-center justify-between gap-3 p-[12px_24px] border-b border-[var(--ln)] bg-[rgba(11,14,23,0.9)] backdrop-blur-md z-20 shrink-0">
          <input type="text" placeholder="Search videos, scripts, jobs" className="flex-1 max-w-[340px] px-3 py-2 rounded-lg bg-[var(--gl)] border border-[var(--ln)] text-[var(--mu)] text-[13px] outline-none focus:border-[var(--ac)] transition-colors" />
          
          <div className="flex items-center gap-3 text-xs text-[var(--mu)]">
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-[var(--ln)] bg-[var(--gl)] cursor-pointer hover:border-[var(--ac)] text-[var(--tx)]">
              <div className={`w-2 h-2 rounded-full ${isOnline ? 'bg-[var(--ok)] shadow-[0_0_8px_var(--ok)]' : 'bg-[var(--wa)] shadow-[0_0_8px_var(--wa)]'}`} />
              {isOnline ? 'Online' : 'Offline'}
            </div>
            
            <div className="flex items-center gap-2">
              <span>Paid spend <b className="text-[var(--tx)] font-medium">${spend != null ? spend.toFixed(2) : '0.00'}</b> of $50 cap</span>
              <div className="h-[5px] w-[90px] rounded-sm bg-[var(--gl2)] overflow-hidden mt-[1px]">
                <div className="h-full w-[37%] bg-blue-500" />
              </div>
            </div>
            <div className="w-[28px] h-[28px] rounded-md bg-slate-800 border border-slate-700 flex items-center justify-center font-semibold text-slate-200 shrink-0 ml-1">TO</div>
          </div>
        </header>

        {/* Offline Banner */}
        {!isOnline && (
          <div className="p-[9px_24px] bg-[rgba(245,184,74,0.1)] border-b border-[rgba(245,184,74,0.35)] text-[var(--wa)] text-[13px] shrink-0">
            You're offline. Premium engines are paused. New jobs use local engines, and publishing waits until you're back online.
          </div>
        )}

        {/* Routes: naturally scrollable */}
        <main className="flex-1 p-[22px_24px] relative bg-transparent">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/create" element={<Create />} />
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
