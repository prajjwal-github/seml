import React, { useState, useEffect } from 'react';
import {
  X,
  Compass,
  FileSpreadsheet,
  PlusCircle,
  AlertCircle,
  CheckCircle2,
  HardDrive,
  Info,
} from 'lucide-react';
import { api } from '../lib/api';
import { DeviceCategory } from '../types';

interface AddDeviceModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreated: () => void;
}

export const AddDeviceModal: React.FC<AddDeviceModalProps> = ({ isOpen, onClose, onCreated }) => {
  const [activeTab, setActiveTab] = useState<'browser' | 'manual' | 'csv'>('browser');
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Browser detection state
  const [detectedInfo, setDetectedInfo] = useState<{
    manufacturer: string;
    model: string;
    category: DeviceCategory;
    os: string;
    confidence: number;
  }>({
    manufacturer: 'Generic',
    model: 'PC',
    category: 'DESKTOP',
    os: 'Windows',
    confidence: 0.7,
  });

  // Manual form state
  const [manualForm, setManualForm] = useState({
    manufacturer: '',
    model: '',
    serial_number: '',
    category: 'LAPTOP' as DeviceCategory,
    os_name: 'Windows 11 Pro',
    storage_size_gb: 512,
    storage_type: 'NVME_SSD',
  });

  // CSV content
  const [csvContent, setCsvContent] = useState(
    `category,manufacturer,model,serial_number,os_name,storage_media_type,storage_size_gb
LAPTOP,Dell,Latitude 5430,DELL-LAT-8849,Windows 11,NVME_SSD,512
SERVER,Supermicro,SYS-2029U,SM-2029-4412,Ubuntu Server,SATA_SSD,1920
PHONE,Google,Pixel 7a,GOOG-PX7A-3991,Android 14,UFS,128`
  );

  useEffect(() => {
    if (!isOpen) return;
    // Perform browser detection
    try {
      const ua = navigator.userAgent;
      let cat: DeviceCategory = 'DESKTOP';
      let os = 'Unknown OS';
      let mfg = 'Unknown Vendor';
      let model = 'Browser Device';
      let conf = 0.65;

      if (/Android/i.test(ua)) {
        cat = 'PHONE';
        os = 'Android';
        mfg = 'Android Device';
        conf = 0.85;
      } else if (/iPhone/i.test(ua)) {
        cat = 'PHONE';
        os = 'iOS';
        mfg = 'Apple';
        model = 'iPhone';
        conf = 0.9;
      } else if (/iPad/i.test(ua)) {
        cat = 'TABLET';
        os = 'iPadOS';
        mfg = 'Apple';
        model = 'iPad';
        conf = 0.9;
      } else if (/Macintosh|Mac OS X/i.test(ua)) {
        cat = 'LAPTOP';
        os = 'macOS';
        mfg = 'Apple';
        model = 'MacBook';
        conf = 0.8;
      } else if (/Windows/i.test(ua)) {
        cat = 'LAPTOP';
        os = 'Windows';
        mfg = 'PC';
        model = 'Workstation';
        conf = 0.75;
      } else if (/Linux/i.test(ua)) {
        cat = 'DESKTOP';
        os = 'Linux';
        conf = 0.7;
      }

      // Check userAgentData if available
      const navAny = navigator as any;
      if (navAny.userAgentData) {
        if (navAny.userAgentData.mobile) {
          cat = 'PHONE';
        }
        if (navAny.userAgentData.platform) {
          os = navAny.userAgentData.platform;
        }
      }

      setDetectedInfo({
        manufacturer: mfg,
        model,
        category: cat,
        os,
        confidence: conf,
      });

      setManualForm((prev) => ({
        ...prev,
        manufacturer: mfg,
        model,
        category: cat,
        os_name: os,
        serial_number: `BRW-${cat.slice(0, 3)}-${Math.random().toString(36).substring(2, 8).toUpperCase()}`,
      }));
    } catch {
      // Fallback
    }

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handleRegisterBrowserDevice = async () => {
    setSubmitting(true);
    setErrorMsg(null);
    try {
      const payload = {
        category: detectedInfo.category,
        manufacturer: detectedInfo.manufacturer,
        model: detectedInfo.model,
        serial_number: `BROWSER-${Math.random().toString(36).substring(2, 10).toUpperCase()}`,
        os_name: detectedInfo.os,
        detected_by: 'BROWSER_USERAGENT',
        detection_confidence: detectedInfo.confidence,
        volumes: [
          {
            name: 'Primary Volume (Simulated)',
            media_type: 'NVME_SSD',
            size_bytes: 256 * 1024 * 1024 * 1024,
            is_system: true,
            removable: false,
          },
        ],
      };
      await api.createDevice(payload);
      setSuccessMsg('Browser-detected device registered successfully!');
      setTimeout(() => {
        onCreated();
        onClose();
      }, 800);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to register browser device');
    } finally {
      setSubmitting(false);
    }
  };

  const handleManualSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setErrorMsg(null);
    try {
      const payload = {
        category: manualForm.category,
        manufacturer: manualForm.manufacturer,
        model: manualForm.model,
        serial_number: manualForm.serial_number,
        os_name: manualForm.os_name,
        detected_by: 'MANUAL_ENTRY',
        detection_confidence: 1.0,
        volumes: [
          {
            name: 'System Disk',
            media_type: manualForm.storage_type,
            size_bytes: manualForm.storage_size_gb * 1024 * 1024 * 1024,
            is_system: true,
            removable: false,
          },
        ],
      };
      await api.createDevice(payload);
      setSuccessMsg('Device created successfully!');
      setTimeout(() => {
        onCreated();
        onClose();
      }, 800);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to create device');
    } finally {
      setSubmitting(false);
    }
  };

  const handleCsvSubmit = async () => {
    setSubmitting(true);
    setErrorMsg(null);
    try {
      const res = await api.importDevicesCsv(csvContent);
      setSuccessMsg(`Successfully imported ${Array.isArray(res) ? res.length : 'all'} devices!`);
      setTimeout(() => {
        onCreated();
        onClose();
      }, 900);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to import CSV');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <div className="bg-card border border-border rounded-2xl shadow-2xl w-full max-w-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        <div className="p-5 border-b border-border flex items-center justify-between">
          <div>
            <h3 className="text-base font-bold text-foreground">Add New Device</h3>
            <p className="text-xs text-muted-foreground">Register assets via browser detection, manual specs, or CSV bulk import</p>
          </div>
          <button onClick={onClose} className="p-1 rounded-lg text-muted-foreground hover:bg-muted">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Tab selection */}
        <div className="flex border-b border-border bg-muted/30 px-5 text-xs font-semibold">
          <button
            onClick={() => setActiveTab('browser')}
            className={`py-3 px-4 border-b-2 flex items-center gap-2 transition-colors ${
              activeTab === 'browser'
                ? 'border-primary text-primary font-bold'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
          >
            <Compass className="h-4 w-4" />
            <span>Browser Auto-Detect</span>
          </button>
          <button
            onClick={() => setActiveTab('manual')}
            className={`py-3 px-4 border-b-2 flex items-center gap-2 transition-colors ${
              activeTab === 'manual'
                ? 'border-primary text-primary font-bold'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
          >
            <PlusCircle className="h-4 w-4" />
            <span>Manual Form</span>
          </button>
          <button
            onClick={() => setActiveTab('csv')}
            className={`py-3 px-4 border-b-2 flex items-center gap-2 transition-colors ${
              activeTab === 'csv'
                ? 'border-primary text-primary font-bold'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
          >
            <FileSpreadsheet className="h-4 w-4" />
            <span>CSV Bulk Import</span>
          </button>
        </div>

        <div className="p-6">
          {errorMsg && (
            <div className="mb-4 p-3 text-xs bg-rose-500/10 border border-rose-500/30 text-rose-600 dark:text-rose-400 rounded-lg flex items-center gap-2">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}
          {successMsg && (
            <div className="mb-4 p-3 text-xs bg-emerald-500/10 border border-emerald-500/30 text-emerald-600 dark:text-emerald-400 rounded-lg flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 shrink-0" />
              <span>{successMsg}</span>
            </div>
          )}

          {activeTab === 'browser' && (
            <div className="space-y-4 text-xs">
              <div className="p-4 rounded-xl bg-blue-500/5 border border-blue-500/20">
                <div className="flex items-start gap-3">
                  <div className="p-2 rounded-lg bg-blue-500/10 text-blue-600 dark:text-blue-400 shrink-0">
                    <Compass className="h-5 w-5" />
                  </div>
                  <div>
                    <h4 className="font-bold text-foreground text-sm">Client Machine Identification</h4>
                    <p className="text-muted-foreground mt-0.5">
                      Identified via <code className="font-mono text-primary">navigator.userAgentData</code> and high-entropy platform hints.
                    </p>
                  </div>
                </div>

                <div className="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono text-[11px] pt-3 border-t border-border/40">
                  <div>
                    <span className="text-muted-foreground block text-[10px]">Manufacturer</span>
                    <span className="font-bold text-foreground">{detectedInfo.manufacturer}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground block text-[10px]">Model / Family</span>
                    <span className="font-bold text-foreground">{detectedInfo.model}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground block text-[10px]">Classified Category</span>
                    <span className="font-bold text-primary">{detectedInfo.category}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground block text-[10px]">Confidence</span>
                    <span className="font-bold text-emerald-600 dark:text-emerald-400">
                      {Math.round(detectedInfo.confidence * 100)}%
                    </span>
                  </div>
                </div>
              </div>

              {/* Hardware Access Disclaimer */}
              <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-800 dark:text-amber-300 text-[11px] flex items-start gap-2">
                <Info className="h-4 w-4 shrink-0 mt-0.5" />
                <p>
                  <strong>Browser Sandbox Boundary:</strong> Web browsers cannot enumerate physical block devices, serial numbers, or drive partitions. For full storage inventory and SMART telemetry, deploy the lightweight, read-only <code className="font-mono font-bold">wipe-agent</code>.
                </p>
              </div>

              <button
                onClick={handleRegisterBrowserDevice}
                disabled={submitting}
                className="w-full py-2.5 px-4 rounded-lg bg-primary text-primary-foreground font-semibold hover:bg-primary/90 transition-colors disabled:opacity-50"
              >
                {submitting ? 'Registering...' : 'Register Detected Device to Inventory'}
              </button>
            </div>
          )}

          {activeTab === 'manual' && (
            <form onSubmit={handleManualSubmit} className="space-y-4 text-xs">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block font-medium text-foreground mb-1">Manufacturer</label>
                  <input
                    type="text"
                    required
                    value={manualForm.manufacturer}
                    onChange={(e) => setManualForm({ ...manualForm, manufacturer: e.target.value })}
                    placeholder="e.g. Lenovo, Dell, Apple"
                    className="w-full px-3 py-2 bg-background border border-border rounded-lg text-xs"
                  />
                </div>
                <div>
                  <label className="block font-medium text-foreground mb-1">Model Name</label>
                  <input
                    type="text"
                    required
                    value={manualForm.model}
                    onChange={(e) => setManualForm({ ...manualForm, model: e.target.value })}
                    placeholder="e.g. ThinkPad T14 Gen 3"
                    className="w-full px-3 py-2 bg-background border border-border rounded-lg text-xs"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block font-medium text-foreground mb-1">Serial Number</label>
                  <input
                    type="text"
                    required
                    value={manualForm.serial_number}
                    onChange={(e) => setManualForm({ ...manualForm, serial_number: e.target.value })}
                    placeholder="e.g. PF-99482-US"
                    className="w-full px-3 py-2 bg-background border border-border rounded-lg text-xs font-mono"
                  />
                </div>
                <div>
                  <label className="block font-medium text-foreground mb-1">Device Category</label>
                  <select
                    value={manualForm.category}
                    onChange={(e) => setManualForm({ ...manualForm, category: e.target.value as DeviceCategory })}
                    className="w-full px-3 py-2 bg-background border border-border rounded-lg text-xs"
                  >
                    {[
                      'LAPTOP',
                      'DESKTOP',
                      'WORKSTATION',
                      'SERVER',
                      'PHONE',
                      'TABLET',
                      'ALL_IN_ONE',
                      'SMART_TV',
                      'SINGLE_BOARD_COMPUTER',
                      'EXTERNAL_DRIVE',
                      'USB_FLASH',
                      'SD_CARD',
                      'NETWORK_DEVICE',
                      'OTHER',
                    ].map((cat) => (
                      <option key={cat} value={cat}>
                        {cat}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="block font-medium text-foreground mb-1">Operating System</label>
                  <input
                    type="text"
                    value={manualForm.os_name}
                    onChange={(e) => setManualForm({ ...manualForm, os_name: e.target.value })}
                    className="w-full px-3 py-2 bg-background border border-border rounded-lg text-xs"
                  />
                </div>
                <div>
                  <label className="block font-medium text-foreground mb-1">Storage Media</label>
                  <select
                    value={manualForm.storage_type}
                    onChange={(e) => setManualForm({ ...manualForm, storage_type: e.target.value })}
                    className="w-full px-3 py-2 bg-background border border-border rounded-lg text-xs"
                  >
                    <option value="NVME_SSD">NVMe SSD</option>
                    <option value="SATA_SSD">SATA SSD</option>
                    <option value="HDD">HDD (Mechanical)</option>
                    <option value="EMMC">eMMC</option>
                    <option value="UFS">UFS (phones / tablets)</option>
                    <option value="USB_FLASH">USB Flash</option>
                    <option value="SD_CARD">SD Card</option>
                  </select>
                </div>
                <div>
                  <label className="block font-medium text-foreground mb-1">Storage Size (GB)</label>
                  <input
                    type="number"
                    value={manualForm.storage_size_gb}
                    onChange={(e) => setManualForm({ ...manualForm, storage_size_gb: Number(e.target.value) })}
                    className="w-full px-3 py-2 bg-background border border-border rounded-lg text-xs"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={submitting}
                className="w-full py-2.5 px-4 rounded-lg bg-primary text-primary-foreground font-semibold hover:bg-primary/90 transition-colors disabled:opacity-50 mt-4"
              >
                {submitting ? 'Creating Device...' : 'Save Device to Inventory'}
              </button>
            </form>
          )}

          {activeTab === 'csv' && (
            <div className="space-y-4 text-xs">
              <p className="text-muted-foreground">
                Paste CSV text with columns: <code className="font-mono text-primary font-semibold">category, manufacturer, model, serial_number, os_name, storage_media_type, storage_size_gb</code>
              </p>
              <textarea
                rows={7}
                value={csvContent}
                onChange={(e) => setCsvContent(e.target.value)}
                className="w-full p-3 font-mono text-[11px] bg-background border border-border rounded-lg focus:outline-none focus:ring-1 focus:ring-primary"
              />
              <button
                onClick={handleCsvSubmit}
                disabled={submitting}
                className="w-full py-2.5 px-4 rounded-lg bg-primary text-primary-foreground font-semibold hover:bg-primary/90 transition-colors disabled:opacity-50"
              >
                {submitting ? 'Importing CSV...' : 'Process and Import CSV'}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
