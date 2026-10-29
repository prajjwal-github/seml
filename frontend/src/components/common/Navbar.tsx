import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  ShieldCheck,
  Sun,
  Moon,
  LogOut,
  UserCheck,
  ChevronDown,
  Wifi,
  WifiOff,
} from 'lucide-react';
import { useAuthStore } from '../../store/authStore';
import { useThemeStore } from '../../store/themeStore';
import { wsClient } from '../../lib/ws';
import { UserRole } from '../../types';
import { ROLES, roleInfo } from '../../lib/roles';

export const Navbar: React.FC = () => {
  const { user, logout, quickLogin } = useAuthStore();
  const { theme, toggleTheme } = useThemeStore();
  const navigate = useNavigate();
  const [wsConnected, setWsConnected] = useState(false);
  const [roleDropdownOpen, setRoleDropdownOpen] = useState(false);

  useEffect(() => {
    const unsub = wsClient.on('connection.status', (data) => {
      setWsConnected(data.connected);
    });
    return () => unsub();
  }, []);

  const handleQuickSwitch = async (role: UserRole) => {
    setRoleDropdownOpen(false);
    await quickLogin(role);
    navigate('/dashboard');
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <header className="h-16 border-b border-border bg-card/90 backdrop-blur-md sticky top-[33px] z-40 px-4 sm:px-6 flex items-center justify-between">
      <div className="flex items-center space-x-4">
        <Link to="/dashboard" className="flex items-center space-x-2.5 group">
          <div className="w-9 h-9 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center text-primary group-hover:scale-105 transition-transform">
            <ShieldCheck className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-bold text-base tracking-tight text-foreground">SecureWipe</span>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-muted text-muted-foreground uppercase font-semibold">
                NIST 800-88
              </span>
            </div>
            <p className="text-[10px] text-muted-foreground hidden sm:block">Certified IT Asset Recycling</p>
          </div>
        </Link>

        {/* Live WebSocket Status Dot */}
        <div className="hidden lg:flex items-center space-x-1.5 text-xs text-muted-foreground border-l border-border pl-4">
          {wsConnected ? (
            <>
              <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
              <span className="text-[11px] font-mono">Live WS Connected</span>
            </>
          ) : (
            <>
              <span className="h-2 w-2 rounded-full bg-amber-500"></span>
              <span className="text-[11px] font-mono">WS Reconnecting...</span>
            </>
          )}
        </div>
      </div>

      <div className="flex items-center space-x-3">
        {/* Public Verify Link */}
        <Link
          to="/verify"
          className="text-xs font-medium text-muted-foreground hover:text-foreground px-2.5 py-1.5 rounded-md hover:bg-muted transition-colors hidden md:block"
        >
          Public Certificate Verify
        </Link>

        {/* Theme Toggle */}
        <button
          onClick={toggleTheme}
          title="Toggle light/dark theme"
          className="p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted border border-border/50 transition-colors"
        >
          {theme === 'dark' ? <Sun className="h-4 w-4 text-amber-400" /> : <Moon className="h-4 w-4" />}
        </button>

        {/* Persona / Quick Switch Dropdown */}
        <div className="relative">
          <button
            onClick={() => setRoleDropdownOpen(!roleDropdownOpen)}
            className="flex items-center space-x-2 text-xs font-medium px-2.5 py-1.5 rounded-lg border border-border bg-background hover:bg-muted transition-colors"
          >
            <UserCheck className="h-3.5 w-3.5 text-primary" />
            <span className="hidden sm:inline font-semibold text-primary">{roleInfo(user?.role)?.title || 'Guest'}</span>
            <ChevronDown className="h-3 w-3 text-muted-foreground" />
          </button>

          {roleDropdownOpen && (
            <div className="absolute right-0 mt-2 w-56 rounded-lg bg-card border border-border shadow-xl py-2 z-50 text-xs">
              <div className="px-3 py-1.5 text-muted-foreground font-semibold border-b border-border/50 uppercase text-[10px] tracking-wider">
                Switch role (demo)
              </div>
              {ROLES.map(({ role: r }) => (
                <button
                  key={r}
                  onClick={() => handleQuickSwitch(r)}
                  className={`w-full text-left px-3 py-2 flex items-center justify-between hover:bg-muted transition-colors ${
                    user?.role === r ? 'font-bold text-primary bg-primary/5' : 'text-foreground'
                  }`}
                >
                  <span>{roleInfo(r)?.title}</span>
                  {user?.role === r && <span className="text-[10px] bg-primary/20 text-primary px-1.5 rounded">Active</span>}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* User Profile & Logout */}
        {user ? (
          <div className="flex items-center space-x-2 pl-2 border-l border-border">
            <div className="hidden sm:block text-right">
              <div className="text-xs font-semibold text-foreground leading-tight">{user.name}</div>
              <div className="text-[10px] text-muted-foreground font-mono">{user.email}</div>
            </div>
            <button
              onClick={handleLogout}
              title="Logout"
              className="p-2 text-muted-foreground hover:text-destructive hover:bg-destructive/10 rounded-lg transition-colors"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        ) : (
          <Link
            to="/login"
            className="text-xs font-semibold bg-primary text-primary-foreground px-3 py-1.5 rounded-lg hover:bg-primary/90 transition-colors"
          >
            Sign In
          </Link>
        )}
      </div>
    </header>
  );
};
