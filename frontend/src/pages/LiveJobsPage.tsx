import React, { useState, useEffect } from 'react';
import {
  PlayCircle,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Terminal,
  Clock,
  HardDrive,
  ShieldCheck,
  RotateCcw,
  StopCircle,
} from 'lucide-react';
import { api } from '../lib/api';
import { wsClient } from '../lib/ws';
import { WipeJob, WipeRequest } from '../types';
import { StatusBadge } from '../components/common/StatusBadge';
import { LoadingSkeleton } from '../components/common/LoadingSkeleton';
import { formatDate } from '../lib/utils';

export const LiveJobsPage: React.FC = () => {
  const [jobs, setJobs] = useState<WipeJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedJob, setSelectedJob] = useState<WipeJob | null>(null);
  const [jobEvents, setJobEvents] = useState<any[]>([]);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const fetchJobsAndApproved = async () => {
    try {
      const allJobs = await api.getJobs();
      setJobs(allJobs);
      if (!selectedJob && allJobs.length > 0) {
        setSelectedJob(allJobs[0]);
      }
    } catch {
      // Failed to load jobs
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobsAndApproved();

    // Listen for WebSocket progress and status updates
    const unsubProgress = wsClient.on('job.progress', (msg) => {
      setJobs((prev) =>
        prev.map((j) =>
          j.id === msg.job_id
            ? { ...j, status: msg.status ?? j.status, progress: msg.progress, current_pass: msg.current_pass, total_passes: msg.total_passes }
            : j
        )
      );
      if (['COMPLETED', 'FAILED', 'CANCELLED', 'QUEUED'].includes(msg.status)) {
        fetchJobsAndApproved();
      }
      if (selectedJob && selectedJob.id === msg.job_id) {
        setJobEvents((prev) => [
          {
            id: Math.random().toString(),
            timestamp: new Date().toLocaleTimeString(),
            message: `Pass ${msg.current_pass}/${msg.total_passes} · ${msg.progress}% · ${msg.message || ''}`,
          },
          ...prev.slice(0, 49),
        ]);
      }
    });

    const unsubStatus = wsClient.on('job.status', (msg) => {
      setJobs((prev) =>
        prev.map((j) => (j.id === msg.job_id ? { ...j, status: msg.status } : j))
      );
      if (selectedJob && selectedJob.id === msg.job_id) {
        setJobEvents((prev) => [
          {
            id: Math.random().toString(),
            timestamp: new Date().toLocaleTimeString(),
            message: `State transition -> ${msg.status}`,
          },
          ...prev.slice(0, 49),
        ]);
      }
      fetchJobsAndApproved();
    });

    return () => {
      unsubProgress();
      unsubStatus();
    };
  }, [selectedJob]);

  const handleSelectJob = async (job: WipeJob) => {
    setSelectedJob(job);
    try {
      const events = await api.getJobEvents(job.id);
      setJobEvents(
        events.map((e: any) => ({
          id: e.id,
          timestamp: new Date(e.created_at).toLocaleTimeString(),
          message: `${e.event_type}: ${e.message}`,
        }))
      );
    } catch {
      setJobEvents([]);
    }
  };

  const handleCancel = async (jobId: string) => {
    try {
      await api.cancelJob(jobId);
      await fetchJobsAndApproved();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to cancel job');
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight text-foreground">Wipe Progress</h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            Approved requests start wiping automatically. Follow each pass live until the signed certificate is issued.
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <span className="text-[11px] font-mono px-2.5 py-1 rounded bg-amber-500/10 text-amber-600 dark:text-amber-400 font-bold border border-amber-500/20">
            SIMULATION ENGINE ACTIVE
          </span>
        </div>
      </div>

      {errorMsg && (
        <div className="p-3 text-xs bg-rose-500/10 border border-rose-500/30 text-rose-600 dark:text-rose-400 rounded-lg flex items-center justify-between">
          <span>{errorMsg}</span>
          <button onClick={() => setErrorMsg(null)} className="text-rose-600 font-bold ml-2">
            &times;
          </button>
        </div>
      )}

      {/* Main Jobs Layout: Left List, Right Live Console */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Job List */}
        <div className="bg-card border border-border rounded-xl p-4 shadow-sm space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-foreground">Jobs Queue & History</h2>
            <span className="text-xs text-muted-foreground font-mono">{jobs.length} jobs</span>
          </div>

          {loading ? (
            <LoadingSkeleton count={4} className="h-20" />
          ) : jobs.length === 0 ? (
            <p className="text-xs text-muted-foreground py-6 text-center">No wipe jobs recorded yet.</p>
          ) : (
            <div className="space-y-2 max-h-[600px] overflow-y-auto pr-1">
              {jobs.map((j) => (
                <div
                  key={j.id}
                  onClick={() => handleSelectJob(j)}
                  className={`p-3.5 rounded-xl border cursor-pointer transition-all ${
                    selectedJob?.id === j.id
                      ? 'border-primary bg-primary/5 shadow-sm'
                      : 'border-border/80 bg-background hover:bg-muted/40'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-xs text-foreground truncate max-w-[150px]">
                      {j.device_name || j.device_model || 'Device'}
                    </span>
                    <StatusBadge status={j.status} />
                  </div>
                  <div className="text-[11px] text-muted-foreground font-mono mt-1">
                    Pass {j.current_pass} of {j.total_passes} | Mode: {j.mode}
                  </div>

                  {/* Progress bar */}
                  <div className="w-full bg-muted rounded-full h-1.5 mt-2 overflow-hidden">
                    <div
                      className={`h-full transition-all duration-300 ${
                        j.status === 'COMPLETED'
                          ? 'bg-emerald-500'
                          : j.status === 'FAILED'
                          ? 'bg-rose-500'
                          : 'bg-primary'
                      }`}
                      style={{ width: `${j.progress}%` }}
                    />
                  </div>
                  <div className="flex justify-between items-center text-[10px] text-muted-foreground mt-1 font-mono">
                    <span>{j.progress}%</span>
                    <span>{formatDate(j.created_at)}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right: Selected Job Live Console & Details */}
        <div className="bg-card border border-border rounded-xl p-5 shadow-sm lg:col-span-2 space-y-4 flex flex-col justify-between">
          {selectedJob ? (
            <>
              <div className="space-y-3">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-border pb-3">
                  <div>
                    <div className="flex items-center space-x-2">
                      <h2 className="text-base font-bold text-foreground">
                        {selectedJob.device_name || selectedJob.device_model || 'Device'}
                      </h2>
                      <StatusBadge status={selectedJob.status} />
                    </div>
                    <p className="text-xs text-muted-foreground font-mono mt-0.5">
                      Job ID: {selectedJob.id} | Mode: {selectedJob.mode}
                    </p>
                  </div>

                  {['RUNNING', 'QUEUED'].includes(selectedJob.status) && (
                    <button
                      onClick={() => handleCancel(selectedJob.id)}
                      className="px-3 py-1.5 rounded-lg border border-rose-500/40 text-rose-600 dark:text-rose-400 text-xs font-semibold hover:bg-rose-500/10 transition-colors flex items-center gap-1.5"
                    >
                      <StopCircle className="h-3.5 w-3.5" />
                      <span>Abort / Cancel Job</span>
                    </button>
                  )}
                </div>

                {/* Live Progress Bar Card */}
                <div className="p-4 rounded-xl bg-muted/30 border border-border/60 space-y-2">
                  <div className="flex items-center justify-between text-xs font-semibold">
                    <span className="text-foreground">
                      Execution Progress: Pass {selectedJob.current_pass} of {selectedJob.total_passes}
                    </span>
                    <span className="font-mono text-primary text-sm font-bold">{selectedJob.progress}%</span>
                  </div>
                  <div className="w-full bg-muted rounded-full h-3 overflow-hidden">
                    <div
                      className={`h-full transition-all duration-300 ${
                        selectedJob.status === 'COMPLETED'
                          ? 'bg-emerald-500'
                          : selectedJob.status === 'FAILED'
                          ? 'bg-rose-500'
                          : 'bg-primary'
                      }`}
                      style={{ width: `${selectedJob.progress}%` }}
                    />
                  </div>
                  <div className="grid grid-cols-3 gap-2 text-[11px] text-muted-foreground pt-1">
                    <div>
                      Started:{' '}
                      <strong className="text-foreground">{formatDate(selectedJob.started_at)}</strong>
                    </div>
                    <div>
                      Finished:{' '}
                      <strong className="text-foreground">{formatDate(selectedJob.finished_at)}</strong>
                    </div>
                    <div className="text-right">
                      Verification:{' '}
                      <strong className="text-emerald-600 dark:text-emerald-400">
                        {selectedJob.result?.verified ? 'PASSED (100%)' : selectedJob.status === 'COMPLETED' ? 'PASSED' : 'PENDING'}
                      </strong>
                    </div>
                  </div>
                </div>

                {/* Console Log Terminal */}
                <div className="rounded-xl border border-border bg-slate-950 text-slate-100 p-4 font-mono text-xs shadow-inner space-y-2">
                  <div className="flex items-center justify-between text-[11px] text-slate-400 border-b border-slate-800 pb-2">
                    <div className="flex items-center space-x-2">
                      <Terminal className="h-3.5 w-3.5 text-emerald-400" />
                      <span>Sanitization Telemetry Stream</span>
                    </div>
                    <span className="text-[10px] text-slate-500">FastAPI WebSocket /ws</span>
                  </div>

                  <div className="h-64 overflow-y-auto space-y-1.5 text-[11px] pr-2">
                    {jobEvents.length === 0 ? (
                      <p className="text-slate-500 italic py-6 text-center">
                        Streaming simulated sector overwrite passes and NIST verification metrics...
                      </p>
                    ) : (
                      jobEvents.map((e) => (
                        <div key={e.id} className="flex items-start space-x-2">
                          <span className="text-slate-500 shrink-0 text-[10px]">{e.timestamp}</span>
                          <span className="text-emerald-400">&gt;</span>
                          <span className="text-slate-200">{e.message}</span>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>

              {/* Certificate notice if completed */}
              {selectedJob.status === 'COMPLETED' && (
                <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-800 dark:text-emerald-300 text-xs flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <ShieldCheck className="h-5 w-5 text-emerald-600 shrink-0" />
                    <span>
                      Sanitization successfully completed. Cryptographic Certificate of Sanitization generated.
                    </span>
                  </div>
                  <a
                    href="/certificates"
                    className="font-bold underline hover:text-emerald-700 shrink-0 text-xs"
                  >
                    View Certificates &rarr;
                  </a>
                </div>
              )}
            </>
          ) : (
            <div className="py-20 text-center text-muted-foreground text-xs">
              Select a job from the queue to view live progress and execution logs.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
