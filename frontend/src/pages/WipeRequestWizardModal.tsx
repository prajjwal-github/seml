import React, { useState } from 'react';
import {
  X,
  HardDrive,
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  Lock,
  ArrowRight,
  ArrowLeft,
  Info,
} from 'lucide-react';
import { api } from '../lib/api';
import { Device, StorageVolume, WipeMethod } from '../types';
import { formatBytes } from '../lib/utils';

interface WipeRequestWizardModalProps {
  device: Device;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (requestId: string) => void;
}

export const WipeRequestWizardModal: React.FC<WipeRequestWizardModalProps> = ({
  device,
  isOpen,
  onClose,
  onSuccess,
}) => {
  const [step, setStep] = useState<1 | 2 | 3 | 4>(1);
  const [selectedVolumes, setSelectedVolumes] = useState<string[]>(
    device.volumes ? device.volumes.map((v) => v.id) : []
  );
  const [method, setMethod] = useState<WipeMethod>('NIST_800_88_CLEAR');
  const [reason, setReason] = useState('Certified asset recycling / end-of-lifecycle sanitization.');
  const [serialConfirm, setSerialConfirm] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!isOpen) return null;

  // Determine risk
  const hasSystemVolume = device.volumes?.some((v) => selectedVolumes.includes(v.id) && v.is_system);
  const isHighRisk = hasSystemVolume || method === 'NIST_800_88_PURGE';

  const toggleVolume = (volId: string) => {
    setSelectedVolumes((prev) =>
      prev.includes(volId) ? prev.filter((id) => id !== volId) : [...prev, volId]
    );
  };

  const handleSubmit = async () => {
    if (serialConfirm.trim().toLowerCase() !== device.serial_number.trim().toLowerCase()) {
      setErrorMsg(`Typed serial does not match device serial (${device.serial_number})`);
      return;
    }

    setSubmitting(true);
    setErrorMsg(null);
    try {
      const res = await api.createWipeRequest({
        device_id: device.id,
        volume_ids: selectedVolumes,
        method,
        reason,
        confirm_serial: serialConfirm.trim(),
      });
      onSuccess(res.id);
      onClose();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to submit wipe request');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <div className="bg-card border border-border rounded-2xl shadow-2xl w-full max-w-xl overflow-hidden animate-in fade-in zoom-in-95 duration-150 flex flex-col max-h-[90vh]">
        {/* Modal Header */}
        <div className="p-5 border-b border-border flex items-center justify-between shrink-0">
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-primary/10 text-primary font-bold">
                Step {step} of 4
              </span>
              <h3 className="text-base font-bold text-foreground">Request Wipe Certificate</h3>
            </div>
            <p className="text-xs text-muted-foreground mt-0.5">
              {device.manufacturer} {device.model} ({device.serial_number})
            </p>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg text-muted-foreground hover:bg-muted">
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Wizard Progress Bar */}
        <div className="w-full bg-muted h-1 shrink-0">
          <div
            className="bg-primary h-1 transition-all duration-300"
            style={{ width: `${(step / 4) * 100}%` }}
          />
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto space-y-4 text-xs flex-1">
          {errorMsg && (
            <div className="p-3 text-xs bg-rose-500/10 border border-rose-500/30 text-rose-600 dark:text-rose-400 rounded-lg flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* STEP 1: Select Volumes */}
          {step === 1 && (
            <div className="space-y-3">
              <div>
                <h4 className="font-bold text-sm text-foreground">Select Storage Volumes to Sanitize</h4>
                <p className="text-muted-foreground mt-0.5">
                  Choose specific physical media or partitions targeted for certified sanitization.
                </p>
              </div>

              <div className="space-y-2 mt-3">
                {(!device.volumes || device.volumes.length === 0) ? (
                  <p className="text-muted-foreground py-4 text-center">No volumes detected on this device.</p>
                ) : (
                  device.volumes.map((v) => (
                    <label
                      key={v.id}
                      className={`flex items-center justify-between p-3.5 rounded-xl border cursor-pointer transition-all ${
                        selectedVolumes.includes(v.id)
                          ? 'border-primary bg-primary/5 text-foreground'
                          : 'border-border bg-background text-muted-foreground opacity-75'
                      }`}
                    >
                      <div className="flex items-center space-x-3">
                        <input
                          type="checkbox"
                          checked={selectedVolumes.includes(v.id)}
                          onChange={() => toggleVolume(v.id)}
                          className="h-4 w-4 rounded border-border text-primary focus:ring-primary"
                        />
                        <div>
                          <div className="font-bold text-foreground flex items-center gap-2">
                            <span>{v.name}</span>
                            {v.is_system && (
                              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-rose-500/20 text-rose-600 dark:text-rose-400 font-semibold">
                                SYSTEM
                              </span>
                            )}
                          </div>
                          <div className="text-[11px] text-muted-foreground font-mono mt-0.5">
                            {v.media_type} | {v.bus_type || 'Internal'} | {v.partition_table || 'GPT'}
                          </div>
                        </div>
                      </div>
                      <div className="text-right font-mono font-bold text-xs text-foreground">
                        {formatBytes(v.size_bytes)}
                      </div>
                    </label>
                  ))
                )}
              </div>
            </div>
          )}

          {/* STEP 2: Select Method */}
          {step === 2 && (
            <div className="space-y-3">
              <div>
                <h4 className="font-bold text-sm text-foreground">Select Sanitization Method</h4>
                <p className="text-muted-foreground mt-0.5">
                  Compliant with NIST SP 800-88 Rev. 1 Guidelines for Media Sanitization.
                </p>
              </div>

              <div className="grid grid-cols-1 gap-3 mt-3">
                <div
                  onClick={() => setMethod('NIST_800_88_CLEAR')}
                  className={`p-4 rounded-xl border cursor-pointer transition-all ${
                    method === 'NIST_800_88_CLEAR'
                      ? 'border-primary bg-primary/5 shadow-sm'
                      : 'border-border hover:bg-muted/40'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-sm text-foreground">NIST 800-88 Clear</span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-500/10 text-blue-600 font-semibold">
                      Standard Overwrite
                    </span>
                  </div>
                  <p className="text-muted-foreground mt-1 leading-relaxed">
                    Overwrites all user-accessible storage locations using logical writes with fixed or pseudo-random data. Suitable for internal reuse and reassignment.
                  </p>
                </div>

                <div
                  onClick={() => setMethod('NIST_800_88_PURGE')}
                  className={`p-4 rounded-xl border cursor-pointer transition-all ${
                    method === 'NIST_800_88_PURGE'
                      ? 'border-primary bg-primary/5 shadow-sm'
                      : 'border-border hover:bg-muted/40'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-sm text-foreground">NIST 800-88 Purge</span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-600 font-semibold">
                      Hardware Cryptographic Sanitize
                    </span>
                  </div>
                  <p className="text-muted-foreground mt-1 leading-relaxed">
                    Applies physical or cryptographic sanitization commands (ATA Secure Erase, NVMe Cryptographic Sanitize) rendering target data infeasible to recover even using advanced laboratory tools.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* STEP 3: Reason & Risk */}
          {step === 3 && (
            <div className="space-y-4">
              <div>
                <h4 className="font-bold text-sm text-foreground">Justification & Risk Assessment</h4>
                <p className="text-muted-foreground mt-0.5">
                  Provide regulatory or operational rationale for dual-custody approval.
                </p>
              </div>

              <div>
                <label className="block font-medium text-foreground mb-1">Written Business Reason</label>
                <textarea
                  rows={3}
                  required
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  className="w-full p-2.5 bg-background border border-border rounded-lg text-xs"
                />
              </div>

              <div className="p-3.5 rounded-xl border border-border bg-muted/30 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-foreground">Calculated Risk Level</span>
                  <span
                    className={`font-mono text-[11px] font-bold px-2 py-0.5 rounded uppercase ${
                      isHighRisk
                        ? 'bg-rose-500/20 text-rose-600 dark:text-rose-400'
                        : 'bg-emerald-500/20 text-emerald-600 dark:text-emerald-400'
                    }`}
                  >
                    {isHighRisk ? 'HIGH RISK' : 'LOW RISK'}
                  </span>
                </div>
                {isHighRisk ? (
                  <div className="text-[11px] text-rose-600 dark:text-rose-400 flex items-start gap-1.5">
                    <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
                    <span>
                      High risk: a system volume is selected or the Purge method was chosen. The Approver will see this
                      flag when reviewing your request.
                    </span>
                  </div>
                ) : (
                  <p className="text-[11px] text-muted-foreground">
                    Standard risk. The request goes to the Approver for a decision.
                  </p>
                )}
              </div>
            </div>
          )}

          {/* STEP 4: Confirm Serial */}
          {step === 4 && (
            <div className="space-y-4">
              <div>
                <h4 className="font-bold text-sm text-foreground">Confirm Device Serial Number</h4>
                <p className="text-muted-foreground mt-0.5">
                  To prevent accidental sanitization of unintended assets, manually type the serial number below.
                </p>
              </div>

              <div className="p-3.5 rounded-xl bg-muted/40 border border-border text-center">
                <span className="text-[11px] text-muted-foreground uppercase tracking-wider block">Target Device Serial</span>
                <span className="font-mono text-base font-extrabold text-foreground tracking-widest mt-1 block">
                  {device.serial_number}
                </span>
              </div>

              <div>
                <label className="block font-medium text-foreground mb-1">Type Serial to Confirm</label>
                <input
                  type="text"
                  required
                  placeholder={device.serial_number}
                  value={serialConfirm}
                  onChange={(e) => setSerialConfirm(e.target.value)}
                  className="w-full px-3 py-2 bg-background border border-border rounded-lg text-xs font-mono tracking-wider"
                />
              </div>

              <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-800 dark:text-amber-300 text-[11px] flex items-start gap-2">
                <Info className="h-4 w-4 shrink-0 mt-0.5" />
                <p>
                  <strong>What happens next:</strong> your request goes to the Approver. Nothing is wiped until it is
                  approved; after approval the wipe runs automatically and your signed PDF certificate appears on your
                  dashboard.
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer Controls */}
        <div className="p-4 border-t border-border bg-card flex items-center justify-between shrink-0">
          {step > 1 ? (
            <button
              onClick={() => setStep((s) => (s - 1) as any)}
              className="px-3.5 py-2 text-xs font-semibold rounded-lg border border-border hover:bg-muted transition-colors flex items-center gap-1.5"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              <span>Back</span>
            </button>
          ) : (
            <div />
          )}

          {step < 4 ? (
            <button
              onClick={() => {
                if (step === 1 && selectedVolumes.length === 0) {
                  setErrorMsg('Please select at least one volume');
                  return;
                }
                setErrorMsg(null);
                setStep((s) => (s + 1) as any);
              }}
              className="px-4 py-2 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors flex items-center gap-1.5"
            >
              <span>Next Step</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </button>
          ) : (
            <button
              onClick={handleSubmit}
              disabled={submitting || serialConfirm.trim() !== device.serial_number}
              className="px-4 py-2 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50 flex items-center gap-1.5"
            >
              <span>{submitting ? 'Submitting...' : 'Submit certificate request'}</span>
              <CheckCircle2 className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
