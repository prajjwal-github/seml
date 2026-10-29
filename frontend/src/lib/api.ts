/**
 * Type-safe API client communicating with FastAPI backend.
 * Handles JWT bearer injection, token refresh, and structured error propagation.
 */

const BASE_URL = '/api/v1';

export interface ApiError {
  code: number;
  message: string;
  details?: any;
}

export async function apiRequest<T = any>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = localStorage.getItem('securewipe_access_token');

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  if (token && !headers['Authorization']) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const url = endpoint.startsWith('http') || endpoint.startsWith('/api') || endpoint.startsWith('/.well-known')
    ? endpoint
    : `${BASE_URL}${endpoint}`;

  let res = await fetch(url, { ...options, headers });

  // Handle 401 unauthorized: attempt token refresh
  if (res.status === 401 && !endpoint.includes('/auth/login') && !endpoint.includes('/auth/refresh')) {
    const refreshToken = localStorage.getItem('securewipe_refresh_token');
    if (refreshToken) {
      try {
        const refreshRes = await fetch(`${BASE_URL}/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
        if (refreshRes.ok) {
          const data = await refreshRes.json();
          localStorage.setItem('securewipe_access_token', data.access_token);
          localStorage.setItem('securewipe_refresh_token', data.refresh_token);
          headers['Authorization'] = `Bearer ${data.access_token}`;
          res = await fetch(url, { ...options, headers });
        } else {
          localStorage.removeItem('securewipe_access_token');
          localStorage.removeItem('securewipe_refresh_token');
          localStorage.removeItem('securewipe_user');
          window.dispatchEvent(new Event('auth:unauthorized'));
        }
      } catch {
        // Refresh failed
      }
    }
  }

  if (!res.ok) {
    let errData: ApiError = {
      code: res.status,
      message: `Request failed with status ${res.status}`,
    };
    try {
      const parsed = await res.json();
      errData = {
        code: parsed.code || res.status,
        message: parsed.message || parsed.detail || errData.message,
        details: parsed.details,
      };
    } catch {
      // Body not JSON
    }
    throw errData;
  }

  // Handle empty responses
  const contentType = res.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    return (await res.json()) as T;
  }
  return (await res.text()) as unknown as T;
}

export const api = {
  // Auth
  login: (credentials: { email: string; password: string }) =>
    apiRequest('/auth/login', { method: 'POST', body: JSON.stringify(credentials) }),
  me: () => apiRequest('/auth/me'),
  logout: () => apiRequest('/auth/logout', { method: 'POST' }),

  // Devices
  getDevices: (params?: { category?: string; status?: string; search?: string }) => {
    const query = new URLSearchParams(params as any).toString();
    return apiRequest(`/devices${query ? `?${query}` : ''}`);
  },
  getDevice: (id: string) => apiRequest(`/devices/${id}`),
  createDevice: (data: any) => apiRequest('/devices', { method: 'POST', body: JSON.stringify(data) }),
  importDevicesCsv: (csvContent: string) =>
    apiRequest('/devices/import-csv', { method: 'POST', body: JSON.stringify({ csv_content: csvContent }) }),

  // Wipe Requests
  createWipeRequest: (data: {
    device_id: string;
    volume_ids: string[];
    method: string;
    reason: string;
    confirm_serial: string;
  }) => apiRequest('/wipe-requests', { method: 'POST', body: JSON.stringify(data) }),
  getWipeRequests: (params?: { status?: string }) => {
    const query = new URLSearchParams(params as any).toString();
    return apiRequest(`/wipe-requests${query ? `?${query}` : ''}`);
  },
  getWipeRequest: (id: string) => apiRequest(`/wipe-requests/${id}`),
  cancelWipeRequest: (id: string) => apiRequest(`/wipe-requests/${id}/cancel`, { method: 'POST' }),

  // Approvals
  getApprovalsInbox: () => apiRequest('/approvals/inbox'),
  approveRequest: (requestId: string, comment?: string) =>
    apiRequest(`/approvals/${requestId}/approve`, {
      method: 'POST',
      body: JSON.stringify({ decision: 'APPROVED', comment }),
    }),
  rejectRequest: (requestId: string, comment: string) =>
    apiRequest(`/approvals/${requestId}/reject`, {
      method: 'POST',
      body: JSON.stringify({ decision: 'REJECTED', comment }),
    }),

  // Jobs
  startJob: (requestId: string, token: string) =>
    apiRequest('/jobs/start', {
      method: 'POST',
      body: JSON.stringify({ request_id: requestId, token }),
    }),
  getJobs: () => apiRequest('/jobs'),
  getJob: (id: string) => apiRequest(`/jobs/${id}`),
  getJobEvents: (id: string) => apiRequest(`/jobs/${id}/events`),
  cancelJob: (id: string) => apiRequest(`/jobs/${id}/cancel`, { method: 'POST' }),

  // Certificates
  getCertificates: (search?: string) => {
    const query = search ? `?search=${encodeURIComponent(search)}` : '';
    return apiRequest(`/certificates${query}`);
  },
  getCertificate: (id: string) => apiRequest(`/certificates/${id}`),
  revokeCertificate: (id: string, reason: string) =>
    apiRequest(`/certificates/${id}/revoke`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    }),

  // Public Verification (No auth required)
  verifyById: (id: string) => apiRequest(`/verify/${id}`),
  verifyPayload: (payload: any, signature: string, public_key_id?: string) =>
    apiRequest('/verify', {
      method: 'POST',
      body: JSON.stringify({ payload, signature, public_key_id }),
    }),
  getPublicKeys: () => apiRequest('/.well-known/wipe-keys'),

  // Audit
  getAuditLogs: (params?: { action?: string; limit?: number }) => {
    const query = new URLSearchParams(params as any).toString();
    return apiRequest(`/audit${query ? `?${query}` : ''}`);
  },
  verifyAuditChain: () => apiRequest('/audit/verify-chain'),

  // Reports
  getReportsSummary: () => apiRequest('/reports/summary'),

  // Users (Admin)
  getUsers: () => apiRequest('/users'),
  createUser: (data: any) => apiRequest('/users', { method: 'POST', body: JSON.stringify(data) }),
};
