import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Clock,
  Loader2,
  FileCheck2,
  XCircle,
  Search,
  FilePlus2,
  CheckCircle2,
  Info,
  Undo2,
} from 'lucide-react';
import { api } from '../../lib/api';
import { Device, WipeRequest } from '../../types';
import { useAuthStore } from '../../store/authStore';
import { useLiveRefresh } from '../../lib/useLiveRefresh';
import { ACTIVE_STATUSES, certStatusLabel, formatMethod } from '../../lib/roles';
import { formatDate } from '../../lib/utils';
import { StatCard } from '../../components/common/StatCard';
import { StatusBadge } from '../../components/common/StatusBadge';
import { CategoryIcon } from '../../components/common/CategoryIcon';
import { LoadingSkeleton } from '../../components/common/LoadingSkeleton';
import { RequestProgress } from '../../components/common/RequestProgress';
import { DownloadCertificateButton } from '../../components/common/DownloadCertificateButton';
import { WipeRequestWizardModal } from '../WipeRequestWizardModal';

export const OperatorDashboard: React.FC = () => {
  const { user } = useAuthStore();
  const [devices, setDevices] = useState<Device[]>([]);
  const [requests, setRequests] = useState<WipeRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [wizardDevice, setWizardDevice] = useState<Device | null>(null);
  const [openingId, setOpeningId] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [devs, reqs] = await Promise.all([api.getDevices(), api.getWipeRequests()]);
      setDevices(devs);
      setRequests(reqs);
    } catch (err: any) {
      setError(err.message || 'Could not load your dashboard');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const hasActive = requests.some((r) => ACTIVE_STATUSES.includes(r.status));
  useLiveRefresh(load, hasActive);

  const counts = useMemo(
    () => ({
      pending: requests.filter((r) => r.status === 'PENDING_APPROVAL').length,
      inProgress: requests.filter((r) => ['APPROVED', 'QUEUED', 'RUNNING', 'VERIFYING'].includes(r.status)).length,
      ready: requests.filter((r) => r.certificate_id).length,
      rejected: requests.filter((r) => r.status === 'REJECTED').length,
    }),
    [requests]
  );

  const filteredDevices = devices.filter((d) => {
    const q = search.trim().toLowerCase();
    return (
      !q ||
      `${d.manufacturer} ${d.model} ${d.serial_number} ${d.category}`.toLowerCase().includes(q)
    );
  });

  const openWizard = async (deviceId: string) => {
    setOpeningId(deviceId);
    setError(null);
    try {
      setWizardDevice(await api.getDevice(deviceId));
    } catch (err: any) {
      setError(err.message || 'Could not open the device');
    } finally {
      setOpeningId(null);
    }
  };

  const withdraw = async (req: WipeRequest) => {
    setError(null);
    try {
      await api.cancelWipeRequest(req.id);
      setNotice(`Request for ${req.device_name} was withdrawn.`);
      load();
    } catch (err: any) {
      setError(err.message || 'Could not withdraw the request');
    }
  };

  if (loading) {
    return (
      <div className="space-y-6 max-w-7xl mx-auto">
        <h1 className="text-2xl font-extrabold">Operator Dashboard</h1>
        <LoadingSkeleton count={4} className="h-24" />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-3">
        <div>
          <span className="text-[10px] font-bold uppercase tracking-wider text-primary">Operator</span>
          <h1 className="text-2xl font-extrabold tracking-tight text-foreground">Request a data-wipe certificate</h1>
          <p className="text-xs text-muted-foreground mt-0.5 max-w-2xl">
            Before a device is sold or handed over, request a certificate for it. The Approver reviews the request; once
            approved the device is sanitized and a signed PDF certificate is issued for you to download.
          </p>
        </div>
        <div className="text-xs text-muted-foreground">Signed in as <strong className="text-foreground">{user?.name}</strong></div>
      </div>

      {notice && (
        <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-700 dark:text-emerald-400 text-xs flex items-center justify-between">
          <span className="flex items-center gap-2"><CheckCircle2 className="h-4 w-4" />{notice}</span>
          <button onClick={() => setNotice(null)} className="font-semibold">Dismiss</button>
        </div>
      )}
      {error && (
        <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-700 dark:text-rose-400 text-xs flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="font-semibold">Dismiss</button>
        </div>
      )}

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Awaiting approval" value={counts.pending} icon={Clock} tone="amber" hint="With the Approver" />
        <StatCard label="Being wiped" value={counts.inProgress} icon={Loader2} tone="blue" hint="Approved, in progress" />
        <StatCard label="Certificates ready" value={counts.ready} icon={FileCheck2} tone="emerald" hint="Download as PDF" />
        <StatCard label="Rejected" value={counts.rejected} icon={XCircle} tone="rose" hint="See the reason below" />
      </div>

      {/* My requests */}
      <section className="bg-card border border-border rounded-xl shadow-sm">
        <div className="p-4 border-b border-border flex items-center justify-between">
          <div>
            <h2 className="text-sm font-bold text-foreground">My certificate requests</h2>
            <p className="text-[11px] text-muted-foreground">Updates live as the Approver decides and the wipe runs.</p>
          </div>
          <span className="text-[11px] text-muted-foreground font-mono">{requests.length} total</span>
        </div>
        {requests.length === 0 ? (
          <div className="p-10 text-center text-xs text-muted-foreground">
            <FilePlus2 className="h-8 w-8 mx-auto mb-2 opacity-50" />
            You have not requested any certificates yet. Pick a device below to get started.
          </div>
        ) : (
          <div className="divide-y divide-border">
            {requests.map((r) => (
              <div key={r.id} className="p-4 grid grid-cols-1 lg:grid-cols-12 gap-4 items-center">
                <div className="lg:col-span-4 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-foreground truncate">{r.device_name}</span>
                    <StatusBadge status={r.status} label={certStatusLabel(r.status)} />
                  </div>
                  <div className="text-[11px] text-muted-foreground font-mono mt-0.5">
                    S/N {r.device_serial} · {formatMethod(r.method)}
                  </div>
                  <div className="text-[11px] text-muted-foreground mt-0.5">Requested {formatDate(r.created_at)}</div>
                </div>
                <div className="lg:col-span-5">
                  <RequestProgress request={r} />
                  {r.status === 'REJECTED' && (
                    <div className="mt-2 p-2 rounded-lg bg-rose-500/10 text-[11px] text-rose-700 dark:text-rose-400">
                      <strong>Rejected by {r.approver_name}:</strong> {r.decision_comment}
                    </div>
                  )}
                  {r.approver_name && r.status !== 'REJECTED' && (
                    <div className="mt-1 text-[10px] text-muted-foreground">Approved by {r.approver_name}</div>
                  )}
                </div>
                <div className="lg:col-span-3 flex lg:justify-end gap-2">
                  {r.certificate_id ? (
                    <div className="flex flex-col items-end gap-1">
                      <DownloadCertificateButton certificateId={r.certificate_id} />
                      <span className="text-[10px] font-mono text-muted-foreground">{r.certificate_id}</span>
                    </div>
                  ) : r.status === 'PENDING_APPROVAL' ? (
                    <button
                      onClick={() => withdraw(r)}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg border border-border hover:bg-muted"
                    >
                      <Undo2 className="h-3.5 w-3.5" /> Withdraw
                    </button>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Devices */}
      <section className="bg-card border border-border rounded-xl shadow-sm">
        <div className="p-4 border-b border-border flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-bold text-foreground">Office devices</h2>
            <p className="text-[11px] text-muted-foreground">Registered by the Admin. Request a certificate for the one you are selling.</p>
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
                <th className="text-left px-4 py-2.5 font-semibold">Certificate status</th>
                <th className="text-right px-4 py-2.5 font-semibold">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {filteredDevices.map((d) => {
                const status = d.wipe_status || 'NONE';
                const busy = ACTIVE_STATUSES.includes(status);
                return (
                  <tr key={d.id} className="hover:bg-muted/30">
                    <td className="px-4 py-2.5">
                      <div className="flex items-center gap-2">
                        <CategoryIcon category={d.category} className="h-4 w-4 text-muted-foreground" />
                        <span className="font-medium text-foreground">{d.manufacturer} {d.model}</span>
                      </div>
                    </td>
                    <td className="px-4 py-2.5 font-mono text-muted-foreground">{d.serial_number}</td>
                    <td className="px-4 py-2.5 text-muted-foreground">{d.category.replace(/_/g, ' ')}</td>
                    <td className="px-4 py-2.5">
                      <StatusBadge status={status} label={certStatusLabel(status)} />
                    </td>
                    <td className="px-4 py-2.5 text-right">
                      {busy ? (
                        <span className="text-[11px] text-muted-foreground inline-flex items-center gap-1">
                          <Info className="h-3.5 w-3.5" /> Request in progress
                        </span>
                      ) : (
                        <button
                          onClick={() => openWizard(d.id)}
                          disabled={openingId === d.id}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary text-primary-foreground font-semibold hover:bg-primary/90 disabled:opacity-60"
                        >
                          {openingId === d.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <FilePlus2 className="h-3.5 w-3.5" />}
                          {status === 'COMPLETED' ? 'Request again' : 'Request certificate'}
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
              {filteredDevices.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-muted-foreground">
                    No devices match your search.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      {wizardDevice && (
        <WipeRequestWizardModal
          key={wizardDevice.id}
          device={wizardDevice}
          isOpen
          onClose={() => setWizardDevice(null)}
          onSuccess={() => {
            setNotice(`Certificate request submitted for ${wizardDevice.manufacturer} ${wizardDevice.model}. It is now with the Approver.`);
            load();
          }}
        />
      )}
    </div>
  );
};
