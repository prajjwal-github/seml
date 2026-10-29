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
import { roleInfo } from '../../lib/roles';
import { UserRole } from '../../types';
import { cn } from '../../lib/utils';

interface NavItem {
  name: string;
  href: string;
  icon: React.ElementType;
  badge?: number;
}

interface SidebarProps {
  pendingApprovalsCount?: number;
  activeJobsCount?: number;
}

export const Sidebar: React.FC<SidebarProps> = ({ pendingApprovalsCount = 0, activeJobsCount = 0 }) => {
  const { user } = useAuthStore();
  const info = roleInfo(user?.role);

  const NAV: Record<UserRole, NavItem[]> = {
    ADMIN: [
      { name: 'Admin Dashboard', href: '/dashboard', icon: LayoutDashboard },
      { name: 'Device Registry', href: '/devices', icon: HardDrive },
      { name: 'Wipe Progress', href: '/jobs', icon: PlayCircle, badge: activeJobsCount },
      { name: 'Certificates', href: '/certificates', icon: FileCheck2 },
      { name: 'Audit Log', href: '/audit', icon: FileSearch },
      { name: 'Users & Roles', href: '/admin', icon: Settings },
    ],
    OPERATOR: [
      { name: 'Operator Dashboard', href: '/dashboard', icon: LayoutDashboard },
      { name: 'Office Devices', href: '/devices', icon: HardDrive },
      { name: 'My Certificates', href: '/certificates', icon: FileCheck2 },
      { name: 'Verify a Certificate', href: '/verify', icon: ShieldCheck },
    ],
    APPROVER: [
      { name: 'Approver Dashboard', href: '/dashboard', icon: LayoutDashboard },
      { name: 'Approvals Inbox', href: '/approvals', icon: CheckSquare, badge: pendingApprovalsCount },
      { name: 'Wipe Progress', href: '/jobs', icon: PlayCircle, badge: activeJobsCount },
      { name: 'Certificates', href: '/certificates', icon: FileCheck2 },
      { name: 'Audit Log', href: '/audit', icon: FileSearch },
    ],
  };
  const navItems = user ? NAV[user.role] ?? [] : [];

  return (
    <aside className="w-64 border-r border-border bg-card/60 flex flex-col shrink-0 min-h-[calc(100vh-6.25rem)]">
      <div className="p-4 space-y-1">
        <div className="text-[10px] font-semibold tracking-wider text-muted-foreground uppercase px-3 py-2">
          {info ? `${info.title} · ${info.subtitle}` : 'Sanitization Platform'}
        </div>
        {navItems.map((item) => {
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

        {info && (
          <div className="bg-muted/50 rounded-lg p-3 text-xs border border-border/40">
            <div className="text-[11px] font-semibold text-foreground">Your role: {info.title}</div>
            <p className="text-[10px] text-muted-foreground mt-1 leading-relaxed">{info.description}</p>
          </div>
        )}
      </div>
    </aside>
  );
};
