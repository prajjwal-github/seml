import React, { useState, useEffect } from 'react';
import {
  FileCheck2,
  Download,
  Eye,
  ShieldAlert,
  Search,
  ExternalLink,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Lock,
} from 'lucide-react';
import { api } from '../lib/api';
import { Certificate } from '../types';
import { StatusBadge } from '../components/common/StatusBadge';
import { LoadingSkeleton } from '../components/common/LoadingSkeleton';
import { formatDate } from '../lib/utils';
import { useAuthStore } from '../store/authStore';

export const CertificatesPage: React.FC = () => {
  const [certs, setCerts] = useState<Certificate[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [previewCert, setPreviewCert] = useState<Certificate | null>(null);
  const [revokeCert, setRevokeCert] = useState<Certificate | null>(null);
  const [revokeReason, setRevokeReason] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const { user } = useAuthStore();

  const fetchCerts = async () => {
    try {
      const data = await api.getCertificates(searchTerm);
      setCerts(data);
    } catch {
      // Failed to load certs
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCerts();
  }, [searchTerm]);

  const handleRevoke = async () => {
    if (!revokeCert || !revokeReason.trim()) return;
    setSubmitting(true);
    setErrorMsg(null);
    try {
      await api.revokeCertificate(revokeCert.certificate_id, revokeReason.trim());
      setRevokeCert(null);
      setRevokeReason('');
      fetchCerts();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to revoke certificate');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDownloadPdf = async (certId: string) => {
    setErrorMsg(null);
    try {
      await api.downloadCertificatePdf(certId);
    } catch (err: any) {
      setErrorMsg(err.message || 'Could not download the certificate');
    }
  };

  const handleDownloadJson = (cert: Certificate) => {
    const blob = new Blob([JSON.stringify(cert.payload, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${cert.certificate_id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight text-foreground">
            {user?.role === 'OPERATOR' ? 'My Certificates' : 'Certificates of Sanitization'}
          </h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            Cryptographically signed with Ed25519, embedded QR codes, and diagonal simulation watermarks.
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <a
            href="/verify"
            target="_blank"
            rel="noreferrer"
            className="flex items-center space-x-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg border border-border bg-card hover:bg-muted transition-colors text-foreground"
          >
            <ExternalLink className="h-3.5 w-3.5 text-primary" />
            <span>Open Public Verifier</span>
          </a>
        </div>
      </div>

      {/* Search Toolbar */}
      <div className="bg-card border border-border p-4 rounded-xl shadow-sm flex items-center justify-between">
        <div className="relative flex-1 max-w-md">
          <Search className="h-4 w-4 absolute left-3 top-2.5 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search certificate ID or device model..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-4 py-2 text-xs bg-background border border-border rounded-lg focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </div>
        <span className="text-xs text-muted-foreground font-mono">{certs.length} certificates</span>
      </div>

      {errorMsg && !revokeCert && (
        <div className="p-3 text-xs bg-rose-500/10 border border-rose-500/30 text-rose-600 dark:text-rose-400 rounded-lg">
          {errorMsg}
        </div>
      )}

      {loading ? (
        <LoadingSkeleton count={4} className="h-16" />
      ) : certs.length === 0 ? (
        <div className="p-12 text-center bg-card border border-border rounded-xl">
          <FileCheck2 className="h-8 w-8 text-muted-foreground mx-auto mb-2 opacity-50" />
          <p className="text-sm font-semibold text-foreground">No certificates found</p>
          <p className="text-xs text-muted-foreground mt-1">Certificates are automatically generated when a wipe job completes.</p>
        </div>
      ) : (
        <div className="bg-card border border-border rounded-xl shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-muted/50 border-b border-border text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
                <tr>
                  <th className="px-5 py-3">Certificate ID</th>
                  <th className="px-5 py-3">Device & Method</th>
                  <th className="px-5 py-3">Issued Date</th>
                  <th className="px-5 py-3">Ed25519 Key ID</th>
                  <th className="px-5 py-3">Status</th>
                  <th className="px-5 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60">
                {certs.map((c) => (
                  <tr key={c.id} className="hover:bg-muted/30 transition-colors">
                    <td className="px-5 py-3.5">
                      <div className="flex items-center space-x-2">
                        <FileCheck2 className="h-4 w-4 text-emerald-500 shrink-0" />
                        <span className="font-mono font-bold text-foreground">{c.certificate_id}</span>
                      </div>
                    </td>
                    <td className="px-5 py-3.5">
                      <div className="font-semibold text-foreground">{c.device_model || 'Inspected Device'}</div>
                      <div className="text-[11px] text-muted-foreground font-mono">{c.method || 'NIST SP 800-88'}</div>
                    </td>
                    <td className="px-5 py-3.5 text-muted-foreground">{formatDate(c.issued_at)}</td>
                    <td className="px-5 py-3.5 font-mono text-[11px] text-muted-foreground">{c.public_key_id}</td>
                    <td className="px-5 py-3.5">
                      {c.revoked_at ? (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold font-mono bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20">
                          REVOKED
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold font-mono bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                          VALID
                        </span>
                      )}
                    </td>
                    <td className="px-5 py-3.5 text-right space-x-2">
                      <button
                        onClick={() => setPreviewCert(c)}
                        className="px-2.5 py-1 rounded bg-muted hover:bg-muted/80 text-foreground transition-colors font-semibold"
                        title="View Canonical Payload"
                      >
                        Inspect
                      </button>
                      <button
                        onClick={() => handleDownloadPdf(c.certificate_id)}
                        className="px-2.5 py-1 rounded bg-primary/10 text-primary hover:bg-primary/20 transition-colors font-semibold inline-flex items-center gap-1"
                        title="Download Signed PDF"
                      >
                        <Download className="h-3 w-3" />
                        <span>PDF</span>
                      </button>
                      <button
                        onClick={() => handleDownloadJson(c)}
                        className="px-2.5 py-1 rounded bg-muted hover:bg-muted/80 text-foreground transition-colors font-semibold font-mono text-[11px]"
                        title="Download JSON Payload"
                      >
                        JSON
                      </button>
                      {(user?.role === 'ADMIN' || user?.role === 'APPROVER') && !c.revoked_at && (
                        <button
                          onClick={() => setRevokeCert(c)}
                          className="px-2 py-1 rounded text-rose-600 dark:text-rose-400 hover:bg-rose-500/10 transition-colors font-semibold"
                          title="Revoke Certificate"
                        >
                          Revoke
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Preview JSON Modal */}
      {previewCert && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="bg-card border border-border rounded-2xl shadow-2xl w-full max-w-2xl p-6 space-y-4 animate-in fade-in zoom-in-95 text-xs max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between border-b border-border pb-3 shrink-0">
              <div>
                <h3 className="text-base font-bold text-foreground">Certificate Cryptographic Payload</h3>
                <p className="text-muted-foreground font-mono">{previewCert.certificate_id}</p>
              </div>
              <button onClick={() => setPreviewCert(null)} className="p-1 rounded-lg text-muted-foreground hover:bg-muted">
                &times;
              </button>
            </div>

            <div className="p-3 bg-muted/40 rounded-lg text-[11px] font-mono space-y-1 shrink-0">
              <div className="text-muted-foreground truncate">
                SHA-256 Digest: <strong className="text-foreground">{previewCert.payload_sha256}</strong>
              </div>
              <div className="text-muted-foreground truncate">
                Ed25519 Signature: <strong className="text-foreground">{previewCert.signature.slice(0, 32)}...</strong>
              </div>
              <div className="text-muted-foreground">
                Signing Key: <strong className="text-foreground">{previewCert.public_key_id}</strong>
              </div>
            </div>

            <pre className="p-4 rounded-xl bg-slate-950 text-slate-100 overflow-y-auto font-mono text-[11px] flex-1 leading-relaxed">
              {JSON.stringify(previewCert.payload, null, 2)}
            </pre>

            <div className="flex justify-end space-x-2 pt-2 border-t border-border shrink-0">
              <button
                onClick={() => handleDownloadPdf(previewCert.certificate_id)}
                className="px-3 py-1.5 rounded-lg bg-primary text-primary-foreground font-semibold flex items-center gap-1.5"
              >
                <Download className="h-3.5 w-3.5" />
                <span>Download ReportLab PDF</span>
              </button>
              <button
                onClick={() => setPreviewCert(null)}
                className="px-3.5 py-1.5 rounded-lg border border-border text-foreground hover:bg-muted"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Revoke Modal */}
      {revokeCert && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="bg-card border border-border rounded-2xl shadow-2xl w-full max-w-md p-6 space-y-4 animate-in fade-in zoom-in-95 text-xs">
            <h3 className="text-base font-bold text-foreground">Revoke Certificate of Sanitization</h3>
            <p className="text-muted-foreground">
              Are you sure you want to revoke certificate <strong className="font-mono text-foreground">{revokeCert.certificate_id}</strong>? This action will permanently mark the certificate as revoked and record an audit log entry.
            </p>

            {errorMsg && (
              <div className="p-3 bg-rose-500/10 border border-rose-500/30 text-rose-600 dark:text-rose-400 rounded-lg">
                {errorMsg}
              </div>
            )}

            <div>
              <label className="block font-medium text-foreground mb-1">Mandatory Revocation Reason</label>
              <textarea
                rows={3}
                required
                value={revokeReason}
                onChange={(e) => setRevokeReason(e.target.value)}
                placeholder="Discovered post-sanitization compliance violation..."
                className="w-full p-2.5 bg-background border border-border rounded-lg text-xs"
              />
            </div>

            <div className="flex justify-end space-x-2 pt-2">
              <button
                onClick={() => setRevokeCert(null)}
                disabled={submitting}
                className="px-3.5 py-1.5 rounded-lg border border-border text-foreground hover:bg-muted"
              >
                Cancel
              </button>
              <button
                onClick={handleRevoke}
                disabled={submitting || !revokeReason.trim()}
                className="px-4 py-1.5 rounded-lg bg-rose-600 text-white font-semibold hover:bg-rose-700 transition-colors disabled:opacity-50"
              >
                {submitting ? 'Revoking...' : 'Confirm Revocation'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
