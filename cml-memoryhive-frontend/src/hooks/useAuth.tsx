import { createContext, ReactNode, useContext, useEffect, useState } from 'react';
import { authApi, hasSession } from '../services/api';
import type { User } from '../types/api';

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name?: string) => Promise<void>;
  logout: (options?: { localOnly?: boolean }) => Promise<void>;
  setAIExternalProcessing: (allowed: boolean) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);
const demoMode = import.meta.env.VITE_DEMO_MODE === 'true';
const demoUser: User = {
  id: '01a4dc43-39a8-4f09-b2f1-71a0a8b0fbde',
  email: 'mahesh@example.com',
  name: 'Mahesh',
  role: 'admin',
  is_active: true,
  ai_external_processing_allowed: false,
  created_at: '2026-08-01T00:00:00Z',
  updated_at: '2026-08-01T00:00:00Z',
};

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(() => demoMode ? demoUser : null);
  const [isLoading, setIsLoading] = useState(() => !demoMode && hasSession());

  useEffect(() => {
    const expire = () => setUser(null);
    window.addEventListener('memoryhive:session-expired', expire);
    if (!demoMode && hasSession()) {
      authApi.restore().then(setUser).catch(() => setUser(null)).finally(() => setIsLoading(false));
    }
    return () => window.removeEventListener('memoryhive:session-expired', expire);
  }, []);

  const login = async (email: string, password: string) => {
    await authApi.login({ email, password });
    setUser(await authApi.me());
  };

  const register = async (email: string, password: string, name?: string) => {
    await authApi.register({ email, password, name });
    await login(email, password);
  };

  const logout = async (options: { localOnly?: boolean } = {}) => {
    try {
      if (options.localOnly || demoMode) authApi.clearSession();
      else await authApi.logout();
    } catch {
      // Server-side revocation is best effort; local cleanup must always complete.
    } finally {
      authApi.clearSession();
      setUser(null);
    }
  };

  const setAIExternalProcessing = async (allowed: boolean) => {
    if (demoMode) {
      setUser((current) => current ? { ...current, ai_external_processing_allowed: allowed } : current);
      return;
    }
    setUser(await authApi.updateAIPrivacy(allowed));
  };

  return (
    <AuthContext.Provider value={{
      user, isLoading, isAuthenticated: Boolean(user), login, register, logout,
      setAIExternalProcessing,
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within an AuthProvider');
  return context;
}
