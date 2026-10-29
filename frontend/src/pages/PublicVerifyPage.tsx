import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ShieldCheck,
  ShieldAlert,
  Search,
  Upload,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  FileCode,
  ArrowRight,
  RefreshCw,
  ExternalLink,
} from 'lucide-react';
import { api } from '../lib/api';
import { SimulationBanner } from '../components/common/SimulationBanner';
import { formatDate } from '../lib/utils';

export const PublicVerifyPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [certIdInput, setCertIdInput] = useState(id || '');
  const [verifying, setVerifying] = useState(false);
  const [result, setResult] = useState<any | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [jsonInput, setJsonInput] = useState('');
  const [sigInput, setSigInput] = useState('');
  const [showJsonTab, setShowJsonTab] = useState(false);

  const runVerificationById = async (targetId: string) => {
    if (!targetId.trim()) return;
    setVerifying(true);
    setErrorMsg(null);
    setResult(null);
    try {
      const res = await api.verifyById(targetId.trim());
      setResult(res);
    } catch (err: any) {
      setErrorMsg(err.message || 'Verification failed');
    } finally {
      setVerifying(false);
    }
  };

  const runVerificationByPayload = async (payload: any, sig: string) => {
    setVerifying(true);
    setErrorMsg(null);
    setResult(null);
    try {
      const res = await api.verifyPayload(payload, sig);
      setResult(res);
    } catch (err: any) {
      setErrorMsg(err.message || 'Verification failed');
    } finally {
      setVerifying(false);
    }
  };

  useEffect(() => {
    if (id) {
      setCertIdInput(id);
      runVerificationById(id);
    }
  }, [id]);

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const parsed = JSON.parse(event.target?.result as string);
        if (parsed.payload && parsed.signature) {
          runVerificationByPayload(parsed.payload, parsed.signature);
        } else if (parsed.certificate_id) {
          // If pure certificate object
          runVerificationById(parsed.certificate_id);
        } else {
          setErrorMsg('Uploaded JSON file missing required payload or signature fields.');
        }
      } catch {
        setErrorMsg('Invalid JSON file.');
      }
    };
    reader.readAsText(file);
  };

  // Tamper test simulation: load sample certificate, mutate 1 byte, verify it fails with TAMPERED
  const handleTamperTest = async () => {
    if (!result?.payload || !result?.signature) {
      setErrorMsg('Load a valid certificate first to test tamper detection.');
      return;
    }
    // Deep clone and mutate one byte/field in payload
    const tamperedPayload = JSON.parse(JSON.stringify(result.payload));
    tamperedPayload.device_model = (tamperedPayload.device_model || 'Device') + ' [TAMPERED_BYTE]';
    await runVerificationByPayload(tamperedPayload, result.signature);
  };

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      {/* Simulation Banner */}
      <SimulationBanner />

      {/* Public Header */}
      <header className="border-b border-border bg-card/80 backdrop-blur-sm px-6 py-4 flex items-center justify-between">
        <Link to="/" className="flex items-center space-x-2.5">
          <div className="w-8 h-8 rounded-lg bg-primary/10 border border-primary/20 text-primary flex items-center justify-center">
            <ShieldCheck className="h-5 w-5" />
          </div>
          <div>
            <span className="font-extrabold text-base tracking-tight text-foreground">SecureWipe Public Verifier</span>
            <span className="text-[10px] font-mono ml-2 text-muted-foreground uppercase">Ed25519 Offline Validation</span>
          </div>
        </Link>

        <div className="flex items-center space-x-3 text-xs">
          <a
            href="/.well-known/wipe-keys"
            target="_blank"
            rel="noreferrer"
            className="text-muted-foreground hover:text-foreground flex items-center gap-1 font-mono text-[11px]"
          >
            <span>Public Keys</span>
            <ExternalLink className="h-3 w-3" />
          </a>
          <Link to="/dashboard" className="font-semibold text-primary hover:underline">
            Go to Platform &rarr;
          </Link>
        </div>
      </header>

      {/* Main Verifier Content */}
      <main className="flex-1 max-w-4xl mx-auto w-full p-6 sm:p-10 space-y-6">
        <div className="text-center max-w-xl mx-auto space-y-2">
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-foreground">
            Verify Certificate of Sanitization
          </h1>
          <p className="text-xs text-muted-foreground">
            Verify digital signatures generated via NIST SP 800-88 Rev. 1 sanitization procedures. Anyone can independently verify authenticity without logging in.
          </p>
        </div>

        {/* Verification Input Box */}
        <div className="bg-card border border-border rounded-2xl shadow-lg p-6 space-y-4">
          <div className="flex border-b border-border text-xs font-semibold">
            <button
              onClick={() => setShowJsonTab(false)}
              className={`pb-3 px-4 border-b-2 transition-colors ${
                !showJsonTab ? 'border-primary text-primary font-bold' : 'border-transparent text-muted-foreground'
              }`}
            >
              Verify by Certificate ID
            </button>
            <button
              onClick={() => setShowJsonTab(true)}
              className={`pb-3 px-4 border-b-2 transition-colors ${
                showJsonTab ? 'border-primary text-primary font-bold' : 'border-transparent text-muted-foreground'
              }`}
            >
              Upload / Paste JSON Payload
            </button>
          </div>

          {!showJsonTab ? (
            <div className="space-y-4">
              <div className="flex flex-col sm:flex-row gap-2">
                <div className="relative flex-1">
                  <Search className="h-4 w-4 absolute left-3 top-3 text-muted-foreground" />
                  <input
                    type="text"
                    value={certIdInput}
                    onChange={(e) => setCertIdInput(e.target.value)}
                    placeholder="e.g. CERT-2026-6C48B25E"
                    className="w-full pl-9 pr-4 py-2.5 text-xs bg-background border border-border rounded-lg font-mono focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>
                <button
                  onClick={() => runVerificationById(certIdInput)}
                  disabled={verifying || !certIdInput.trim()}
                  className="px-5 py-2.5 rounded-lg bg-primary text-primary-foreground font-semibold text-xs hover:bg-primary/90 transition-colors disabled:opacity-50 shrink-0"
                >
                  {verifying ? 'Verifying...' : 'Verify Certificate'}
                </button>
              </div>

              {/* Drag and Drop Zone */}
              <div className="border border-dashed border-border rounded-xl p-4 text-center bg-muted/20 hover:bg-muted/40 transition-colors cursor-pointer relative">
                <input
                  type="file"
                  accept=".json"
                  onChange={handleFileUpload}
                  className="absolute inset-0 opacity-0 cursor-pointer"
                />
                <Upload className="h-5 w-5 text-muted-foreground mx-auto mb-1" />
                <span className="text-xs font-semibold text-foreground block">
                  Drop certificate JSON file here or browse
                </span>
                <span className="text-[10px] text-muted-foreground">Supported format: .json</span>
              </div>
            </div>
          ) : (
            <div className="space-y-3 text-xs">
              <div>
                <label className="block font-medium text-foreground mb-1">JSON Payload</label>
                <textarea
                  rows={4}
                  value={jsonInput}
                  onChange={(e) => setJsonInput(e.target.value)}
                  placeholder='{"certificate_id": "CERT-2026-XXXX", "device_category": "LAPTOP", ...}'
                  className="w-full p-2.5 bg-background border border-border rounded-lg font-mono text-[11px]"
                />
              </div>
              <div>
                <label className="block font-medium text-foreground mb-1">Ed25519 Signature (Base64)</label>
                <input
                  type="text"
                  value={sigInput}
                  onChange={(e) => setSigInput(e.target.value)}
                  placeholder="Base64 encoded Ed25519 signature string..."
                  className="w-full px-3 py-2 bg-background border border-border rounded-lg font-mono text-[11px]"
                />
              </div>
              <button
                onClick={() => {
                  try {
                    const parsed = JSON.parse(jsonInput);
                    runVerificationByPayload(parsed, sigInput.trim());
                  } catch {
                    setErrorMsg('Invalid JSON string in payload textarea.');
                  }
                }}
                disabled={verifying || !jsonInput.trim() || !sigInput.trim()}
                className="w-full py-2.5 rounded-lg bg-primary text-primary-foreground font-semibold hover:bg-primary/90 transition-colors disabled:opacity-50"
              >
                {verifying ? 'Verifying...' : 'Verify Cryptographic Signature'}
              </button>
            </div>
          )}
        </div>

        {errorMsg && (
          <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-600 dark:text-rose-400 text-xs flex items-center justify-between">
            <span>{errorMsg}</span>
            <button onClick={() => setErrorMsg(null)} className="font-bold">
              &times;
            </button>
          </div>
        )}

        {/* Verification Result Card */}
        {result && (
          <div
            className={`bg-card border rounded-2xl shadow-xl p-6 space-y-4 animate-in fade-in duration-200 ${
              result.status === 'VALID'
                ? 'border-emerald-500/50'
                : result.status === 'TAMPERED'
                ? 'border-rose-500/50 bg-rose-500/5'
                : result.status === 'REVOKED'
                ? 'border-amber-500/50 bg-amber-500/5'
                : 'border-border'
            }`}
          >
            {/* Status Heading */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border pb-4">
              <div className="flex items-center space-x-3">
                {result.status === 'VALID' ? (
                  <div className="w-12 h-12 rounded-xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex items-center justify-center shrink-0">
                    <CheckCircle2 className="h-7 w-7" />
                  </div>
                ) : result.status === 'TAMPERED' ? (
                  <div className="w-12 h-12 rounded-xl bg-rose-500/10 text-rose-600 dark:text-rose-400 flex items-center justify-center shrink-0">
                    <XCircle className="h-7 w-7" />
                  </div>
                ) : (
                  <div className="w-12 h-12 rounded-xl bg-amber-500/10 text-amber-600 dark:text-amber-400 flex items-center justify-center shrink-0">
                    <AlertTriangle className="h-7 w-7" />
                  </div>
                )}

                <div>
                  <div className="flex items-center space-x-2">
                    <span
                      className={`text-base font-extrabold font-mono tracking-wider px-2.5 py-0.5 rounded ${
                        result.status === 'VALID'
                          ? 'bg-emerald-500/20 text-emerald-600 dark:text-emerald-400'
                          : result.status === 'TAMPERED'
                          ? 'bg-rose-500/20 text-rose-600 dark:text-rose-400'
                          : 'bg-amber-500/20 text-amber-600 dark:text-amber-400'
                      }`}
                    >
                      {result.status}
                    </span>
                    <span className="text-xs text-muted-foreground">{result.message}</span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Verified at {formatDate(result.verified_at)}
                  </p>
                </div>
              </div>

              {/* Tamper test trigger button if certificate is valid */}
              {result.status === 'VALID' && (
                <button
                  onClick={handleTamperTest}
                  title="Simulates an attacker modifying 1 byte in the payload to prove cryptographic tamper detection"
                  className="px-3 py-1.5 rounded-lg border border-rose-500/40 text-rose-600 dark:text-rose-400 hover:bg-rose-500/10 text-xs font-semibold flex items-center gap-1.5 transition-colors"
                >
                  <RefreshCw className="h-3.5 w-3.5" />
                  <span>Test Tamper Detection</span>
                </button>
              )}
            </div>

            {/* Cryptographic Proof Details */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs font-mono">
              <div className="p-3 bg-muted/40 rounded-lg">
                <span className="text-[10px] text-muted-foreground block font-sans">Signing Key ID</span>
                <span className="font-bold text-foreground">{result.public_key_id || 'Active Platform Key'}</span>
              </div>
              <div className="p-3 bg-muted/40 rounded-lg">
                <span className="text-[10px] text-muted-foreground block font-sans">Cryptographic Algorithm</span>
                <span className="font-bold text-foreground">Ed25519 (RFC 8032) + SHA-256</span>
              </div>
            </div>

            {/* Verified Payload Details */}
            {result.payload && (
              <div className="space-y-2 pt-2 border-t border-border">
                <h4 className="text-xs font-bold text-foreground font-sans">Inspected Certificate Contents:</h4>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-[11px] font-mono">
                  <div>
                    <span className="text-muted-foreground text-[10px] block">Device Category:</span>
                    <span className="font-bold text-foreground">{result.payload.device_category || 'N/A'}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground text-[10px] block">Sanitization Method:</span>
                    <span className="font-bold text-foreground">{result.payload.method || 'NIST CLEAR'}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground text-[10px] block">Hashed Serial:</span>
                    <span className="font-bold text-foreground truncate block">
                      {result.payload.device_serial_hash?.slice(0, 16)}...
                    </span>
                  </div>
                </div>

                <div className="mt-3">
                  <span className="text-[10px] text-muted-foreground block mb-1">Canonical JSON Payload:</span>
                  <pre className="p-3 rounded-lg bg-slate-950 text-slate-100 font-mono text-[10px] max-h-40 overflow-y-auto">
                    {JSON.stringify(result.payload, null, 2)}
                  </pre>
                </div>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
};
