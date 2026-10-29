import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  ArrowLeft,
  HardDrive,
  Cpu,
  ShieldCheck,
  ShieldAlert,
  Lock,
  Unlock,
  AlertTriangle,
  Play,
  FileCheck2,
  Clock,
  CheckCircle2,
} from 'lucide-react';
import { api } from '../lib/api';
import { Device, StorageVolume, WipeRequest, Certificate } from '../types';
import { CategoryIcon } from '../components/common/CategoryIcon';
import { StatusBadge } from '../components/common/StatusBadge';
import { LoadingSkeleton } from '../components/common/LoadingSkeleton';
import { WipeRequestWizardModal } from './WipeRequestWizardModal';
import { formatBytes, formatDate } from '../lib/utils';
import { useAuthStore } from '../store/authStore';
import { ACTIVE_STATUSES, certStatusLabel, formatMethod } from '../lib/roles';
import { useLiveRefresh } from '../lib/useLiveRefresh';
import { RequestProgress } from '../components/common/RequestProgress';
import { DownloadCertificateButton } from '../components/common/DownloadCertificateButton';

export const DeviceDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuthStore();

  const [device, setDevice] = useState<Device | null>(null);
  const [requests, setRequests] = useState<WipeRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [isWizardOpen, setIsWizardOpen] = useState(false);
  const [createdRequestId, setCreatedRequestId] = useState<string | null>(null);

  const fetchDeviceData = async () => {
    if (!id) return;
    try {
      const data = await api.getDevice(id);
      setDevice(data);
      const allReqs = await api.getWipeRequests();
      setRequests(allReqs.filter((r: WipeRequest) => r.device_id === id));
    } catch {
      // Failed to load device
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDeviceData();
  }, [id]);

  useLiveRefresh(fetchDeviceData, requests.some((r) => ACTIVE_STATUSES.includes(r.status)));

  if (loading || !device) {
    return (
      <div className="space-y-6 max-w-5xl mx-auto">
        <LoadingSkeleton count={3} className="h-32" />
      </div>
    );
  }

  const activeRequest = requests.find((r) => ACTIVE_STATUSES.includes(r.status));
  const latestStatus = requests[0]?.status ?? 'NONE';

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Back Link & Header */}
      <div>
        <Link
          to="/devices"
          className="inline-flex items-center space-x-1.5 text-xs text-muted-foreground hover:text-foreground mb-3 transition-colors"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          <span>Back to devices</span>
        </Link>

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center space-x-3.5">
            <div className="w-12 h-12 rounded-2xl bg-primary/10 text-primary flex items-center justify-center shadow-sm">
              <CategoryIcon category={device.category} className="h-6 w-6" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h1 className="text-xl font-extrabold text-foreground">
                  {device.manufacturer} {device.model}
                </h1>
                <StatusBadge status={latestStatus} label={certStatusLabel(latestStatus)} />
              </div>
              <p className="text-xs text-muted-foreground font-mono mt-0.5">
                Serial: {device.serial_number} | {device.category}
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            {user?.role === 'OPERATOR' &&
              (activeRequest ? (
                <Link
                  to="/dashboard"
                  className="flex items-center space-x-2 px-4 py-2 text-xs font-semibold rounded-lg bg-amber-500 text-slate-950 hover:bg-amber-600 transition-colors shadow-sm"
                >
                  <Clock className="h-4 w-4" />
                  <span>Track request: {certStatusLabel(activeRequest.status)}</span>
                </Link>
              ) : (
                <button
                  onClick={() => setIsWizardOpen(true)}
                  className="flex items-center space-x-2 px-4 py-2 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors shadow-sm"
                >
                  <ShieldAlert className="h-4 w-4" />
                  <span>Request wipe certificate</span>
                </button>
              ))}
            {user?.role === 'APPROVER' && activeRequest?.status === 'PENDING_APPROVAL' && (
              <Link
                to="/dashboard"
                className="flex items-center space-x-2 px-4 py-2 text-xs font-semibold rounded-lg bg-amber-500 text-slate-950 hover:bg-amber-600 transition-colors shadow-sm"
              >
                <Clock className="h-4 w-4" />
                <span>Review pending request</span>
              </Link>
            )}
          </div>
        </div>
      </div>

      {/* Success banner after request submission */}
      {createdRequestId && (
        <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-900 dark:text-amber-300 text-xs flex items-start gap-3">
          <Clock className="h-5 w-5 shrink-0 text-amber-600 mt-0.5" />
          <div className="space-y-1">
            <h4 className="font-bold">Certificate request submitted</h4>
            <p>
              Your request is now with the Approver. Once approved, the device is wiped and the signed certificate appears
              on your dashboard for download.
            </p>
            <Link to="/dashboard" className="font-semibold underline block pt-1">
              Go to my dashboard &rarr;
            </Link>
          </div>
        </div>
      )}

      {/* Hardware & Detection Metadata Card */}
      <div className="bg-card border border-border p-5 rounded-xl shadow-sm space-y-4">
        <h2 className="text-sm font-bold text-foreground">Hardware Specifications & Telemetry</h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs font-mono">
          <div className="p-3 bg-muted/40 rounded-lg border border-border/50">
            <span className="text-[10px] text-muted-foreground block font-sans">Operating System</span>
            <span className="font-bold text-foreground">{device.os_name || device.os_family || '—'}</span>
            <span className="text-[10px] text-muted-foreground block mt-0.5">{device.os_version || ''}</span>
          </div>
          <div className="p-3 bg-muted/40 rounded-lg border border-border/50">
            <span className="text-[10px] text-muted-foreground block font-sans">CPU Architecture</span>
            <span className="font-bold text-foreground">{device.cpu_arch || 'x86_64'}</span>
          </div>
          <div className="p-3 bg-muted/40 rounded-lg border border-border/50">
            <span className="text-[10px] text-muted-foreground block font-sans">BIOS / Boot Mode</span>
            <span className="font-bold text-foreground">{device.boot_mode || 'UEFI SecureBoot'}</span>
            <span className="text-[10px] text-muted-foreground block mt-0.5">{device.bios_vendor || 'OEM'}</span>
          </div>
          <div className="p-3 bg-muted/40 rounded-lg border border-border/50">
            <span className="text-[10px] text-muted-foreground block font-sans">Detection Confidence</span>
            <span className="font-bold text-emerald-600 dark:text-emerald-400">
              {Math.round((device.detection_confidence || 1.0) * 100)}%
            </span>
            <span className="text-[10px] text-muted-foreground block mt-0.5">by {device.detected_by || 'AGENT'}</span>
          </div>
        </div>
      </div>

      {/* Storage Volumes Inventory */}
      <div className="bg-card border border-border p-5 rounded-xl shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-bold text-foreground">Storage Inventory & Hidden Area Telemetry</h2>
            <p className="text-xs text-muted-foreground mt-0.5">
              Read-only inspection of physical blocks, hardware encryption, HPA/DCO, and over-provisioning.
            </p>
          </div>
          <span className="font-mono text-xs text-muted-foreground">{device.volumes?.length || 0} Volumes</span>
        </div>

        <div className="space-y-3">
          {(!device.volumes || device.volumes.length === 0) ? (
            <p className="text-xs text-muted-foreground py-4 text-center">No storage volumes detected.</p>
          ) : (
            device.volumes.map((vol) => (
              <div
                key={vol.id}
                className="p-4 rounded-xl border border-border/80 bg-background hover:border-primary/40 transition-colors text-xs space-y-3"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <div className="p-2 rounded-lg bg-muted text-primary shrink-0">
                      <HardDrive className="h-5 w-5" />
                    </div>
                    <div>
                      <div className="font-bold text-foreground text-sm flex items-center gap-2">
                        <span>{vol.name}</span>
                        {vol.is_system && (
                          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-rose-500/20 text-rose-600 dark:text-rose-400 font-semibold">
                            SYSTEM BOOT
                          </span>
                        )}
                        {vol.is_removable && (
                          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-600 dark:text-blue-400">
                            REMOVABLE
                          </span>
                        )}
                      </div>
                      <div className="text-[11px] text-muted-foreground font-mono mt-0.5">
                        Media: {vol.media_type} | Bus: {vol.bus_type || 'Internal'} | Model: {vol.model || 'OEM'}
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-mono font-bold text-sm text-foreground">{formatBytes(vol.size_bytes)}</div>
                    <div className="text-[10px] text-muted-foreground font-mono">
                      Serial: {vol.serial_number || 'N/A'}
                    </div>
                  </div>
                </div>

                {/* Security, Encryption, and Hidden Areas Indicators */}
                <div className="pt-2 border-t border-border/40 grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px]">
                  <div>
                    <span className="text-[10px] text-muted-foreground block">Encryption Status</span>
                    <span className="font-semibold text-foreground flex items-center gap-1 mt-0.5">
                      {vol.encryption_status && vol.encryption_status !== 'None' ? (
                        <>
                          <Lock className="h-3 w-3 text-emerald-500" />
                          <span>{vol.encryption_status}</span>
                        </>
                      ) : (
                        <>
                          <Unlock className="h-3 w-3 text-amber-500" />
                          <span>Unencrypted</span>
                        </>
                      )}
                    </span>
                  </div>

                  <div>
                    <span className="text-[10px] text-muted-foreground block">HPA / DCO Present</span>
                    <span className="font-mono text-foreground mt-0.5 block">
                      {vol.hidden_areas?.hpa_present || vol.hidden_areas?.dco_present ? (
                        <span className="text-amber-500 font-bold">YES (HPA/DCO Detected)</span>
                      ) : (
                        'None (Checked)'
                      )}
                    </span>
                  </div>

                  <div>
                    <span className="text-[10px] text-muted-foreground block">Over-Provisioning</span>
                    <span className="font-mono text-foreground mt-0.5 block">
                      {vol.hidden_areas?.over_provisioning_percent
                        ? `${vol.hidden_areas.over_provisioning_percent}% reserved`
                        : 'Standard'}
                    </span>
                  </div>

                  <div>
                    <span className="text-[10px] text-muted-foreground block">Remapped Sectors</span>
                    <span className="font-mono text-foreground mt-0.5 block">
                      {vol.hidden_areas?.remapped_sectors ?? 0} sectors
                    </span>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Wipe Requests & Audit History on this Device */}
      <div className="bg-card border border-border p-5 rounded-xl shadow-sm space-y-4">
        <h2 className="text-sm font-bold text-foreground">Certificate requests for this device</h2>
        {requests.length === 0 ? (
          <p className="text-xs text-muted-foreground py-3">No sanitization requests have been created for this device.</p>
        ) : (
          <div className="divide-y divide-border/60 text-xs">
            {requests.map((r) => (
              <div key={r.id} className="py-3 grid grid-cols-1 md:grid-cols-12 gap-3 items-center">
                <div className="md:col-span-5">
                  <div className="flex items-center space-x-2">
                    <span className="font-bold text-foreground">{formatMethod(r.method)}</span>
                    <StatusBadge status={r.status} label={certStatusLabel(r.status)} />
                  </div>
                  <p className="text-[11px] text-muted-foreground mt-0.5">
                    {r.requester_name} · {formatDate(r.created_at)} · Risk {r.risk_level}
                  </p>
                  {r.decision_comment && (
                    <p className="text-[11px] text-muted-foreground italic mt-0.5">
                      {r.approver_name}: “{r.decision_comment}”
                    </p>
                  )}
                </div>
                <div className="md:col-span-5">
                  <RequestProgress request={r} />
                </div>
                <div className="md:col-span-2 flex md:justify-end">
                  {r.certificate_id && <DownloadCertificateButton certificateId={r.certificate_id} compact />}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Wipe Request Wizard Modal */}
      <WipeRequestWizardModal
        device={device}
        isOpen={isWizardOpen}
        onClose={() => setIsWizardOpen(false)}
        onSuccess={(reqId) => {
          setCreatedRequestId(reqId);
          fetchDeviceData();
        }}
      />
    </div>
  );
};
