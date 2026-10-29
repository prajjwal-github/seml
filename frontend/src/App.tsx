import React, { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { useAuthStore } from './store/authStore';
import { Layout } from './components/common/Layout';
import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { DevicesPage } from './pages/DevicesPage';
import { DeviceDetailPage } from './pages/DeviceDetailPage';
import { ApprovalsInboxPage } from './pages/ApprovalsInboxPage';
import { LiveJobsPage } from './pages/LiveJobsPage';
import { CertificatesPage } from './pages/CertificatesPage';
import { PublicVerifyPage } from './pages/PublicVerifyPage';
import { AuditLogPage } from './pages/AuditLogPage';
import { AdminSettingsPage } from './pages/AdminSettingsPage';

const ProtectedRoute: React.FC<{ children: React.ReactNode; adminOnly?: boolean }> = ({
  children,
  adminOnly = false,
}) => {
  const { isAuthenticated, isLoading, user } = useAuthStore();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center text-xs text-muted-foreground">
        Verifying cryptographic session...
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (adminOnly && user?.role !== 'ADMIN') {
    return <Navigate to="/dashboard" replace />;
  }

  return <>{children}</>;
};

export const App: React.FC = () => {
  const { checkAuth } = useAuthStore();

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  return (
    <BrowserRouter>
      <Routes>
        {/* Public Routes (No Authentication Required) */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/verify" element={<PublicVerifyPage />} />
        <Route path="/verify/:id" element={<PublicVerifyPage />} />

        {/* Authenticated Platform Routes */}
        <Route
          element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }
        >
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/devices" element={<DevicesPage />} />
          <Route path="/devices/:id" element={<DeviceDetailPage />} />
          <Route path="/approvals" element={<ApprovalsInboxPage />} />
          <Route path="/jobs" element={<LiveJobsPage />} />
          <Route path="/certificates" element={<CertificatesPage />} />
          <Route path="/audit" element={<AuditLogPage />} />
          <Route
            path="/admin"
            element={
              <ProtectedRoute adminOnly>
                <AdminSettingsPage />
              </ProtectedRoute>
            }
          />
        </Route>

        {/* Catch-all fallback */}
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  );
};
export default App;
