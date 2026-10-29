import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  HardDrive,
  CheckSquare,
  PlayCircle,
  FileCheck2,
  FileSearch,
  ShieldCheck,
  Settings,
  FileDown,
} from 'lucide-react';
import { useAuthStore } from '../../store/authStore';
import { cn } from '../../lib/utils';

interface NavItem {
  name: string;
  href: string;
  icon: React.ElementType;
  badge?: number;
  adminOnly?: boolean;
}

interface SidebarProps {
  pendingApprovalsCount?: number;
  activeJobsCount?: number;
}

export const Sidebar: React.FC<SidebarProps> = ({ pendingApprovalsCount = 0, activeJobsCount = 0 }) => {
  const { user } = useAuthStore();

  const navItems: NavItem[] = [
    { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
    { name: 'Device Inventory', href: '/devices', icon: HardDrive },
    {
      name: 'Approvals Inbox',
      href: '/approvals',
      icon: CheckSquare,
      badge: pendingApprovalsCount,
    },
    {
      name: 'Live Wipe Jobs',
      href: '/jobs',
      icon: PlayCircle,
      badge: activeJobsCount,
    },
    { name: 'Certificates', href: '/certificates', icon: FileCheck2 },
    { name: 'Audit Log & Chain', href: '/audit', icon: FileSearch },
    { name: 'Public Verification', href: '/verify', icon: ShieldCheck },
    { name: 'Admin & Policies', href: '/admin', icon: Settings, adminOnly: true },
  ];

  return (
    <aside className="w-64 border-r border-border bg-card/60 flex flex-col shrink-0 min-h-[calc(100vh-6.25rem)]">
      <div className="p-4 space-y-1">
        <div className="text-[10px] font-semibold tracking-wider text-muted-foreground uppercase px-3 py-2">
          Sanitization Platform
        </div>
        {navItems.map((item) => {
          if (item.adminOnly && user?.role !== 'ADMIN') {
            return null;
          }
          const Icon = item.icon;
          return (
            <NavLink
              key={item.href}
              to={item.href}
              className={({ isActive }) =>
                cn(
                  'flex items-center justify-between px-3 py-2.5 rounded-lg text-xs font-medium transition-all group',
                  isActive
                    ? 'bg-primary text-primary-foreground shadow-sm font-semibold'
                    : 'text-muted-foreground hover:text-foreground hover:bg-muted/80'
                )
              }
            >
              <div className="flex items-center space-x-3">
                <Icon className="h-4 w-4 shrink-0 transition-transform group-hover:scale-110" />
                <span>{item.name}</span>
              </div>
              {item.badge !== undefined && item.badge > 0 && (
                <span
                  className={cn(
                    'px-2 py-0.5 rounded-full text-[10px] font-bold font-mono',
                    item.href === '/approvals'
                      ? 'bg-amber-500 text-slate-950 animate-pulse'
                      : 'bg-primary/20 text-primary'
                  )}
                >
                  {item.badge}
                </span>
              )}
            </NavLink>
          );
        })}
      </div>

      {/* Role Context Card & Report Download in Sidebar footer */}
      <div className="mt-auto p-4 border-t border-border/60 space-y-2">
        <a
          href="/SecureWipe_Project_Report.pdf"
          download="SecureWipe_Project_Report.pdf"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center justify-between px-3 py-2 rounded-lg text-xs font-semibold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30 hover:bg-emerald-500/20 transition-all group"
          title="Download the official 15-page IEEE/NIST Project Report & SRS (PDF)"
        >
          <div className="flex items-center space-x-2.5">
            <FileDown className="h-4 w-4 shrink-0 transition-transform group-hover:scale-110" />
            <span>Project Report</span>
          </div>
          <span className="text-[10px] font-mono uppercase bg-emerald-500/20 px-1.5 py-0.5 rounded">PDF (15p)</span>
        </a>

        <div className="bg-muted/50 rounded-lg p-3 text-xs border border-border/40">
          <div className="text-[11px] font-semibold text-foreground flex items-center justify-between">
            <span>Dual-Custody Policy</span>
            <span className="text-[10px] text-emerald-600 dark:text-emerald-400 font-mono">ENFORCED</span>
          </div>
          <p className="text-[10px] text-muted-foreground mt-1 leading-relaxed">
            Four-eyes rule active: requesters cannot self-approve. High-risk actions require 2 distinct approvers.
          </p>
        </div>
      </div>
    </aside>
  );
};
