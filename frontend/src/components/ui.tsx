import React from 'react';

export const Card = ({ children, className = '', ...props }: any) => (
  <div className={`glass-panel p-4 ${className}`} {...props}>{children}</div>
);

export const Button = ({ children, variant = 'primary', className = '', ...props }: any) => {
  const base = "rounded-lg font-medium px-4 py-2 transition-all duration-150 border disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer";
  const variants: Record<string, string> = {
    primary: "bg-blue-600 hover:bg-blue-500 text-white border-blue-500/50 shadow-sm",
    secondary: "bg-slate-800 hover:bg-slate-700 text-slate-200 border-slate-700 hover:text-white",
    danger: "bg-red-600/80 hover:bg-red-500 text-white border-red-500/40",
    ghost: "bg-[var(--gl)] text-[var(--tx)] border-[var(--ln)] hover:bg-[var(--gl2)]"
  };
  const chosen = variants[variant] || variants.primary;
  return <button className={`${base} ${chosen} ${className}`} {...props}>{children}</button>;
};

export const Badge = ({ children, variant = 'info', className = '' }: any) => {
  const variants: Record<string, string> = {
    info: "bg-blue-500/15 text-blue-300 border border-blue-500/30",
    success: "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30",
    warning: "bg-amber-500/15 text-amber-300 border border-amber-500/30",
    danger: "bg-red-500/15 text-red-400 border border-red-500/30",
    neutral: "bg-slate-800 text-slate-300 border border-slate-700"
  };
  const chosen = variants[variant] || variants.info;
  return <span className={`text-[11px] font-medium px-2 py-0.5 rounded-md whitespace-nowrap ${chosen} ${className}`}>{children}</span>;
};

export const Tabs = ({ tabs, activeTab, onChange }: any) => (
  <div className="flex gap-1 mb-4">
    {tabs.map((t: string) => (
      <button 
        key={t}
        onClick={() => onChange(t)}
        className={`px-3 py-1.5 rounded-lg text-sm transition-colors border ${activeTab === t ? 'bg-[var(--gl2)] text-white border-[var(--ln)]' : 'text-[var(--mu)] border-transparent hover:text-white'}`}
      >
        {t}
      </button>
    ))}
  </div>
);

export const Progress = ({ value }: { value: number }) => (
  <div className="h-1 bg-[var(--gl2)] rounded-md overflow-hidden mt-1.5">
    <div className="h-full bg-blue-500" style={{ width: `${value}%` }} />
  </div>
);

export const EmptyState = ({ title, description }: any) => (
  <div className="p-8 text-center glass-panel">
    <h3 className="text-[var(--tx)] font-medium mb-2">{title}</h3>
    <p className="text-[var(--mu)] text-sm">{description}</p>
  </div>
);

export const Modal = ({ isOpen, onClose, title, children }: any) => {
  if (!isOpen) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <div className="glass-panel w-full max-w-lg shadow-2xl">
        <div className="flex justify-between items-center p-4 border-b border-[var(--ln)]">
          <h2 className="font-semibold text-lg">{title}</h2>
          <button onClick={onClose} className="text-[var(--mu)] hover:text-white text-xl leading-none">&times;</button>
        </div>
        <div className="p-4">{children}</div>
      </div>
    </div>
  );
};
