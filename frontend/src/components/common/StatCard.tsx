import React from 'react';
import { cn } from '../../lib/utils';

interface StatCardProps {
  label: string;
  value: React.ReactNode;
  hint?: string;
  icon: React.ElementType;
  tone?: 'blue' | 'amber' | 'emerald' | 'rose' | 'indigo' | 'slate';
  onClick?: () => void;
}

const TONES: Record<NonNullable<StatCardProps['tone']>, string> = {
  blue: 'bg-blue-500/10 text-blue-600 dark:text-blue-400',
  amber: 'bg-amber-500/10 text-amber-600 dark:text-amber-400',
  emerald: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400',
  rose: 'bg-rose-500/10 text-rose-600 dark:text-rose-400',
  indigo: 'bg-indigo-500/10 text-indigo-600 dark:text-indigo-400',
  slate: 'bg-slate-500/10 text-slate-600 dark:text-slate-400',
};

export const StatCard: React.FC<StatCardProps> = ({ label, value, hint, icon: Icon, tone = 'blue', onClick }) => (
  <div
    onClick={onClick}
    className={cn(
      'bg-card border border-border p-4 rounded-xl shadow-sm flex items-center justify-between transition-all',
      onClick && 'cursor-pointer hover:border-primary/50 hover:shadow-md'
    )}
  >
    <div>
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      <h3 className="text-2xl font-bold text-foreground mt-1">{value}</h3>
      {hint && <span className="text-[11px] text-muted-foreground mt-0.5 block">{hint}</span>}
    </div>
    <div className={cn('w-12 h-12 rounded-xl flex items-center justify-center', TONES[tone])}>
      <Icon className="w-6 h-6" />
    </div>
  </div>
);
