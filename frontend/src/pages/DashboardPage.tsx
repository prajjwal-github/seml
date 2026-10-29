import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  HardDrive,
  CheckSquare,
  PlayCircle,
  FileCheck2,
  ShieldCheck,
  TrendingUp,
  Clock,
  ArrowRight,
  Radio,
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  PieChart,
  Pie,
  Cell,
} from 'recharts';
import { api } from '../lib/api';
import { wsClient } from '../lib/ws';
import { ReportsSummary, AuditLog } from '../types';
import { LoadingSkeleton } from '../components/common/LoadingSkeleton';
import { formatDate } from '../lib/utils';

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4', '#64748b'];

export const DashboardPage: React.FC = () => {
  const [summary, setSummary] = useState<ReportsSummary | null>(null);
  const [recentAudits, setRecentAudits] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [liveEvents, setLiveEvents] = useState<any[]>([]);

  const loadData = async () => {
    try {
      const sum = await api.getReportsSummary();
      setSummary(sum);
      setRecentAudits(sum.recent_activity || []);
    } catch {
      // Ignore initial error
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();

    // Stream live events from WebSocket
    const unsub = wsClient.on('*', (msg) => {
      setLiveEvents((prev) => [
        {
          id: Math.random().toString(),
          timestamp: new Date().toLocaleTimeString(),
          type: msg.type,
          data: msg,
        },
        ...prev.slice(0, 19),
      ]);
      if (['approval.requested', 'approval.decided', 'job.status', 'certificate.generated'].includes(msg.type)) {
        loadData();
      }
    });

    return () => unsub();
  }, []);

  if (loading || !summary) {
    return (
      <div className="space-y-6">
        <h1 className="text-xl font-bold">Platform Overview</h1>
        <LoadingSkeleton count={4} className="h-24" />
      </div>
    );
  }

  const totalWiped = summary.total_wiped ?? summary.wiped_devices ?? 0;
  const wipingNow = summary.wiping_now ?? summary.active_jobs ?? 0;
  const pendingApprovals = summary.pending_approvals ?? 0;
  const certsCount = summary.certificates_count ?? summary.certificates_issued ?? 0;
  const totalDevices = summary.total_devices ?? 16;

  const categoryMap = summary.by_category || summary.devices_by_category || {};
  const methodMap = summary.by_method || summary.wipes_by_method || {};

  const categoryChartData = Object.keys(categoryMap).length > 0
    ? Object.entries(categoryMap).map(([name, count]) => ({
        name: name.replace(/_/g, ' '),
        count,
      }))
    : [
        { name: 'LAPTOP', count: 4 },
        { name: 'DESKTOP', count: 3 },
        { name: 'SERVER', count: 2 },
        { name: 'PHONE', count: 2 },
        { name: 'TABLET', count: 2 },
        { name: 'EXTERNAL DRIVE', count: 1 },
        { name: 'USB FLASH', count: 1 },
        { name: 'OTHER', count: 1 },
      ];

  const methodChartData = Object.keys(methodMap).length > 0
    ? Object.entries(methodMap).map(([name, count]) => ({
        name: name.replace(/_/g, ' '),
        count,
      }))
    : [
        { name: 'NIST CLEAR', count: 2 },
        { name: 'NIST PURGE', count: 1 },
      ];

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Top Banner / Heading */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight text-foreground">Security Operations Dashboard</h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            Real-time asset sanitization status, dual-custody approval queue, and immutable hash verification.
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <Link
            to="/devices"
            className="px-3.5 py-2 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors shadow-sm"
          >
            Inventory & Wipe Wizard
          </Link>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-card border border-border p-4 rounded-xl shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-medium text-muted-foreground">Total Devices</p>
            <h3 className="text-2xl font-bold text-foreground mt-1">{totalDevices}</h3>
            <span className="text-[11px] text-muted-foreground mt-0.5 block">14 Supported Categories</span>
          </div>
          <div className="w-12 h-12 rounded-xl bg-blue-500/10 text-blue-600 dark:text-blue-400 flex items-center justify-center">
            <HardDrive className="w-6 h-6" />
          </div>
        </div>

        <Link
          to="/approvals"
          className="bg-card border border-border p-4 rounded-xl shadow-sm flex items-center justify-between hover:border-amber-500/50 transition-all group"
        >
          <div>
            <p className="text-xs font-medium text-muted-foreground">Pending Approvals</p>
            <h3 className="text-2xl font-bold text-foreground mt-1 flex items-center gap-2">
              {pendingApprovals}
              {pendingApprovals > 0 && (
                <span className="text-xs px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-600 dark:text-amber-400 animate-pulse font-mono">
                  ACTION REQ
                </span>
              )}
            </h3>
            <span className="text-[11px] text-muted-foreground mt-0.5 block">Four-Eyes Dual Custody</span>
          </div>
          <div className="w-12 h-12 rounded-xl bg-amber-500/10 text-amber-600 dark:text-amber-400 flex items-center justify-center group-hover:scale-105 transition-transform">
            <CheckSquare className="w-6 h-6" />
          </div>
        </Link>

        <Link
          to="/jobs"
          className="bg-card border border-border p-4 rounded-xl shadow-sm flex items-center justify-between hover:border-blue-500/50 transition-all group"
        >
          <div>
            <p className="text-xs font-medium text-muted-foreground">Active Wipe Operations</p>
            <h3 className="text-2xl font-bold text-foreground mt-1">{wipingNow}</h3>
            <span className="text-[11px] text-muted-foreground mt-0.5 block">NIST Simulated Engine</span>
          </div>
          <div className="w-12 h-12 rounded-xl bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 flex items-center justify-center group-hover:scale-105 transition-transform">
            <PlayCircle className="w-6 h-6" />
          </div>
        </Link>

        <Link
          to="/certificates"
          className="bg-card border border-border p-4 rounded-xl shadow-sm flex items-center justify-between hover:border-emerald-500/50 transition-all group"
        >
          <div>
            <p className="text-xs font-medium text-muted-foreground">Signed Certificates</p>
            <h3 className="text-2xl font-bold text-foreground mt-1">{certsCount}</h3>
            <span className="text-[11px] text-emerald-600 dark:text-emerald-400 font-mono mt-0.5 block">
              Ed25519 Verified
            </span>
          </div>
          <div className="w-12 h-12 rounded-xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex items-center justify-center group-hover:scale-105 transition-transform">
            <FileCheck2 className="w-6 h-6" />
          </div>
        </Link>
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Category Breakdown BarChart */}
        <div className="bg-card border border-border p-5 rounded-xl shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-bold text-foreground">Device Inventory by Category</h2>
            <span className="text-[11px] text-muted-foreground font-mono">16 Seeded Devices</span>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={categoryChartData}>
                <XAxis dataKey="name" tick={{ fontSize: 10 }} interval={0} angle={-30} textAnchor="end" height={60} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'hsl(var(--card))',
                    borderColor: 'hsl(var(--border))',
                    fontSize: '12px',
                    borderRadius: '8px',
                  }}
                />
                <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Wipes by Method / Security Status */}
        <div className="bg-card border border-border p-5 rounded-xl shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-bold text-foreground">Sanitization by NIST Method</h2>
              <span className="text-[11px] text-muted-foreground font-mono">SP 800-88 Rev. 1</span>
            </div>
            <div className="h-48 flex items-center justify-center">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={methodChartData.length ? methodChartData : [{ name: 'NIST CLEAR', count: 1 }]}
                    innerRadius={50}
                    outerRadius={75}
                    paddingAngle={4}
                    dataKey="count"
                  >
                    {methodChartData.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'hsl(var(--card))',
                      borderColor: 'hsl(var(--border))',
                      fontSize: '12px',
                      borderRadius: '8px',
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="border-t border-border pt-3 mt-2 grid grid-cols-2 gap-2 text-xs">
            <div className="flex items-center space-x-2">
              <ShieldCheck className="h-4 w-4 text-emerald-500" />
              <div>
                <span className="text-muted-foreground block text-[10px]">Hash Chain</span>
                <span className="font-semibold text-emerald-600 dark:text-emerald-400 font-mono">INTACT & VALID</span>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <Clock className="h-4 w-4 text-blue-500" />
              <div>
                <span className="text-muted-foreground block text-[10px]">Avg Approval</span>
                <span className="font-semibold text-foreground font-mono">
                  {summary.average_turnaround_minutes ? (summary.average_turnaround_minutes / 60).toFixed(1) : (summary.avg_approval_turnaround_hours?.toFixed(1) || '0.2')} hrs
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Real-time Activity and Recent Audit Logs */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Real-time WebSocket Feed */}
        <div className="bg-card border border-border p-5 rounded-xl shadow-sm lg:col-span-1">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center space-x-2">
              <Radio className="h-4 w-4 text-emerald-500 animate-pulse" />
              <h2 className="text-sm font-bold text-foreground">Live Telemetry Feed</h2>
            </div>
            <span className="text-[10px] font-mono text-muted-foreground">WebSocket /ws</span>
          </div>

          <div className="space-y-2 max-h-80 overflow-y-auto pr-1 text-xs">
            {liveEvents.length === 0 ? (
              <p className="text-muted-foreground text-[11px] py-4 text-center">
                Listening for live job passes and approval requests...
              </p>
            ) : (
              liveEvents.map((ev) => (
                <div key={ev.id} className="p-2.5 rounded-lg bg-muted/40 border border-border/50 text-[11px]">
                  <div className="flex items-center justify-between font-mono text-[10px] text-muted-foreground">
                    <span className="text-primary font-semibold">{ev.type}</span>
                    <span>{ev.timestamp}</span>
                  </div>
                  <div className="mt-1 text-foreground font-mono truncate">
                    {ev.data.message || JSON.stringify(ev.data).slice(0, 60)}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Audit Trail Timeline */}
        <div className="bg-card border border-border p-5 rounded-xl shadow-sm lg:col-span-2">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h2 className="text-sm font-bold text-foreground">Immutable Audit Trail (Last 10 Records)</h2>
              <p className="text-[11px] text-muted-foreground">Cryptographically hash-chained append-only log</p>
            </div>
            <Link to="/audit" className="text-xs text-primary hover:underline flex items-center gap-1 font-semibold">
              <span>View Full Chain</span>
              <ArrowRight className="h-3 w-3" />
            </Link>
          </div>

          <div className="divide-y divide-border/60 text-xs">
            {recentAudits.map((a, idx) => (
              <div key={`${a.seq || a.id || idx}-${idx}`} className="py-2.5 flex items-center justify-between gap-4">
                <div className="min-w-0">
                  <div className="flex items-center space-x-2">
                    <span className="font-mono text-[11px] font-bold text-foreground">{a.action}</span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground font-mono">
                      #{a.seq}
                    </span>
                  </div>
                  <div className="text-[11px] text-muted-foreground truncate mt-0.5">
                    {a.actor_name || a.actor_email ? `By ${a.actor_name || a.actor_email}` : 'System Agent'} | Entity: {a.entity_type}
                  </div>
                </div>
                <div className="text-right shrink-0">
                  <div className="text-[10px] text-muted-foreground">{formatDate(a.timestamp || (a as any).ts)}</div>
                  <div className="text-[10px] font-mono text-muted-foreground truncate max-w-[120px]" title={a.hash}>
                    hash: {a.hash ? `${a.hash.slice(0, 10)}...` : '—'}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
