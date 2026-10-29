import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Search,
  Filter,
  Plus,
  LayoutGrid,
  List as ListIcon,
  HardDrive,
  Cpu,
  ShieldAlert,
  ArrowRight,
  CheckCircle2,
} from 'lucide-react';
import { api } from '../lib/api';
import { Device, DeviceCategory } from '../types';
import { CategoryIcon } from '../components/common/CategoryIcon';
import { StatusBadge } from '../components/common/StatusBadge';
import { LoadingSkeleton } from '../components/common/LoadingSkeleton';
import { AddDeviceModal } from './AddDeviceModal';
import { useAuthStore } from '../store/authStore';
import { certStatusLabel } from '../lib/roles';

export const DevicesPage: React.FC = () => {
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string>('');
  const [viewMode, setViewMode] = useState<'table' | 'grid'>('table');
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);

  const navigate = useNavigate();
  const { user } = useAuthStore();

  const fetchDevices = async () => {
    try {
      const data = await api.getDevices();
      setDevices(data);
    } catch {
      // Error fetching devices
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDevices();
  }, []);

  const filtered = devices.filter((d) => {
    const matchesSearch =
      searchTerm === '' ||
      d.manufacturer.toLowerCase().includes(searchTerm.toLowerCase()) ||
      d.model.toLowerCase().includes(searchTerm.toLowerCase()) ||
      d.serial_number.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (d.os_name && d.os_name.toLowerCase().includes(searchTerm.toLowerCase()));

    const matchesCategory = categoryFilter === '' || d.category === categoryFilter;
    return matchesSearch && matchesCategory;
  });

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header & Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight text-foreground">Office Devices</h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            {user?.role === 'ADMIN'
              ? 'Every office device registered for certified wiping. Add devices manually, by browser detection, or by CSV.'
              : 'Open a device to see its details and request a wipe certificate.'}
          </p>
        </div>
        <div className="flex items-center space-x-3">
          {user?.role === 'ADMIN' && (
          <button
            onClick={() => setIsAddModalOpen(true)}
            className="flex items-center space-x-2 px-3.5 py-2 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors shadow-sm"
          >
            <Plus className="h-4 w-4" />
            <span>Add Device</span>
          </button>
          )}
        </div>
      </div>

      {/* Search & Filter Toolbar */}
      <div className="bg-card border border-border p-4 rounded-xl shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex flex-1 items-center gap-3">
          <div className="relative flex-1 max-w-md">
            <Search className="h-4 w-4 absolute left-3 top-2.5 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search by manufacturer, model, serial..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-4 py-2 text-xs bg-background border border-border rounded-lg focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>

          <div className="flex items-center space-x-2 text-xs">
            <Filter className="h-4 w-4 text-muted-foreground" />
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="px-3 py-2 bg-background border border-border rounded-lg text-xs"
            >
              <option value="">All Categories ({devices.length})</option>
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
              ].map((c) => (
                <option key={c} value={c}>
                  {c.replace(/_/g, ' ')}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="flex items-center space-x-1 border border-border rounded-lg p-1 bg-muted/40">
          <button
            onClick={() => setViewMode('table')}
            className={`p-1.5 rounded ${viewMode === 'table' ? 'bg-card text-foreground shadow-sm' : 'text-muted-foreground'}`}
            title="Table View"
          >
            <ListIcon className="h-4 w-4" />
          </button>
          <button
            onClick={() => setViewMode('grid')}
            className={`p-1.5 rounded ${viewMode === 'grid' ? 'bg-card text-foreground shadow-sm' : 'text-muted-foreground'}`}
            title="Grid View"
          >
            <LayoutGrid className="h-4 w-4" />
          </button>
        </div>
      </div>

      {loading ? (
        <LoadingSkeleton count={5} className="h-16" />
      ) : filtered.length === 0 ? (
        <div className="p-12 text-center bg-card border border-border rounded-xl">
          <HardDrive className="h-8 w-8 text-muted-foreground mx-auto mb-2 opacity-50" />
          <p className="text-sm font-semibold text-foreground">No devices match your filter</p>
          <p className="text-xs text-muted-foreground mt-1">Try clearing search terms or adding a new device</p>
        </div>
      ) : viewMode === 'table' ? (
        /* Table View */
        <div className="bg-card border border-border rounded-xl shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-muted/50 border-b border-border text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
                <tr>
                  <th className="px-5 py-3">Device Identity</th>
                  <th className="px-5 py-3">Category</th>
                  <th className="px-5 py-3">Operating System</th>
                  <th className="px-5 py-3">Serial / UUID</th>
                  <th className="px-5 py-3">Detection</th>
                  <th className="px-5 py-3">Status</th>
                  <th className="px-5 py-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60">
                {filtered.map((d) => (
                  <tr
                    key={d.id}
                    onClick={() => navigate(`/devices/${d.id}`)}
                    className="hover:bg-muted/30 transition-colors cursor-pointer group"
                  >
                    <td className="px-5 py-3.5">
                      <div className="flex items-center space-x-3">
                        <div className="w-9 h-9 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0">
                          <CategoryIcon category={d.category} className="h-5 w-5" />
                        </div>
                        <div>
                          <div className="font-bold text-foreground group-hover:text-primary transition-colors">
                            {d.manufacturer} {d.model}
                          </div>
                          <div className="text-[11px] text-muted-foreground font-mono">{d.hostname || 'standalone'}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-5 py-3.5">
                      <span className="font-mono text-[11px] font-semibold text-foreground">
                        {d.category.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td className="px-5 py-3.5">
                      <div className="text-foreground">{d.os_name || d.os_family || '—'}</div>
                      <div className="text-[10px] text-muted-foreground font-mono">{d.cpu_arch || 'x86_64'}</div>
                    </td>
                    <td className="px-5 py-3.5 font-mono text-[11px] text-foreground">
                      {d.serial_number}
                    </td>
                    <td className="px-5 py-3.5">
                      <div className="flex items-center gap-1.5">
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-muted text-muted-foreground">
                          {d.detected_by || 'AGENT'}
                        </span>
                        {d.detection_confidence && (
                          <span className="text-[10px] font-mono text-emerald-600 dark:text-emerald-400 font-bold">
                            {Math.round(d.detection_confidence * 100)}%
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-5 py-3.5">
                      <StatusBadge status={d.wipe_status || 'NONE'} label={certStatusLabel(d.wipe_status)} />
                    </td>
                    <td className="px-5 py-3.5 text-right">
                      <span className="text-primary font-semibold text-xs inline-flex items-center gap-1 group-hover:translate-x-1 transition-transform">
                        <span>Inspect</span>
                        <ArrowRight className="h-3.5 w-3.5" />
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        /* Grid View */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((d) => (
            <div
              key={d.id}
              onClick={() => navigate(`/devices/${d.id}`)}
              className="bg-card border border-border p-5 rounded-xl shadow-sm hover:border-primary/50 transition-all cursor-pointer flex flex-col justify-between group"
            >
              <div>
                <div className="flex items-start justify-between">
                  <div className="w-10 h-10 rounded-xl bg-primary/10 text-primary flex items-center justify-center">
                    <CategoryIcon category={d.category} className="h-5 w-5" />
                  </div>
                  <StatusBadge status={d.wipe_status || 'NONE'} label={certStatusLabel(d.wipe_status)} />
                </div>
                <div className="mt-3">
                  <h3 className="font-bold text-sm text-foreground group-hover:text-primary transition-colors">
                    {d.manufacturer} {d.model}
                  </h3>
                  <p className="text-[11px] text-muted-foreground font-mono mt-0.5">{d.serial_number}</p>
                </div>

                <div className="mt-4 pt-3 border-t border-border/50 grid grid-cols-2 gap-2 text-[11px]">
                  <div>
                    <span className="text-muted-foreground text-[10px] block">OS</span>
                    <span className="font-medium text-foreground truncate block">{d.os_name || '—'}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground text-[10px] block">Confidence</span>
                    <span className="font-mono text-emerald-600 dark:text-emerald-400 font-bold">
                      {Math.round((d.detection_confidence || 1.0) * 100)}%
                    </span>
                  </div>
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-border flex items-center justify-between text-xs">
                <span className="text-[11px] font-mono text-muted-foreground">{d.category}</span>
                <span className="text-primary font-semibold flex items-center gap-1">
                  View Volumes <ArrowRight className="h-3 w-3" />
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add Device Modal */}
      <AddDeviceModal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        onCreated={() => fetchDevices()}
      />
    </div>
  );
};
