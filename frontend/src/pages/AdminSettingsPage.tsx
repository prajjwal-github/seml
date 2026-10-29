import React, { useState, useEffect } from 'react';
import {
  Settings,
  Users,
  ShieldAlert,
  Key,
  Plus,
  Clock,
  CheckCircle2,
  Lock,
} from 'lucide-react';
import { api } from '../lib/api';
import { User, UserRole } from '../types';
import { LoadingSkeleton } from '../components/common/LoadingSkeleton';
import { formatDate } from '../lib/utils';

export const AdminSettingsPage: React.FC = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [newUser, setNewUser] = useState({
    name: '',
    email: '',
    password: '',
    role: 'OPERATOR' as UserRole,
  });
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const fetchUsers = async () => {
    try {
      const data = await api.getUsers();
      setUsers(data);
    } catch {
      // Failed to load users
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setErrorMsg(null);
    try {
      await api.createUser(newUser);
      setIsCreateOpen(false);
      setNewUser({ name: '', email: '', password: '', role: 'OPERATOR' });
      fetchUsers();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to create user');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-extrabold tracking-tight text-foreground">Platform Administration & Policies</h1>
        <p className="text-xs text-muted-foreground mt-0.5">
          User lifecycle management, dual-custody parameters, and simulation engine controls.
        </p>
      </div>

      {/* Security Policies Overview */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-card border border-border p-4 rounded-xl shadow-sm space-y-2">
          <div className="flex items-center space-x-2 text-primary font-bold text-xs">
            <Clock className="h-4 w-4" />
            <span>Approval TTL Policy</span>
          </div>
          <p className="text-xl font-extrabold text-foreground font-mono">24 Hours</p>
          <p className="text-[11px] text-muted-foreground">
            Unapproved requests expire automatically. Stale tokens are refused by the wipe worker.
          </p>
        </div>

        <div className="bg-card border border-border p-4 rounded-xl shadow-sm space-y-2">
          <div className="flex items-center space-x-2 text-amber-500 font-bold text-xs">
            <Lock className="h-4 w-4" />
            <span>Dual-Custody Rules</span>
          </div>
          <p className="text-xl font-extrabold text-foreground font-mono">Four-Eyes Active</p>
          <p className="text-[11px] text-muted-foreground">
            Enforced by PostgreSQL trigger and API. High-risk operations require 2 distinct approvers.
          </p>
        </div>

        <div className="bg-card border border-border p-4 rounded-xl shadow-sm space-y-2">
          <div className="flex items-center space-x-2 text-emerald-500 font-bold text-xs">
            <Key className="h-4 w-4" />
            <span>Cryptographic Keys</span>
          </div>
          <p className="text-xl font-extrabold text-foreground font-mono">Ed25519 Active</p>
          <p className="text-[11px] text-muted-foreground">
            Root signing keys published at <code className="font-mono text-[10px]">/.well-known/wipe-keys</code>.
          </p>
        </div>
      </div>

      {/* User Management Section */}
      <div className="bg-card border border-border rounded-xl p-5 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-bold text-foreground">User Accounts & Roles</h2>
            <p className="text-xs text-muted-foreground">Personnel authorized for sanitization requests and approvals.</p>
          </div>
          <button
            onClick={() => setIsCreateOpen(true)}
            className="flex items-center space-x-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
          >
            <Plus className="h-4 w-4" />
            <span>New User</span>
          </button>
        </div>

        {loading ? (
          <LoadingSkeleton count={4} className="h-14" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-muted/50 border-b border-border text-[11px] font-semibold text-muted-foreground uppercase">
                <tr>
                  <th className="px-4 py-2.5">Name</th>
                  <th className="px-4 py-2.5">Email</th>
                  <th className="px-4 py-2.5">Role</th>
                  <th className="px-4 py-2.5">Status</th>
                  <th className="px-4 py-2.5">Created</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60">
                {users.map((u) => (
                  <tr key={u.id} className="hover:bg-muted/30">
                    <td className="px-4 py-3 font-bold text-foreground">{u.name}</td>
                    <td className="px-4 py-3 font-mono text-[11px] text-muted-foreground">{u.email}</td>
                    <td className="px-4 py-3">
                      <span className="font-mono text-[10px] font-bold px-2 py-0.5 rounded bg-muted text-foreground">
                        {u.role}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-[10px] text-emerald-600 dark:text-emerald-400 font-bold">ACTIVE</span>
                    </td>
                    <td className="px-4 py-3 text-muted-foreground text-[11px]">{formatDate(u.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Create User Modal */}
      {isCreateOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="bg-card border border-border rounded-2xl shadow-2xl w-full max-w-md p-6 space-y-4 animate-in fade-in zoom-in-95 text-xs">
            <h3 className="text-base font-bold text-foreground">Create User Account</h3>
            {errorMsg && (
              <div className="p-3 bg-rose-500/10 border border-rose-500/30 text-rose-600 dark:text-rose-400 rounded-lg">
                {errorMsg}
              </div>
            )}
            <form onSubmit={handleCreateUser} className="space-y-3">
              <div>
                <label className="block font-medium text-foreground mb-1">Full Name</label>
                <input
                  type="text"
                  required
                  value={newUser.name}
                  onChange={(e) => setNewUser({ ...newUser, name: e.target.value })}
                  placeholder="Jane Doe"
                  className="w-full px-3 py-2 bg-background border border-border rounded-lg text-xs"
                />
              </div>
              <div>
                <label className="block font-medium text-foreground mb-1">Email Address</label>
                <input
                  type="email"
                  required
                  value={newUser.email}
                  onChange={(e) => setNewUser({ ...newUser, email: e.target.value })}
                  placeholder="jane.doe@securewipe.local"
                  className="w-full px-3 py-2 bg-background border border-border rounded-lg text-xs"
                />
              </div>
              <div>
                <label className="block font-medium text-foreground mb-1">Password</label>
                <input
                  type="password"
                  required
                  value={newUser.password}
                  onChange={(e) => setNewUser({ ...newUser, password: e.target.value })}
                  placeholder="••••••••••••"
                  className="w-full px-3 py-2 bg-background border border-border rounded-lg text-xs"
                />
              </div>
              <div>
                <label className="block font-medium text-foreground mb-1">Assigned Role</label>
                <select
                  value={newUser.role}
                  onChange={(e) => setNewUser({ ...newUser, role: e.target.value as UserRole })}
                  className="w-full px-3 py-2 bg-background border border-border rounded-lg text-xs"
                >
                  <option value="OPERATOR">Operator (requests certificates)</option>
                  <option value="APPROVER">Approver (approves / rejects)</option>
                  <option value="ADMIN">Admin (manages devices)</option>
                </select>
              </div>

              <div className="flex justify-end space-x-2 pt-3">
                <button
                  type="button"
                  onClick={() => setIsCreateOpen(false)}
                  className="px-3 py-1.5 rounded-lg border border-border text-foreground hover:bg-muted"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-1.5 rounded-lg bg-primary text-primary-foreground font-semibold hover:bg-primary/90 disabled:opacity-50"
                >
                  {submitting ? 'Creating...' : 'Create Account'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
