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

  const isFormData = typeof FormData !== 'undefined' && options.body instanceof FormData;
  const headers: Record<string, string> = {
    ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
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
      let message = parsed.message || parsed.detail || errData.message;
      if (Array.isArray(message)) {
        // FastAPI validation errors: [{loc, msg}, ...]
        message = message
          .map((e: any) => `${(e.loc || []).filter((p: any) => p !== 'body').join('.')}: ${e.msg}`)
          .join('; ');
      }
      errData = {
        code: parsed.code || res.status,
        message: String(message),
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
  updateDevice: (id: string, data: any) =>
    apiRequest(`/devices/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteDevice: (id: string) => apiRequest(`/devices/${id}`, { method: 'DELETE' }),
  importDevicesCsv: (csvContent: string) => {
    const form = new FormData();
    form.append('file', new Blob([csvContent], { type: 'text/csv' }), 'devices.csv');
    return apiRequest('/devices/import-csv', { method: 'POST', body: form });
  },

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
  downloadCertificatePdf: async (certificateId: string) => {
    // The PDF endpoint needs the bearer token, so fetch it as a blob rather than opening a raw URL
    const send = () =>
      fetch(`${BASE_URL}/certificates/${encodeURIComponent(certificateId)}/pdf`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('securewipe_access_token') ?? ''}` },
      });
    let res = await send();
    if (res.status === 401) {
      await apiRequest('/auth/me').catch(() => undefined); // triggers a token refresh
      res = await send();
    }
    if (!res.ok) {
      let message = `Download failed (${res.status})`;
      try {
        message = (await res.json()).message || message;
      } catch {
        // not JSON
      }
      throw { code: res.status, message } as ApiError;
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${certificateId}.pdf`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  },
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
