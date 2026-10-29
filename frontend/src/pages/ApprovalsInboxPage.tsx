import React, { useState, useEffect } from 'react';
import {
  CheckSquare,
  AlertTriangle,
  Clock,
  ShieldCheck,
  XCircle,
  CheckCircle2,
  Lock,
  ArrowRight,
  Info,
  UserCheck,
} from 'lucide-react';
import { api } from '../lib/api';
import { WipeRequest } from '../types';
import { useAuthStore } from '../store/authStore';
import { LoadingSkeleton } from '../components/common/LoadingSkeleton';
import { StatusBadge } from '../components/common/StatusBadge';
import { formatDate } from '../lib/utils';

export const ApprovalsInboxPage: React.FC = () => {
  const [requests, setRequests] = useState<WipeRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedReq, setSelectedReq] = useState<WipeRequest | null>(null);
  const [modalType, setModalType] = useState<'approve' | 'reject' | null>(null);
  const [comment, setComment] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  const { user } = useAuthStore();

  const fetchInbox = async () => {
    try {
      const data = await api.getApprovalsInbox();
      setRequests(data);
    } catch {
      // Failed to load inbox
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInbox();
  }, []);

  const handleDecision = async () => {
    if (!selectedReq || !modalType) return;
    if (modalType === 'reject' && !comment.trim()) {
      setActionError('A written comment explaining the rejection is mandatory.');
      return;
    }

    setSubmitting(true);
    setActionError(null);
    try {
      if (modalType === 'approve') {
        await api.approveRequest(selectedReq.id, comment);
        setActionSuccess('Approved. The wipe has started and the certificate will be issued automatically.');
      } else {
        await api.rejectRequest(selectedReq.id, comment);
        setActionSuccess(`Request rejected.`);
      }
      setTimeout(() => {
        setModalType(null);
        setSelectedReq(null);
        setComment('');
        setActionSuccess(null);
        fetchInbox();
      }, 1000);
    } catch (err: any) {
      setActionError(err.message || 'Operation failed');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Header */}
      <div>
        <div className="flex items-center space-x-2">
          <div className="p-2 rounded-xl bg-amber-500/10 text-amber-600 dark:text-amber-400">
            <CheckSquare className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-2xl font-extrabold tracking-tight text-foreground">Approvals Inbox</h1>
            <p className="text-xs text-muted-foreground mt-0.5">
              Certificate requests from operators. A requester can never approve their own request.
            </p>
          </div>
        </div>
      </div>

      {/* Role Reminder */}
      <div className="p-4 rounded-xl bg-card border border-border flex items-center justify-between text-xs">
        <div className="flex items-center space-x-3">
          <UserCheck className="h-4 w-4 text-primary" />
          <div>
            <span className="font-bold text-foreground">Current Reviewer Persona: {user?.name}</span>
            <span className="text-muted-foreground ml-2 font-mono text-[11px]">Role: {user?.role}</span>
          </div>
        </div>
        <div className="text-[11px] text-muted-foreground">
          Pending in Queue: <strong className="text-foreground">{requests.length}</strong>
        </div>
      </div>

      {loading ? (
        <LoadingSkeleton count={3} className="h-28" />
      ) : requests.length === 0 ? (
        <div className="p-12 text-center bg-card border border-border rounded-xl">
          <CheckCircle2 className="h-10 w-10 text-emerald-500 mx-auto mb-2 opacity-80" />
          <h3 className="text-sm font-bold text-foreground">Approvals Inbox is Clear</h3>
          <p className="text-xs text-muted-foreground mt-1 max-w-md mx-auto">
            All submitted sanitization requests have been reviewed, approved, or rejected. Newly created requests will appear here in real time.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {requests.map((req) => {
            const isRequester = user?.id === req.requested_by;
            const isHighRisk = req.risk_level === 'HIGH' || req.risk_level === 'CRITICAL';

            return (
              <div
                key={req.id}
                className="bg-card border border-border rounded-xl p-5 shadow-sm space-y-4 hover:border-border/80 transition-all"
              >
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                  <div>
                    <div className="flex items-center space-x-2">
                      <span className="text-sm font-bold text-foreground">
                        {req.device_name || 'IT Asset'}
                      </span>
                      <StatusBadge status={req.status} />
                      <span
                        className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold uppercase ${
                          isHighRisk
                            ? 'bg-rose-500/20 text-rose-600 dark:text-rose-400'
                            : 'bg-emerald-500/20 text-emerald-600 dark:text-emerald-400'
                        }`}
                      >
                        {req.risk_level} RISK
                      </span>
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">
                      Target Method:{' '}
                      <strong className="text-foreground font-mono">
                        {req.method.replace(/_/g, ' ')}
                      </strong>{' '}
                      | NIST: {req.nist_category}
                    </div>
                  </div>

                  <div className="text-right text-[11px] text-muted-foreground">
                    <div>Expires: {formatDate(req.expires_at)}</div>
                    <div className="font-mono text-[10px]">Requested by: {req.requester_name || req.requested_by}</div>
                  </div>
                </div>

                <div className="p-3 bg-muted/40 rounded-lg text-xs space-y-1">
                  <span className="text-[10px] text-muted-foreground uppercase font-semibold">Justification</span>
                  <p className="text-foreground">{req.reason}</p>
                </div>

                {isHighRisk && (
                  <div className="p-2.5 bg-rose-500/10 border border-rose-500/20 rounded-lg text-[11px] text-rose-700 dark:text-rose-400 flex items-center gap-1.5 font-semibold">
                    <AlertTriangle className="h-3.5 w-3.5" />
                    Includes a system volume or the Purge method. Check before approving.
                  </div>
                )}

                {/* Actions */}
                <div className="pt-2 border-t border-border flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
                  {isRequester ? (
                    <div className="text-rose-600 dark:text-rose-400 font-semibold flex items-center gap-1.5 text-[11px]">
                      <AlertTriangle className="h-4 w-4" />
                      <span>Four-eyes rule: You submitted this request and cannot approve it.</span>
                    </div>
                  ) : (
                    <span className="text-muted-foreground text-[11px]">
                      Approving starts the certified wipe and issues a signed certificate.
                    </span>
                  )}

                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => {
                        setSelectedReq(req);
                        setModalType('reject');
                        setComment('');
                      }}
                      className="px-3.5 py-1.5 rounded-lg border border-border text-foreground hover:bg-destructive/10 hover:text-destructive hover:border-destructive/30 transition-colors font-semibold"
                    >
                      Reject
                    </button>
                    <button
                      disabled={isRequester || user?.role !== 'APPROVER'}
                      onClick={() => {
                        setSelectedReq(req);
                        setModalType('approve');
                        setComment('');
                      }}
                      className="px-4 py-1.5 rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 font-semibold transition-colors disabled:opacity-40 disabled:cursor-not-allowed shadow-sm"
                    >
                      Approve Request
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Decision Modal */}
      {modalType && selectedReq && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="bg-card border border-border rounded-2xl shadow-2xl w-full max-w-md p-6 space-y-4 animate-in fade-in zoom-in-95 text-xs">
            <h3 className="text-base font-bold text-foreground">
              {modalType === 'approve' ? 'Approve Sanitization Request' : 'Reject Sanitization Request'}
            </h3>
            <p className="text-muted-foreground">
              {selectedReq.device_name} — {selectedReq.method.replace(/_/g, ' ')}
            </p>

            {actionError && (
              <div className="p-3 bg-rose-500/10 border border-rose-500/30 text-rose-600 dark:text-rose-400 rounded-lg">
                {actionError}
              </div>
            )}
            {actionSuccess && (
              <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 text-emerald-600 dark:text-emerald-400 rounded-lg">
                {actionSuccess}
              </div>
            )}

            <div>
              <label className="block font-medium text-foreground mb-1">
                {modalType === 'approve' ? 'Reviewer Comment (Optional)' : 'Rejection Rationale (Mandatory)'}
              </label>
              <textarea
                rows={3}
                required={modalType === 'reject'}
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                placeholder={
                  modalType === 'approve'
                    ? 'Verified against IT asset disposal manifest...'
                    : 'Asset still retained for audit compliance...'
                }
                className="w-full p-2.5 bg-background border border-border rounded-lg text-xs"
              />
            </div>

            <div className="flex items-center justify-end space-x-2 pt-2">
              <button
                onClick={() => setModalType(null)}
                disabled={submitting}
                className="px-3.5 py-1.5 rounded-lg border border-border text-foreground hover:bg-muted"
              >
                Cancel
              </button>
              <button
                onClick={handleDecision}
                disabled={submitting}
                className={`px-4 py-1.5 rounded-lg font-semibold text-white transition-colors disabled:opacity-50 ${
                  modalType === 'approve' ? 'bg-emerald-600 hover:bg-emerald-700' : 'bg-rose-600 hover:bg-rose-700'
                }`}
              >
                {submitting ? 'Processing...' : modalType === 'approve' ? 'Confirm Approval' : 'Confirm Rejection'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
