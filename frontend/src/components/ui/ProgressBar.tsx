import React from 'react';
import { cn } from '@/lib/utils';

interface ProgressBarProps {
  progress: number;
  label?: string;
  sublabel?: string;
  className?: string;
  color?: 'brand' | 'emerald' | 'indigo' | 'amber';
}

export const ProgressBar: React.FC<ProgressBarProps> = ({
  progress,
  label,
  sublabel,
  className,
  color = 'brand'
}) => {
  const clampedProgress = Math.min(100, Math.max(0, progress));

  const colorStyles = {
    brand: 'bg-gradient-to-r from-teal-500 to-brand-500',
    emerald: 'bg-gradient-to-r from-emerald-500 to-teal-500',
    indigo: 'bg-gradient-to-r from-indigo-500 to-purple-500',
    amber: 'bg-gradient-to-r from-amber-500 to-orange-500',
  };

  return (
    <div className={cn('w-full space-y-1.5', className)}>
      {(label || sublabel) && (
        <div className="flex justify-between text-xs font-medium">
          {label && <span className="text-slate-700 dark:text-slate-300">{label}</span>}
          {sublabel && <span className="text-slate-500 dark:text-slate-400">{sublabel}</span>}
        </div>
      )}
      <div className="w-full h-2.5 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden p-0.5 border border-slate-200/50 dark:border-slate-700/50">
        <div
          className={cn('h-full rounded-full transition-all duration-500 ease-out', colorStyles[color])}
          style={{ width: `${clampedProgress}%` }}
        />
      </div>
    </div>
  );
};
