import React, { useState, useEffect } from 'react';
import {
  FileSearch,
  ShieldCheck,
  ShieldAlert,
  Download,
  Filter,
  CheckCircle2,
  RefreshCw,
  Search,
} from 'lucide-react';
import { api } from '../lib/api';
import { AuditLog } from '../types';
import { LoadingSkeleton } from '../components/common/LoadingSkeleton';
import { formatDate } from '../lib/utils';

export const AuditLogPage: React.FC = () => {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [verifying, setVerifying] = useState(false);
  const [chainResult, setChainResult] = useState<{
    is_valid: boolean;
    total_records: number;
    error?: string;
  } | null>(null);
  const [actionFilter, setActionFilter] = useState('');
  const [searchTerm, setSearchTerm] = useState('');

  const fetchLogs = async () => {
    try {
      const data = await api.getAuditLogs({ action: actionFilter || undefined, limit: 100 });
      setLogs(data);
    } catch {
      // Error fetching logs
    } finally {
      setLoading(false);
    }
  };

  const verifyChain = async () => {
    setVerifying(true);
    try {
      const res = await api.verifyAuditChain();
      setChainResult(res);
    } catch (err: any) {
      setChainResult({
        is_valid: false,
        total_records: 0,
        error: err.message || 'Chain verification failed',
      });
    } finally {
      setVerifying(false);
    }
  };

  useEffect(() => {
    fetchLogs();
    verifyChain();
  }, [actionFilter]);

  const handleExportCsv = () => {
    window.open('/api/v1/audit/export.csv', '_blank');
  };

  const filteredLogs = logs.filter((l) => {
    if (!searchTerm) return true;
    const term = searchTerm.toLowerCase();
    return (
      l.action.toLowerCase().includes(term) ||
      (l.actor_email && l.actor_email.toLowerCase().includes(term)) ||
      (l.entity_type && l.entity_type.toLowerCase().includes(term)) ||
      l.hash.toLowerCase().includes(term)
    );
  });

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight text-foreground">Immutable Hash-Chained Audit Trail</h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            Append-only tamper-evident log protected by PostgreSQL trigger blocking UPDATE and DELETE.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={verifyChain}
            disabled={verifying}
            className="flex items-center space-x-1.5 px-3 py-2 text-xs font-semibold rounded-lg border border-border bg-card hover:bg-muted transition-colors text-foreground shadow-sm"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${verifying ? 'animate-spin' : ''}`} />
            <span>Verify Chain Integrity</span>
          </button>
          <button
            onClick={handleExportCsv}
            className="flex items-center space-x-1.5 px-3.5 py-2 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors shadow-sm"
          >
            <Download className="h-3.5 w-3.5" />
            <span>Export CSV</span>
          </button>
        </div>
      </div>

      {/* Cryptographic Chain Integrity Status Card */}
      {chainResult && (
        <div
          className={`p-4 rounded-xl border flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs shadow-sm ${
            chainResult.is_valid
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-900 dark:text-emerald-300'
              : 'bg-rose-500/10 border-rose-500/30 text-rose-900 dark:text-rose-300'
          }`}
        >
          <div className="flex items-center space-x-3">
            {chainResult.is_valid ? (
              <ShieldCheck className="h-6 w-6 text-emerald-600 dark:text-emerald-400 shrink-0" />
            ) : (
              <ShieldAlert className="h-6 w-6 text-rose-600 dark:text-rose-400 shrink-0" />
            )}
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-extrabold text-sm uppercase tracking-wide">
                  {chainResult.is_valid ? 'Hash Chain Integrity: INTACT & VALID' : 'Hash Chain Integrity: TAMPERED'}
                </span>
                <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-black/10 dark:bg-white/10 font-bold">
                  {chainResult.total_records} Verified Records
                </span>
              </div>
              <p className="text-[11px] opacity-80 mt-0.5">
                Every record sequentially binds <code className="font-mono">prev_hash</code> to SHA-256(seq + ts + actor + action + entity + details).
              </p>
            </div>
          </div>

          <div className="text-[11px] font-mono shrink-0">
            Trigger: <strong className="text-foreground">UPDATE/DELETE BLOCKED</strong>
          </div>
        </div>
      )}

      {/* Filters Toolbar */}
      <div className="bg-card border border-border p-4 rounded-xl shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="h-4 w-4 absolute left-3 top-2.5 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search action, actor, entity, or hash..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-4 py-2 text-xs bg-background border border-border rounded-lg focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </div>

        <div className="flex items-center space-x-2 text-xs">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <select
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
            className="px-3 py-2 bg-background border border-border rounded-lg text-xs"
          >
            <option value="">All Actions</option>
            <option value="DEVICE_REGISTERED">DEVICE_REGISTERED</option>
            <option value="WIPE_REQUEST_CREATED">WIPE_REQUEST_CREATED</option>
            <option value="WIPE_REQUEST_APPROVED">WIPE_REQUEST_APPROVED</option>
            <option value="WIPE_JOB_STARTED">WIPE_JOB_STARTED</option>
            <option value="WIPE_JOB_COMPLETED">WIPE_JOB_COMPLETED</option>
            <option value="CERTIFICATE_ISSUED">CERTIFICATE_ISSUED</option>
            <option value="CERTIFICATE_REVOKED">CERTIFICATE_REVOKED</option>
          </select>
        </div>
      </div>

      {/* Audit Log Table */}
      {loading ? (
        <LoadingSkeleton count={6} className="h-16" />
      ) : filteredLogs.length === 0 ? (
        <div className="p-12 text-center bg-card border border-border rounded-xl text-xs text-muted-foreground">
          No audit records found matching your filter.
        </div>
      ) : (
        <div className="bg-card border border-border rounded-xl shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-muted/50 border-b border-border text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
                <tr>
                  <th className="px-5 py-3">Seq #</th>
                  <th className="px-5 py-3">Timestamp</th>
                  <th className="px-5 py-3">Actor</th>
                  <th className="px-5 py-3">Action</th>
                  <th className="px-5 py-3">Entity</th>
                  <th className="px-5 py-3">Cryptographic SHA-256 Hash</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60 font-mono text-[11px]">
                {filteredLogs.map((l) => (
                  <tr key={l.id} className="hover:bg-muted/30 transition-colors">
                    <td className="px-5 py-3.5 font-bold text-primary">#{l.seq}</td>
                    <td className="px-5 py-3.5 text-muted-foreground font-sans">{formatDate(l.timestamp)}</td>
                    <td className="px-5 py-3.5 font-sans">
                      <span className="font-semibold text-foreground">{l.actor_email || 'System'}</span>
                    </td>
                    <td className="px-5 py-3.5">
                      <span className="px-2 py-0.5 rounded bg-muted text-foreground font-semibold text-[10px]">
                        {l.action}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 text-muted-foreground font-sans">
                      {l.entity_type} {l.entity_id ? `(${l.entity_id.slice(0, 8)}...)` : ''}
                    </td>
                    <td className="px-5 py-3.5 text-muted-foreground">
                      <div className="truncate max-w-[200px]" title={`Hash: ${l.hash}\nPrev: ${l.prev_hash}`}>
                        {l.hash.slice(0, 24)}...
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
