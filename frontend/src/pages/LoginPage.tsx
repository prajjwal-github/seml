import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ShieldCheck, Lock, Mail, ArrowRight, UserCheck, CheckCircle2 } from 'lucide-react';
import { useAuthStore } from '../store/authStore';
import { UserRole } from '../types';
import { SimulationBanner } from '../components/common/SimulationBanner';
import { ROLES } from '../lib/roles';

export const LoginPage: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const { login, quickLogin } = useAuthStore();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setSubmitting(true);
    try {
      await login(email, password);
      navigate('/dashboard');
    } catch (err: any) {
      setErrorMsg(err.message || 'Invalid email or password');
    } finally {
      setSubmitting(false);
    }
  };

  const handleQuick = async (role: UserRole) => {
    setSubmitting(true);
    setErrorMsg(null);
    try {
      await quickLogin(role);
      navigate('/dashboard');
    } catch (err: any) {
      setErrorMsg(err.message || 'Quick login failed');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex flex-col justify-between">
      <SimulationBanner />
      <div className="flex-1 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
        <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-primary/10 border border-primary/20 text-primary shadow-lg mb-4">
          <ShieldCheck className="w-8 h-8" />
        </div>
        <h2 className="text-2xl font-extrabold tracking-tight text-foreground">SecureWipe Platform</h2>
        <p className="mt-1 text-xs text-muted-foreground">
          Certified data wiping for office devices: Admin registers, Operator requests, Approver certifies
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-2xl px-4">
        <div className="bg-card border border-border py-8 px-6 shadow-xl rounded-2xl sm:px-10">
          <form className="space-y-4" onSubmit={handleSubmit}>
            {errorMsg && (
              <div className="p-3 text-xs bg-rose-500/10 border border-rose-500/30 text-rose-600 dark:text-rose-400 rounded-lg">
                {errorMsg}
              </div>
            )}

            <div>
              <label className="block text-xs font-medium text-foreground">Email Address</label>
              <div className="mt-1 relative rounded-md shadow-sm">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-muted-foreground">
                  <Mail className="h-4 w-4" />
                </div>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="operator@securewipe.local"
                  className="block w-full pl-9 pr-3 py-2 text-xs bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-foreground">Password</label>
              <div className="mt-1 relative rounded-md shadow-sm">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-muted-foreground">
                  <Lock className="h-4 w-4" />
                </div>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="block w-full pl-9 pr-3 py-2 text-xs bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="w-full flex justify-center items-center space-x-2 py-2.5 px-4 border border-transparent rounded-lg shadow-sm text-xs font-semibold text-primary-foreground bg-primary hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary transition-colors disabled:opacity-50"
            >
              <span>{submitting ? 'Authenticating...' : 'Sign In with Credentials'}</span>
              <ArrowRight className="h-4 w-4" />
            </button>
          </form>

          {/* Quick Demo Switcher Section */}
          <div className="mt-8 border-t border-border pt-6">
            <div className="flex items-center justify-between mb-3">
              <span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
                <UserCheck className="h-3.5 w-3.5 text-primary" />
                Sign in as one of the three roles
              </span>
              <span className="text-[10px] text-muted-foreground font-mono">Demo accounts</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
              {ROLES.map((item) => (
                <button
                  key={item.role}
                  onClick={() => handleQuick(item.role)}
                  disabled={submitting}
                  className="text-left p-3 rounded-lg border border-border/80 bg-muted/40 hover:bg-muted hover:border-primary/50 transition-all group flex flex-col justify-between"
                >
                  <div className="flex items-center justify-between w-full">
                    <span className="text-xs font-bold text-foreground group-hover:text-primary transition-colors">
                      {item.title}
                    </span>
                    <CheckCircle2 className="h-3.5 w-3.5 text-muted-foreground group-hover:text-primary" />
                  </div>
                  <span className="text-[10px] font-semibold text-primary/80 mt-0.5">{item.subtitle}</span>
                  <p className="text-[11px] text-muted-foreground mt-1 leading-relaxed">{item.description}</p>
                  <div className="mt-2 text-[10px] font-mono text-muted-foreground/80">{item.email}</div>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
  );
};

