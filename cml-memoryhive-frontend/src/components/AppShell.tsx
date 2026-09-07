import {
  Archive,
  AlertCircle,
  Cloud,
  FolderTree,
  Library,
  LogOut,
  Plus,
  Search,
  Settings,
  ShieldCheck,
  Star,
  UserRound,
  X,
} from 'lucide-react';
import { useCallback, useEffect, useRef } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { useLibraryStore } from '../store/libraryStore';
import Brand from './Brand';
import CaptureDialog from './CaptureDialog';

const baseNavigation = [
  { to: '/', label: 'Library', icon: Library, end: true },
  { to: '/favorites', label: 'Favorites', icon: Star },
  { to: '/archive', label: 'Archive', icon: Archive },
  { to: '/organize', label: 'Organize', icon: FolderTree },
];

const IDLE_REFRESH_MS = 60_000;
const IDLE_LOGOUT_MS = 10 * 60_000;

export default function AppShell() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const setCaptureOpen = useLibraryStore((state) => state.setCaptureOpen);
  const initialize = useLibraryStore((state) => state.initialize);
  const clear = useLibraryStore((state) => state.clear);
  const error = useLibraryStore((state) => state.error);
  const notice = useLibraryStore((state) => state.notice);
  const dismissMessage = useLibraryStore((state) => state.dismissMessage);
  const navigation = user?.role === 'admin'
    ? [...baseNavigation, { to: '/admin', label: 'Admin', icon: ShieldCheck }]
    : baseNavigation;

  const signOut = useCallback(async (message?: string, localOnly = false) => {
    await logout({ localOnly });
    clear();
    navigate('/login', {
      replace: true,
      state: message ? { notice: message } : undefined,
    });
  }, [clear, logout, navigate]);

  useEffect(() => { void initialize(); }, [initialize]);

  useEffect(() => {
    const onExpired = (event: Event) => {
      const detail = event instanceof CustomEvent ? event.detail as { message?: string } : null;
      void signOut(detail?.message ?? 'Your session expired. Sign in again.', true);
    };
    window.addEventListener('memoryhive:session-expired', onExpired);
    return () => window.removeEventListener('memoryhive:session-expired', onExpired);
  }, [signOut]);

  const lastActivity = useRef(Date.now());
  useEffect(() => {
    if (!user) return undefined;
    const markActive = () => {
      lastActivity.current = Date.now();
    };
    const events = ['pointerdown', 'keydown', 'touchstart', 'scroll'];
    events.forEach((event) => window.addEventListener(event, markActive, { passive: true }));
    const timer = window.setInterval(() => {
      const idleFor = Date.now() - lastActivity.current;
      if (idleFor >= IDLE_LOGOUT_MS) {
        void signOut('Signed out after 10 minutes of inactivity.', true);
        return;
      }
      if (idleFor >= IDLE_REFRESH_MS) void initialize(true);
    }, IDLE_REFRESH_MS);
    return () => {
      window.clearInterval(timer);
      events.forEach((event) => window.removeEventListener(event, markActive));
    };
  }, [initialize, signOut, user]);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Brand />
        <button className="capture-button" type="button" onClick={() => setCaptureOpen(true)}>
          <Plus size={18} aria-hidden="true" />
          Capture
        </button>
        <nav className="sidebar-nav" aria-label="Primary navigation">
          {navigation.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}
            >
              <Icon size={18} aria-hidden="true" />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <NavLink
            to="/settings"
            className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}
          >
            <Settings size={18} aria-hidden="true" />
            <span>Settings</span>
          </NavLink>
          <div className="sync-state">
            <Cloud size={15} aria-hidden="true" />
            <span>Synced</span>
            <span className="sync-dot" aria-hidden="true" />
          </div>
          <button className="account-button" type="button" onClick={() => void signOut()}>
            <span className="avatar" aria-hidden="true">
              <UserRound size={16} />
            </span>
            <span className="account-copy">
              <strong>{user?.name || 'Mahesh'}</strong>
              <small>{user?.email || 'mahesh@example.com'}</small>
            </span>
            <LogOut size={16} aria-label="Sign out" />
          </button>
        </div>
      </aside>

      <header className="mobile-header">
        <Brand />
        <button className="icon-button strong" type="button" onClick={() => setCaptureOpen(true)}>
          <Plus size={20} />
          <span className="sr-only">Capture item</span>
        </button>
      </header>

      <main className="workspace" id="main-content">
        {(error || notice) && (
          <div className={`app-message ${error ? 'error' : 'success'}`} role={error ? 'alert' : 'status'}>
            {error && <AlertCircle size={17} />}
            <span>{error || notice}</span>
            <button type="button" onClick={dismissMessage} aria-label="Dismiss message"><X size={16} /></button>
          </div>
        )}
        <Outlet />
      </main>

      <nav className="mobile-nav" aria-label="Mobile navigation">
        {navigation.slice(0, 4).map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) => `mobile-nav-link${isActive ? ' active' : ''}`}
          >
            <Icon size={20} />
            <span>{label}</span>
          </NavLink>
        ))}
        <button
          type="button"
          className="mobile-nav-link"
          onClick={() => {
            navigate('/');
            requestAnimationFrame(() => document.querySelector<HTMLInputElement>('#library-search')?.focus());
          }}
        >
          <Search size={20} />
          <span>Search</span>
        </button>
      </nav>
      <CaptureDialog />
    </div>
  );
}
