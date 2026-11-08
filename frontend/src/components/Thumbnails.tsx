import React, { useId } from 'react';

export const Thumbnail = ({ type, className = '' }: { type: string, className?: string }) => {
  const i = useId().replace(/:/g, '');
  
  const svgs: Record<string, React.ReactNode> = {
    mountain: (
      <>
        <defs><linearGradient id={i} x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#1e3a8a"/><stop offset="1" stopColor="#f59e5b"/></linearGradient></defs>
        <rect width="160" height="90" fill={`url(#${i})`}/>
        <circle cx="118" cy="30" r="9" fill="#ffe3a8"/>
        <path d="M0 90V58l30-26 26 24 22-18 34 30 48-20v42z" fill="#27324f"/>
        <path d="M0 90V70l40-16 40 14 40-12 40 14v20z" fill="#141b2e"/>
      </>
    ),
    night: (
      <>
        <defs><linearGradient id={i} x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#0a1030"/><stop offset="1" stopColor="#2b3a8f"/></linearGradient></defs>
        <rect width="160" height="90" fill={`url(#${i})`}/>
        <circle cx="116" cy="26" r="10" fill="#e8ecff"/>
        <circle cx="30" cy="18" r="1.2" fill="#fff"/>
        <circle cx="60" cy="30" r="1" fill="#fff"/>
        <circle cx="84" cy="14" r="1.2" fill="#fff"/>
        <path d="M0 90V66q40-18 80-4t80-6v34z" fill="#0b1226"/>
      </>
    ),
    ocean: (
      <>
        <defs><linearGradient id={i} x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#7cc4ff"/><stop offset="1" stopColor="#0b3b6b"/></linearGradient></defs>
        <rect width="160" height="90" fill={`url(#${i})`}/>
        <path d="M0 52q20-8 40 0t40 0 40 0 40 0v38H0z" fill="#0f5a96" fillOpacity=".8"/>
        <path d="M0 68q20-8 40 0t40 0 40 0 40 0v22H0z" fill="#0a3d6c"/>
      </>
    ),
    forest: (
      <>
        <defs><linearGradient id={i} x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#d4a05a"/><stop offset="1" stopColor="#1c3a2a"/></linearGradient></defs>
        <rect width="160" height="90" fill={`url(#${i})`}/>
        <path d="M10 90l14-46 14 46zM40 90l16-58 16 58zM76 90l12-40 12 40zM104 90l16-62 16 62zM136 90l10-34 12 34z" fill="#0f2418"/>
      </>
    ),
    city: (
      <>
        <defs><linearGradient id={i} x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#2a1b5e"/><stop offset="1" stopColor="#ff8a5b"/></linearGradient></defs>
        <rect width="160" height="90" fill={`url(#${i})`}/>
        <path d="M0 90V52h14V36h16v22h12V44h18v18h14V30h18v32h14V48h16v42z" fill="#151228"/>
      </>
    ),
    warm: (
      <>
        <defs><linearGradient id={i} x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#f5b84a"/><stop offset="1" stopColor="#b8431f"/></linearGradient></defs>
        <rect width="160" height="90" fill={`url(#${i})`}/>
        <circle cx="80" cy="48" r="26" fill="#fff4dc" fillOpacity=".85"/>
        <circle cx="80" cy="48" r="16" fill="#d9531e"/>
      </>
    )
  };

  return (
    <div className={`relative overflow-hidden rounded-t-[14px] bg-[#111827] ${className}`}>
      <svg viewBox="0 0 160 90" preserveAspectRatio="xMidYMid slice" className="block w-full h-full">
        {svgs[type] || svgs.mountain}
      </svg>
    </div>
  );
};
