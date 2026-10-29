import { create } from 'zustand';
import { User, UserRole } from '../types';
import { api } from '../lib/api';

interface AuthState {
  user: User | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<User>;
  quickLogin: (role: UserRole) => Promise<User>;
  logout: () => Promise<void>;
  checkAuth: () => Promise<void>;
}

const DEMO_CREDENTIALS: Record<UserRole, { email: string; pass: string }> = {
  OPERATOR: { email: 'operator@securewipe.local', pass: 'Operator123!' },
  APPROVER: { email: 'approver@securewipe.local', pass: 'Approver123!' },
  ADMIN: { email: 'admin@securewipe.local', pass: 'Admin123!' },
};

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  accessToken: localStorage.getItem('securewipe_access_token'),
  isAuthenticated: !!localStorage.getItem('securewipe_access_token'),
  isLoading: true,
  error: null,

  login: async (email, password) => {
    set({ isLoading: true, error: null });
    try {
      const data = await api.login({ email, password });
      if (!data || typeof data !== 'object' || !data.access_token) {
        // e.g. a static host answered with index.html because VITE_API_URL is not set
        throw {
          code: 0,
          message: 'The SecureWipe backend is not connected. Set VITE_API_URL to the backend URL and redeploy.',
        };
      }
      localStorage.setItem('securewipe_access_token', data.access_token);
      localStorage.setItem('securewipe_refresh_token', data.refresh_token);
      localStorage.setItem('securewipe_user', JSON.stringify(data.user));

      set({
        user: data.user,
        accessToken: data.access_token,
        isAuthenticated: true,
        isLoading: false,
      });
      return data.user;
    } catch (err: any) {
      set({ error: err.message || 'Login failed', isLoading: false });
      throw err;
    }
  },

  quickLogin: async (role: UserRole) => {
    const creds = DEMO_CREDENTIALS[role];
    return get().login(creds.email, creds.pass);
  },

  logout: async () => {
    try {
      await api.logout();
    } catch {
      // Ignore network errors on logout
    }
    localStorage.removeItem('securewipe_access_token');
    localStorage.removeItem('securewipe_refresh_token');
    localStorage.removeItem('securewipe_user');
    set({ user: null, accessToken: null, isAuthenticated: false });
  },

  checkAuth: async () => {
    const token = localStorage.getItem('securewipe_access_token');
    if (!token) {
      set({ user: null, isAuthenticated: false, isLoading: false });
      return;
    }
    try {
      const user = await api.me();
      set({ user, isAuthenticated: true, isLoading: false });
    } catch {
      localStorage.removeItem('securewipe_access_token');
      localStorage.removeItem('securewipe_refresh_token');
      set({ user: null, isAuthenticated: false, isLoading: false });
    }
  },
}));
