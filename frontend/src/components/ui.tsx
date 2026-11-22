import React from 'react';

export const Card = ({ children, className = '', ...props }: any) => (
  <div className={`glass-panel p-5 ${className}`} {...props}>{children}</div>
);

export const Button = ({ children, variant = 'primary', className = '', ...props }: any) => {
  const base =
    'rounded-xl font-semibold px-3.5 py-2 text-xs transition-all duration-150 border disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer inline-flex items-center justify-center gap-1.5';
  const variants: Record<string, string> = {
    primary: 'bg-blue-600 hover:bg-blue-500 text-white border-blue-500 shadow-sm shadow-blue-600/20',
    secondary:
      'bg-[var(--gl2)] hover:brightness-105 text-[var(--tx)] border-[var(--input-border)] shadow-2xs',
    danger: 'bg-red-600 hover:bg-red-500 text-white border-red-500 shadow-sm shadow-red-600/20',
    ghost:
      'bg-transparent text-[var(--mu)] border-transparent hover:bg-[var(--gl2)] hover:text-[var(--tx)] hover:border-[var(--ln-subtle)]'
  };
  const chosen = variants[variant] || variants.primary;
  return (
    <button className={`${base} ${chosen} ${className}`} {...props}>
      {children}
    </button>
  );
};

export const Badge = ({ children, variant = 'info', className = '' }: any) => {
  const variants: Record<string, string> = {
    info: 'bg-blue-500/15 text-blue-600 dark:text-blue-400 border border-blue-500/30',
    success: 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 border border-emerald-500/30',
    warning: 'bg-amber-500/15 text-amber-700 dark:text-amber-400 border border-amber-500/30',
    danger: 'bg-red-500/15 text-red-700 dark:text-red-400 border border-red-500/30',
    neutral: 'bg-[var(--gl2)] text-[var(--mu)] border border-[var(--ln-subtle)]'
  };
  const chosen = variants[variant] || variants.info;
  return (
    <span className={`text-[11px] font-bold px-2.5 py-0.5 rounded-lg inline-flex items-center gap-1 ${chosen} ${className}`}>
      {children}
    </span>
  );
};

export const Tabs = ({ tabs, activeTab, onChange }: any) => (
  <div className="flex items-center gap-2 mb-5 flex-wrap">
    {tabs.map((t: string) => {
      const isActive = activeTab === t;
      return (
        <button
          key={t}
          onClick={() => onChange(t)}
          className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all border cursor-pointer ${
            isActive
              ? 'bg-blue-600 text-white border-blue-500 shadow-md shadow-blue-600/25'
              : 'bg-[var(--gl)] text-[var(--mu)] border-[var(--ln)] hover:bg-[var(--gl2)] hover:text-[var(--tx)]'
          }`}
        >
          {t}
        </button>
      );
    })}
  </div>
);

export const Progress = ({ value }: { value: number }) => (
  <div className="h-1.5 bg-[var(--ln-subtle)] rounded-md overflow-hidden mt-1.5">
    <div className="h-full bg-blue-600 transition-all duration-300" style={{ width: `${value}%` }} />
  </div>
);

export const EmptyState = ({ title, description }: any) => (
  <div className="p-8 text-center glass-panel">
    <h3 className="text-[var(--tx)] font-bold text-sm mb-1.5">{title}</h3>
    <p className="text-[var(--mu)] text-xs">{description}</p>
  </div>
);

export const Modal = ({ isOpen, onClose, title, children }: any) => {
  if (!isOpen) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-md">
      <div className="glass-panel w-full max-w-lg shadow-2xl overflow-hidden">
        <div className="flex justify-between items-center p-4 border-b border-[var(--ln-subtle)]">
          <h2 className="font-bold text-base text-[var(--tx)]">{title}</h2>
          <button onClick={onClose} className="text-[var(--mu)] hover:text-[var(--tx)] text-xl leading-none cursor-pointer">
            &times;
          </button>
        </div>
        <div className="p-4">{children}</div>
      </div>
    </div>
  );
};
