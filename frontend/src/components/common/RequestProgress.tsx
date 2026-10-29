import React from 'react';
import { Check, X } from 'lucide-react';
import { WipeRequest } from '../../types';
import { cn } from '../../lib/utils';

const STEPS = ['Requested', 'Approved', 'Data wiped', 'Certificate'];

/** Index of the step currently reached (0-based), or -1 for a stopped request. */
function reachedStep(r: WipeRequest): number {
  switch (r.status) {
    case 'PENDING_APPROVAL':
      return 0;
    case 'APPROVED':
    case 'QUEUED':
    case 'RUNNING':
    case 'VERIFYING':
      return 1;
    case 'COMPLETED':
      return r.certificate_id ? 3 : 2;
    default:
      return -1;
  }
}

/** Four-step tracker that shows where a certificate request is in its lifecycle. */
export const RequestProgress: React.FC<{ request: WipeRequest }> = ({ request }) => {
  const step = reachedStep(request);
  const stopped = step === -1;
  const wiping = ['QUEUED', 'RUNNING', 'VERIFYING', 'APPROVED'].includes(request.status);
  const pct = Math.round(request.job_progress ?? 0);

  return (
    <div className="space-y-2">
      <div className="flex items-center">
        {STEPS.map((label, i) => {
          const done = !stopped && i <= step;
          const failedHere = stopped && i === 1;
          return (
            <React.Fragment key={label}>
              <div className="flex flex-col items-center min-w-[64px]">
                <div
                  className={cn(
                    'w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold border transition-colors',
                    done && 'bg-emerald-500 border-emerald-500 text-white',
                    failedHere && 'bg-rose-500 border-rose-500 text-white',
                    !done && !failedHere && 'bg-muted border-border text-muted-foreground',
                    !stopped && i === step + 1 && wiping && 'border-blue-500 text-blue-600 animate-pulse'
                  )}
                >
                  {done ? <Check className="w-3.5 h-3.5" /> : failedHere ? <X className="w-3.5 h-3.5" /> : i + 1}
                </div>
                <span className="text-[10px] mt-1 text-muted-foreground whitespace-nowrap">{label}</span>
              </div>
              {i < STEPS.length - 1 && (
                <div
                  className={cn(
                    'flex-1 h-0.5 -mt-4 mx-1 rounded',
                    !stopped && i < step ? 'bg-emerald-500' : 'bg-border'
                  )}
                />
              )}
            </React.Fragment>
          );
        })}
      </div>
      {wiping && (
        <div>
          <div className="flex justify-between text-[10px] text-muted-foreground mb-1">
            <span>{request.status === 'VERIFYING' ? 'Verifying wipe…' : 'Wiping storage (simulation)…'}</span>
            <span className="font-mono">{pct}%</span>
          </div>
          <div className="w-full bg-muted h-1.5 rounded-full overflow-hidden">
            <div className="bg-blue-500 h-1.5 transition-all duration-500" style={{ width: `${Math.max(pct, 3)}%` }} />
          </div>
        </div>
      )}
    </div>
  );
};
