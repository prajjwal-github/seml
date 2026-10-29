import React from 'react';
import { ShieldAlert, AlertTriangle, Info } from 'lucide-react';

export const SimulationBanner: React.FC = () => {
  return (
    <div className="w-full bg-gradient-to-r from-amber-600 via-amber-500 to-amber-600 text-slate-950 px-4 py-2 text-xs font-semibold tracking-wide shadow-md flex items-center justify-between z-50 sticky top-0">
      <div className="flex items-center space-x-2">
        <span className="flex h-2 w-2 relative">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-black opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2 w-2 bg-black"></span>
        </span>
        <ShieldAlert className="h-4 w-4 text-black shrink-0" />
        <span className="uppercase tracking-wider font-extrabold text-[11px] sm:text-xs">
          SIMULATION MODE — No real data is erased
        </span>
        <span className="hidden md:inline text-black/80 font-normal">
          | Dual-Custody Gated Wiping & NIST SP 800-88 Rev. 1 Simulation Engine
        </span>
      </div>
      <div className="flex items-center space-x-3 text-[11px]">
        <span className="hidden sm:flex items-center gap-1 bg-black/10 px-2 py-0.5 rounded font-mono text-black border border-black/20">
          <Info className="h-3 w-3" />
          mode: simulation
        </span>
        <span className="bg-black text-amber-400 px-2 py-0.5 rounded font-mono font-bold text-[10px] tracking-widest uppercase">
          Read-Only / Zero Disruption
        </span>
      </div>
    </div>
  );
};
