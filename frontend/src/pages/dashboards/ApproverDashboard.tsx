import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Inbox,
  CheckCircle2,
  XCircle,
  FileCheck2,
  AlertTriangle,
  ShieldCheck,
  User as UserIcon,
} from 'lucide-react';
import { api } from '../../lib/api';
import { WipeRequest } from '../../types';
import { useAuthStore } from '../../store/authStore';
import { useLiveRefresh } from '../../lib/useLiveRefresh';
import { ACTIVE_STATUSES, certStatusLabel, formatMethod } from '../../lib/roles';
import { formatDate } from '../../lib/utils';
import { StatCard } from '../../components/common/StatCard';
import { StatusBadge } from '../../components/common/StatusBadge';
import { LoadingSkeleton } from '../../components/common/LoadingSkeleton';
import { RequestProgress } from '../../components/common/RequestProgress';
import { DownloadCertificateButton } from '../../components/common/DownloadCertificateButton';

type Decision = { request: WipeRequest; type: 'approve' | 'reject' };

export const ApproverDashboard: React.FC = () => {
  const { user } = useAuthStore();
  const [requests, setRequests] = useState<WipeRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [decision, setDecision] = useState<Decision | null>(null);
  const [comment, setComment] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setRequests(await api.getWipeRequests());
    } catch {
      // keep last data
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const pending = requests.filter((r) => r.status === 'PENDING_APPROVAL');
  const decided = requests.filter((r) => r.status !== 'PENDING_APPROVAL' && r.status !== 'CANCELLED');
  const hasRunning = requests.some((r) => ACTIVE_STATUSES.includes(r.status) && r.status !== 'PENDING_APPROVAL');
  useLiveRefresh(load, hasRunning);

  const counts = useMemo(
    () => ({
      approved: requests.filter((r) => !['PENDING_APPROVAL', 'REJECTED', 'CANCELLED', 'EXPIRED'].includes(r.status)).length,
      rejected: requests.filter((r) => r.status === 'REJECTED').length,
      certificates: requests.filter((r) => r.certificate_id).length,
    }),
    [requests]
  );

  const openDecision = (request: WipeRequest, type: 'approve' | 'reject') => {
    setDecision({ request, type });
    setComment('');
    setModalError(null);
  };

  const submitDecision = async () => {
    if (!decision) return;
    if (decision.type === 'reject' && !comment.trim()) {
      setModalError('Please write the reason for rejecting. The operator will see it.');
      return;
    }
    setSubmitting(true);
    setModalError(null);
    try {
      if (decision.type === 'approve') {
        await api.approveRequest(decision.request.id, comment.trim() || undefined);
        setNotice(`Approved ${decision.request.device_name}. The wipe has started and the certificate will be issued automatically.`);
      } else {
        await api.rejectRequest(decision.request.id, comment.trim());
        setNotice(`Rejected ${decision.request.device_name}. The operator has been notified.`);
      }
      setDecision(null);
      load();
    } catch (err: any) {
      setModalError(err.message || 'Could not record the decision');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6 max-w-7xl mx-auto">
        <h1 className="text-2xl font-extrabold">Approver Dashboard</h1>
        <LoadingSkeleton count={4} className="h-24" />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div>
        <span className="text-[10px] font-bold uppercase tracking-wider text-primary">Approver</span>
        <h1 className="text-2xl font-extrabold tracking-tight text-foreground">Certificate approvals</h1>
        <p className="text-xs text-muted-foreground mt-0.5 max-w-2xl">
          Review each request from an operator. Approving starts the certified wipe of the device and issues a signed
          certificate; rejecting sends your reason back to the operator.
        </p>
      </div>

      {notice && (
        <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-700 dark:text-emerald-400 text-xs flex items-center justify-between">
          <span className="flex items-center gap-2"><CheckCircle2 className="h-4 w-4" />{notice}</span>
          <button onClick={() => setNotice(null)} className="font-semibold">Dismiss</button>
        </div>
      )}

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Waiting for you" value={pending.length} icon={Inbox} tone="amber" hint="Pending decisions" />
        <StatCard label="Approved" value={counts.approved} icon={CheckCircle2} tone="emerald" hint="All time" />
        <StatCard label="Rejected" value={counts.rejected} icon={XCircle} tone="rose" hint="All time" />
        <StatCard label="Certificates issued" value={counts.certificates} icon={FileCheck2} tone="indigo" hint="Signed PDFs" />
      </div>

      {/* Pending queue */}
      <section className="bg-card border border-border rounded-xl shadow-sm">
        <div className="p-4 border-b border-border flex items-center justify-between">
          <div>
            <h2 className="text-sm font-bold text-foreground">Pending requests</h2>
            <p className="text-[11px] text-muted-foreground">New requests appear here instantly.</p>
          </div>
          {pending.length > 0 && (
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-700 dark:text-amber-400 font-bold">
              {pending.length} ACTION NEEDED
            </span>
          )}
        </div>
        {pending.length === 0 ? (
          <div className="p-10 text-center text-xs text-muted-foreground">
            <ShieldCheck className="h-8 w-8 mx-auto mb-2 text-emerald-500 opacity-80" />
            All caught up. There are no requests waiting for approval.
          </div>
        ) : (
          <div className="divide-y divide-border">
            {pending.map((r) => {
              const highRisk = r.risk_level === 'HIGH' || r.risk_level === 'CRITICAL';
              const ownRequest = r.requested_by === user?.id;
              return (
                <div key={r.id} className="p-4 flex flex-col lg:flex-row lg:items-center gap-4">
                  <div className="flex-1 min-w-0 space-y-1.5">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-sm font-semibold text-foreground">{r.device_name}</span>
                      <span className="text-[11px] font-mono text-muted-foreground">S/N {r.device_serial}</span>
                      <span
                        className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold ${
                          highRisk ? 'bg-rose-500/15 text-rose-600 dark:text-rose-400' : 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'
                        }`}
                      >
                        {r.risk_level} RISK
                      </span>
                    </div>
                    <div className="text-[11px] text-muted-foreground flex flex-wrap gap-x-4 gap-y-1">
                      <span className="inline-flex items-center gap-1"><UserIcon className="h-3 w-3" />{r.requester_name}</span>
                      <span>{formatMethod(r.method)}</span>
                      <span>{r.volume_ids.length} volume(s)</span>
                      <span>Submitted {formatDate(r.created_at)}</span>
                    </div>
                    <p className="text-xs text-foreground bg-muted/40 rounded-lg px-3 py-2">
                      <span className="text-muted-foreground">Reason: </span>{r.reason}
                    </p>
                    {highRisk && (
                      <p className="text-[11px] text-rose-600 dark:text-rose-400 flex items-center gap-1">
                        <AlertTriangle className="h-3.5 w-3.5" /> Includes a system volume or the Purge method. Check before approving.
                      </p>
                    )}
                  </div>
                  <div className="flex gap-2 shrink-0">
                    <button
                      onClick={() => openDecision(r, 'reject')}
                      className="px-3.5 py-2 rounded-lg border border-border text-xs font-semibold hover:bg-rose-500/10 hover:text-rose-600 hover:border-rose-500/30"
                    >
                      Reject
                    </button>
                    <button
                      onClick={() => openDecision(r, 'approve')}
                      disabled={ownRequest}
                      className="px-4 py-2 rounded-lg bg-emerald-600 text-white text-xs font-semibold hover:bg-emerald-700 disabled:opacity-40 shadow-sm"
                    >
                      Approve
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* Decisions & progress */}
      <section className="bg-card border border-border rounded-xl shadow-sm">
        <div className="p-4 border-b border-border">
          <h2 className="text-sm font-bold text-foreground">Decisions and certificates</h2>
          <p className="text-[11px] text-muted-foreground">Approved requests move through wiping to a signed certificate.</p>
        </div>
        {decided.length === 0 ? (
          <div className="p-8 text-center text-xs text-muted-foreground">No decisions yet.</div>
        ) : (
          <div className="divide-y divide-border">
            {decided.map((r) => (
              <div key={r.id} className="p-4 grid grid-cols-1 lg:grid-cols-12 gap-4 items-center">
                <div className="lg:col-span-4 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-foreground truncate">{r.device_name}</span>
                    <StatusBadge status={r.status} label={certStatusLabel(r.status)} />
                  </div>
                  <div className="text-[11px] text-muted-foreground mt-0.5">
                    Requested by {r.requester_name} · decided {formatDate(r.decided_at)}
                  </div>
                  {r.decision_comment && (
                    <div className="text-[11px] text-muted-foreground italic mt-0.5 truncate">“{r.decision_comment}”</div>
                  )}
                </div>
                <div className="lg:col-span-5">
                  <RequestProgress request={r} />
                </div>
                <div className="lg:col-span-3 flex lg:justify-end">
                  {r.certificate_id && <DownloadCertificateButton certificateId={r.certificate_id} compact />}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {decision && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="bg-card border border-border rounded-2xl shadow-2xl w-full max-w-md p-6 space-y-4 text-xs">
            <h3 className="text-base font-bold text-foreground">
              {decision.type === 'approve' ? 'Approve certificate request' : 'Reject certificate request'}
            </h3>
            <p className="text-muted-foreground">
              {decision.request.device_name} (S/N {decision.request.device_serial}) requested by{' '}
              {decision.request.requester_name}
            </p>
            {decision.type === 'approve' && (
              <p className="p-3 rounded-lg bg-emerald-500/10 text-emerald-700 dark:text-emerald-400">
                Approving starts the certified wipe (simulation) right away. When it finishes, a signed PDF certificate is
                issued to the operator.
              </p>
            )}
            {modalError && (
              <div className="p-3 bg-rose-500/10 border border-rose-500/30 text-rose-600 dark:text-rose-400 rounded-lg">{modalError}</div>
            )}
            <div>
              <label className="block font-medium text-foreground mb-1">
                {decision.type === 'approve' ? 'Comment (optional)' : 'Reason for rejection (required)'}
              </label>
              <textarea
                rows={3}
                autoFocus
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                placeholder={decision.type === 'approve' ? 'Verified against the disposal list.' : 'Asset tag missing, please resubmit.'}
                className="w-full p-2.5 bg-background border border-border rounded-lg text-xs"
              />
            </div>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setDecision(null)}
                disabled={submitting}
                className="px-3.5 py-1.5 rounded-lg border border-border hover:bg-muted"
              >
                Cancel
              </button>
              <button
                onClick={submitDecision}
                disabled={submitting}
                className={`px-4 py-1.5 rounded-lg font-semibold text-white disabled:opacity-50 ${
                  decision.type === 'approve' ? 'bg-emerald-600 hover:bg-emerald-700' : 'bg-rose-600 hover:bg-rose-700'
                }`}
              >
                {submitting ? 'Saving…' : decision.type === 'approve' ? 'Confirm approval' : 'Confirm rejection'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
