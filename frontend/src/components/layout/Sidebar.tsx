'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
  LayoutDashboard, 
  Mic, 
  FolderKanban, 
  Settings, 
  Sparkles, 
  ShieldCheck,
  Cpu,
  Activity
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api';
import { SystemHealth } from '@/lib/types';

export const Sidebar: React.FC = () => {
  const pathname = usePathname();
  const [health, setHealth] = useState<SystemHealth | null>(null);

  useEffect(() => {
    api.getHealth()
      .then(setHealth)
      .catch(() => setHealth(null));
  }, []);

  const navItems = [
    { href: '/', label: 'Dashboard', icon: LayoutDashboard },
    { href: '/meetings', label: 'Meetings', icon: FolderKanban },
    { href: '/meetings/new', label: 'Record & Upload', icon: Mic },
    { href: '/settings', label: 'Settings & Health', icon: Settings },
  ];

  return (
    <aside className="w-64 border-r border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0E131F] flex flex-col justify-between shrink-0 select-none z-20">
      <div>
        {/* Brand Header */}
        <div className="h-16 flex items-center px-6 border-b border-slate-100 dark:border-slate-800/80 gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-teal-500 to-brand-400 flex items-center justify-center shadow-lg shadow-teal-500/20 text-white font-bold text-lg">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <div>
            <span className="font-bold text-slate-900 dark:text-white tracking-tight text-base block leading-none">
              MIS Local
            </span>
            <span className="text-[10px] text-teal-600 dark:text-teal-400 font-medium tracking-wide uppercase">
              Meeting Intelligence
            </span>
          </div>
        </div>

        {/* Navigation Links */}
        <div className="px-3 py-4 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = item.href === '/' ? pathname === '/' : pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all',
                  isActive
                    ? 'bg-teal-50 dark:bg-teal-950/40 text-teal-700 dark:text-teal-300 font-semibold shadow-xs'
                    : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800/60 hover:text-slate-900 dark:hover:text-slate-200'
                )}
              >
                <Icon className={cn('w-4 h-4', isActive ? 'text-teal-600 dark:text-teal-400' : 'text-slate-400')} />
                {item.label}
              </Link>
            );
          })}
        </div>
      </div>

      {/* System Engine Status Footer */}
      <div className="p-4 m-3 rounded-xl border border-slate-200/80 dark:border-slate-800/80 bg-slate-50 dark:bg-slate-900/40 space-y-3">
        <div className="flex items-center justify-between text-xs">
          <span className="font-semibold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" />
            100% Local Inference
          </span>
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
        </div>
        
        <div className="space-y-1.5 text-[11px] text-slate-500 dark:text-slate-400">
          <div className="flex justify-between items-center">
            <span className="flex items-center gap-1">
              <Cpu className="w-3 h-3 text-slate-400" /> Whisper:
            </span>
            <span className="font-mono text-slate-700 dark:text-slate-300">
              {health?.whisper?.device?.toUpperCase() || 'GPU/CPU'}
            </span>
          </div>
          <div className="flex justify-between items-center">
            <span className="flex items-center gap-1">
              <Activity className="w-3 h-3 text-slate-400" /> Ollama:
            </span>
            <span className="font-mono text-slate-700 dark:text-slate-300 truncate max-w-[100px]">
              {health?.ollama?.active_model || 'qwen3:8b'}
            </span>
          </div>
        </div>
      </div>
    </aside>
  );
};
