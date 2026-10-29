import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  HardDrive,
  Clock,
  Loader2,
  FileCheck2,
  Plus,
  Search,
  Trash2,
  Users,
  ArrowRight,
} from 'lucide-react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip } from 'recharts';
import { api } from '../../lib/api';
import { AuditLog, Device, User } from '../../types';
import { useLiveRefresh } from '../../lib/useLiveRefresh';
import { ROLES, certStatusLabel } from '../../lib/roles';
import { formatDate } from '../../lib/utils';
import { StatCard } from '../../components/common/StatCard';
import { StatusBadge } from '../../components/common/StatusBadge';
import { CategoryIcon } from '../../components/common/CategoryIcon';
import { LoadingSkeleton } from '../../components/common/LoadingSkeleton';
import { AddDeviceModal } from '../AddDeviceModal';

export const AdminDashboard: React.FC = () => {
  const navigate = useNavigate();
  const [devices, setDevices] = useState<Device[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [activity, setActivity] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [addOpen, setAddOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [devs, usrs, summary] = await Promise.all([api.getDevices(), api.getUsers(), api.getReportsSummary()]);
      setDevices(devs);
      setUsers(usrs);
      setActivity(summary.recent_activity || []);
    } catch (err: any) {
      setError(err.message || 'Could not load the dashboard');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);
  useLiveRefresh(load);

  const counts = useMemo(
    () => ({
      pending: devices.filter((d) => d.wipe_status === 'PENDING_APPROVAL').length,
      wiping: devices.filter((d) => ['APPROVED', 'QUEUED', 'RUNNING', 'VERIFYING'].includes(d.wipe_status || '')).length,
      certified: devices.filter((d) => d.wipe_status === 'COMPLETED').length,
    }),
    [devices]
  );

  const byCategory = useMemo(() => {
    const map: Record<string, number> = {};
    devices.forEach((d) => (map[d.category] = (map[d.category] || 0) + 1));
    return Object.entries(map)
      .map(([name, count]) => ({ name: name.replace(/_/g, ' '), count }))
      .sort((a, b) => b.count - a.count);
  }, [devices]);

  const filtered = devices.filter((d) => {
    const q = search.trim().toLowerCase();
    return !q || `${d.manufacturer} ${d.model} ${d.serial_number} ${d.category}`.toLowerCase().includes(q);
  });

  const removeDevice = async (d: Device) => {
    if (!window.confirm(`Remove ${d.manufacturer} ${d.model} (${d.serial_number}) from the registry?`)) return;
    setError(null);
    try {
      await api.deleteDevice(d.id);
      load();
    } catch (err: any) {
      setError(err.message || 'Could not remove the device');
    }
  };

  if (loading) {
    return (
      <div className="space-y-6 max-w-7xl mx-auto">
        <h1 className="text-2xl font-extrabold">Admin Dashboard</h1>
        <LoadingSkeleton count={4} className="h-24" />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-3">
        <div>
          <span className="text-[10px] font-bold uppercase tracking-wider text-primary">Admin</span>
          <h1 className="text-2xl font-extrabold tracking-tight text-foreground">Office device registry</h1>
          <p className="text-xs text-muted-foreground mt-0.5 max-w-2xl">
            Register every office device here. Operators can only request a wipe certificate for devices in this registry.
          </p>
        </div>
        <button
          onClick={() => setAddOpen(true)}
          className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 shadow-sm"
        >
          <Plus className="h-4 w-4" /> Add device
        </button>
      </div>

      {error && (
        <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-700 dark:text-rose-400 text-xs flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="font-semibold">Dismiss</button>
        </div>
      )}

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Registered devices" value={devices.length} icon={HardDrive} tone="blue" hint="In the office registry" />
        <StatCard label="Awaiting approval" value={counts.pending} icon={Clock} tone="amber" hint="Requests with the Approver" />
        <StatCard label="Being wiped" value={counts.wiping} icon={Loader2} tone="indigo" hint="Approved, in progress" />
        <StatCard label="Certified clean" value={counts.certified} icon={FileCheck2} tone="emerald" hint="Certificate issued" onClick={() => navigate('/certificates')} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="bg-card border border-border rounded-xl p-5 shadow-sm lg:col-span-2">
          <h2 className="text-sm font-bold text-foreground mb-3">Devices by type</h2>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={byCategory}>
                <XAxis dataKey="name" tick={{ fontSize: 10 }} interval={0} angle={-25} textAnchor="end" height={55} />
                <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
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

        <div className="bg-card border border-border rounded-xl p-5 shadow-sm space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-foreground">Team</h2>
            <button onClick={() => navigate('/admin')} className="text-[11px] text-primary font-semibold flex items-center gap-1">
              Manage users <ArrowRight className="h-3 w-3" />
            </button>
          </div>
          {ROLES.map((r) => {
            const members = users.filter((u) => u.role === r.role && u.is_active);
            return (
              <div key={r.role} className="p-3 rounded-lg bg-muted/40 border border-border/50">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-foreground">{r.title}</span>
                  <span className="text-[11px] font-mono text-muted-foreground flex items-center gap-1">
                    <Users className="h-3 w-3" />
                    {members.length}
                  </span>
                </div>
                <p className="text-[10px] text-muted-foreground mt-0.5">{r.description}</p>
              </div>
            );
          })}
        </div>
      </div>

      <section className="bg-card border border-border rounded-xl shadow-sm">
        <div className="p-4 border-b border-border flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-bold text-foreground">All devices</h2>
            <p className="text-[11px] text-muted-foreground">Certificate status updates live as requests move through approval.</p>
          </div>
          <div className="relative w-full sm:w-72">
            <Search className="h-4 w-4 absolute left-3 top-2.5 text-muted-foreground" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search model, serial, type…"
              className="w-full pl-9 pr-3 py-2 text-xs bg-background border border-border rounded-lg focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead className="bg-muted/40 text-muted-foreground text-[11px] uppercase">
              <tr>
                <th className="text-left px-4 py-2.5 font-semibold">Device</th>
                <th className="text-left px-4 py-2.5 font-semibold">Serial</th>
                <th className="text-left px-4 py-2.5 font-semibold">Type</th>
                <th className="text-left px-4 py-2.5 font-semibold">Storage</th>
                <th className="text-left px-4 py-2.5 font-semibold">Certificate status</th>
                <th className="text-left px-4 py-2.5 font-semibold">Added</th>
                <th className="text-right px-4 py-2.5 font-semibold"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {filtered.map((d) => (
                <tr key={d.id} className="hover:bg-muted/30 cursor-pointer" onClick={() => navigate(`/devices/${d.id}`)}>
                  <td className="px-4 py-2.5">
                    <div className="flex items-center gap-2">
                      <CategoryIcon category={d.category} className="h-4 w-4 text-muted-foreground" />
                      <span className="font-medium text-foreground">{d.manufacturer} {d.model}</span>
                    </div>
                  </td>
                  <td className="px-4 py-2.5 font-mono text-muted-foreground">{d.serial_number}</td>
                  <td className="px-4 py-2.5 text-muted-foreground">{d.category.replace(/_/g, ' ')}</td>
                  <td className="px-4 py-2.5 text-muted-foreground">{d.volumes_count ?? 0} volume(s)</td>
                  <td className="px-4 py-2.5">
                    <StatusBadge status={d.wipe_status || 'NONE'} label={certStatusLabel(d.wipe_status)} />
                  </td>
                  <td className="px-4 py-2.5 text-muted-foreground">{formatDate(d.created_at)}</td>
                  <td className="px-4 py-2.5 text-right">
                    {(!d.wipe_status || d.wipe_status === 'NONE') && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          removeDevice(d);
                        }}
                        title="Remove device"
                        className="p-1.5 rounded-md text-muted-foreground hover:text-rose-600 hover:bg-rose-500/10"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-muted-foreground">
                    No devices found. Use “Add device” to register one.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="bg-card border border-border rounded-xl shadow-sm p-5">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-sm font-bold text-foreground">Recent activity</h2>
          <button onClick={() => navigate('/audit')} className="text-[11px] text-primary font-semibold flex items-center gap-1">
            Full audit log <ArrowRight className="h-3 w-3" />
          </button>
        </div>
        <div className="divide-y divide-border/60 text-xs">
          {activity.map((a, i) => (
            <div key={`${a.seq}-${i}`} className="py-2 flex items-center justify-between gap-4">
              <div className="min-w-0">
                <span className="font-mono text-[11px] font-bold text-foreground">{a.action.replace(/_/g, ' ')}</span>
                <span className="text-[11px] text-muted-foreground ml-2">{a.actor_name ? `by ${a.actor_name}` : 'system'}</span>
              </div>
              <span className="text-[10px] text-muted-foreground shrink-0">{formatDate(a.timestamp || (a as any).ts)}</span>
            </div>
          ))}
          {activity.length === 0 && <p className="py-4 text-center text-muted-foreground">No activity yet.</p>}
        </div>
      </section>

      <AddDeviceModal
        isOpen={addOpen}
        onClose={() => setAddOpen(false)}
        onCreated={() => {
          setAddOpen(false);
          load();
        }}
      />
    </div>
  );
};
