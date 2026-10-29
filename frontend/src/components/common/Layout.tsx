import React, { useEffect, useState } from 'react';
import { Outlet } from 'react-router-dom';
import { SimulationBanner } from './SimulationBanner';
import { Navbar } from './Navbar';
import { Sidebar } from './Sidebar';
import { wsClient } from '../../lib/ws';
import { api } from '../../lib/api';
import { useLiveRefresh } from '../../lib/useLiveRefresh';
import { useAuthStore } from '../../store/authStore';

export const Layout: React.FC = () => {
  const [pendingApprovals, setPendingApprovals] = useState(0);
  const [activeJobs, setActiveJobs] = useState(0);
  const { user } = useAuthStore();

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
    fetchCounts();
    wsClient.connect();
  }, [user?.id]);

  // Any lifecycle event (new request, decision, job progress, certificate) refreshes the badges
  useLiveRefresh(fetchCounts);

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
          <Outlet key={user?.id} />
        </main>
      </div>
    </div>
  );
};
