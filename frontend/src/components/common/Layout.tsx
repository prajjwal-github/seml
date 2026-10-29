import React, { useEffect, useState } from 'react';
import { Outlet } from 'react-router-dom';
import { SimulationBanner } from './SimulationBanner';
import { Navbar } from './Navbar';
import { Sidebar } from './Sidebar';
import { wsClient } from '../../lib/ws';
import { api } from '../../lib/api';

export const Layout: React.FC = () => {
  const [pendingApprovals, setPendingApprovals] = useState(0);
  const [activeJobs, setActiveJobs] = useState(0);

  const fetchCounts = async () => {
    try {
      const summary = await api.getReportsSummary();
      setPendingApprovals(summary.pending_approvals ?? 0);
      setActiveJobs(summary.wiping_now ?? summary.active_jobs ?? 0);
    } catch {
      // Failed to load summary
    }
  };

  useEffect(() => {
    // Initial fetch
    fetchCounts();

    // Connect WebSocket
    wsClient.connect();

    // Listen for WebSocket updates
    const unsubAppr = wsClient.on('approval.requested', () => fetchCounts());
    const unsubApprDec = wsClient.on('approval.decided', () => fetchCounts());
    const unsubJob = wsClient.on('job.status', () => fetchCounts());
    const unsubCert = wsClient.on('certificate.generated', () => fetchCounts());

    return () => {
      unsubAppr();
      unsubApprDec();
      unsubJob();
      unsubCert();
    };
  }, []);

  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground">
      {/* Permanent Simulation Banner */}
      <SimulationBanner />

      {/* Global Navigation Header */}
      <Navbar />

      {/* App Body */}
      <div className="flex-1 flex overflow-hidden">
        <Sidebar pendingApprovalsCount={pendingApprovals} activeJobsCount={activeJobs} />
        <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 bg-muted/20">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
