import React, { useState } from 'react';
import { Download, Loader2 } from 'lucide-react';
import { api } from '../../lib/api';
import { cn } from '../../lib/utils';

export const DownloadCertificateButton: React.FC<{ certificateId: string; compact?: boolean; className?: string }> = ({
  certificateId,
  compact = false,
  className,
}) => {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const download = async () => {
    setBusy(true);
    setError(null);
    try {
      await api.downloadCertificatePdf(certificateId);
    } catch (err: any) {
      setError(err.message || 'Download failed');
    } finally {
      setBusy(false);
    }
  };

  return (
    <span className="inline-flex flex-col items-end">
      <button
        onClick={download}
        disabled={busy}
        title={`Download ${certificateId}.pdf`}
        className={cn(
          'inline-flex items-center gap-1.5 rounded-lg font-semibold bg-emerald-600 text-white hover:bg-emerald-700 transition-colors disabled:opacity-60 shadow-sm',
          compact ? 'px-2.5 py-1 text-[11px]' : 'px-3.5 py-2 text-xs',
          className
        )}
      >
        {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />}
        <span>{compact ? 'PDF' : 'Download certificate'}</span>
      </button>
      {error && <span className="text-[10px] text-rose-600 mt-1">{error}</span>}
    </span>
  );
};
