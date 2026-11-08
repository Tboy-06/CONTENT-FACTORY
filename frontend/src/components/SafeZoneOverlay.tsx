import React from 'react';
import { Search, Heart, MessageCircle, Bookmark, Share2, Disc3 } from 'lucide-react';

interface SafeZoneOverlayProps {
  visible: boolean;
  channelName?: string;
  caption?: string;
}

export default function SafeZoneOverlay({
  visible,
  channelName = 'contentfactory',
  caption = 'Stop making these common mistakes #viral #fyp #shorts'
}: SafeZoneOverlayProps) {
  if (!visible) return null;

  return (
    <div className="absolute inset-0 pointer-events-none z-30 flex flex-col justify-between p-3 select-none overflow-hidden font-sans">
      
      {/* Top Bar (Search + Tabs) */}
      <div className="pt-2 px-1 flex items-center justify-between text-white/80 drop-shadow-[0_1px_2px_rgba(0,0,0,0.8)]">
        <div className="text-xs font-semibold tracking-wider text-white/70">LIVE</div>
        <div className="flex items-center gap-3 text-xs font-medium">
          <span className="text-white/60">Following</span>
          <span className="text-white font-bold border-b-2 border-white pb-0.5">For You</span>
        </div>
        <Search size={16} className="text-white/80" />
      </div>

      {/* Safe Zone Boundary Box (Dashed Cyan Guide) */}
      <div className="absolute inset-x-[8%] top-[14%] bottom-[20%] border-2 border-dashed border-cyan-400/50 rounded-xl pointer-events-none flex flex-col justify-between p-2">
        <div className="flex justify-between items-center text-[10px] font-mono font-bold text-cyan-300 bg-cyan-950/80 px-2 py-0.5 rounded border border-cyan-400/40 w-fit">
          PLATFORM SAFE ZONE
        </div>
        <div className="text-right text-[9px] font-mono text-cyan-300/80 bg-cyan-950/80 px-2 py-0.5 rounded border border-cyan-400/40 w-fit self-end">
          KEEP CRITICAL TEXT INSIDE
        </div>
      </div>

      {/* Main Body with Right Action Sidebar and Bottom Caption */}
      <div className="flex items-end justify-between w-full pb-2">
        
        {/* Left / Bottom: Creator Handle & Caption */}
        <div className="flex-1 pr-14 text-left drop-shadow-[0_1px_3px_rgba(0,0,0,0.9)]">
          <div className="font-semibold text-white text-xs flex items-center gap-1.5 mb-1">
            @{channelName}
            <span className="text-[10px] bg-red-600 text-white font-bold px-1.5 py-0.2 rounded-full">Follow</span>
          </div>
          <p className="text-[11px] text-white/90 line-clamp-2 leading-snug mb-1.5 font-normal">
            {caption}
          </p>
          <div className="flex items-center gap-1.5 text-[10px] text-white/75 font-mono">
            <span className="text-xs">♫</span>
            <span className="truncate">Original Sound - Voiceover Audio (-14 LUFS)</span>
          </div>
        </div>

        {/* Right Action Icons Column */}
        <div className="flex flex-col items-center gap-3 drop-shadow-[0_2px_4px_rgba(0,0,0,0.9)] pb-1">
          {/* Avatar with + badge */}
          <div className="relative mb-1">
            <div className="w-8 h-8 rounded-full border border-white bg-slate-800 flex items-center justify-center font-bold text-[10px] text-white">
              CF
            </div>
            <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 w-3.5 h-3.5 bg-red-500 rounded-full flex items-center justify-center text-[10px] font-bold text-white">
              +
            </div>
          </div>

          {/* Like */}
          <div className="flex flex-col items-center">
            <Heart size={20} className="fill-white/90 text-white/90" />
            <span className="text-[9px] font-medium text-white mt-0.5">248.5K</span>
          </div>

          {/* Comment */}
          <div className="flex flex-col items-center">
            <MessageCircle size={20} className="fill-white/90 text-white/90" />
            <span className="text-[9px] font-medium text-white mt-0.5">1,420</span>
          </div>

          {/* Bookmark */}
          <div className="flex flex-col items-center">
            <Bookmark size={20} className="fill-white/90 text-white/90" />
            <span className="text-[9px] font-medium text-white mt-0.5">38.2K</span>
          </div>

          {/* Share */}
          <div className="flex flex-col items-center">
            <Share2 size={20} className="fill-white/90 text-white/90" />
            <span className="text-[9px] font-medium text-white mt-0.5">14.1K</span>
          </div>

          {/* Music Disc */}
          <div className="w-6 h-6 rounded-full bg-slate-900 border border-white/60 flex items-center justify-center text-white mt-1 animate-spin" style={{ animationDuration: '4s' }}>
            <Disc3 size={14} />
          </div>
        </div>

      </div>

    </div>
  );
}
