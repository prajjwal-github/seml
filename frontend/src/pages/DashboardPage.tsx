import React from 'react';
import { useAuthStore } from '../store/authStore';
import { AdminDashboard } from './dashboards/AdminDashboard';
import { OperatorDashboard } from './dashboards/OperatorDashboard';
import { ApproverDashboard } from './dashboards/ApproverDashboard';

/** Each role lands on its own dashboard. */
export const DashboardPage: React.FC = () => {
  const { user } = useAuthStore();

  switch (user?.role) {
    case 'ADMIN':
      return <AdminDashboard />;
    case 'APPROVER':
      return <ApproverDashboard />;
    case 'OPERATOR':
      return <OperatorDashboard />;
    default:
      return null;
  }
};
