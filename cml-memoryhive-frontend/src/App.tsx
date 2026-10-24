import type { ReactElement } from 'react';
import { Navigate, Route, Routes, useLocation } from 'react-router-dom';
import AccountDeletionPage from './components/AccountDeletionPage';
import AdminPage from './components/AdminPage';
import AppShell from './components/AppShell';
import AuthPage from './components/AuthPage';
import ItemDetailPage from './components/ItemDetailPage';
import LibraryPage from './components/LibraryPage';
import OrganizationPage from './components/OrganizationPage';
import PrivacyPage from './components/PrivacyPage';
import SettingsPage from './components/SettingsPage';
import SupportPage from './components/SupportPage';
import { AuthProvider, useAuth } from './hooks/useAuth';

function LoadingScreen() {
  return (
    <main className="loading-screen" aria-label="Loading Memora">
      <span className="brand-loader" />
    </main>
  );
}

function RequireAuth({ children }: { children: ReactElement }) {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();
  if (isLoading) return <LoadingScreen />;
  if (!isAuthenticated) return <Navigate to="/login" state={{ from: location }} replace />;
  return children;
}

function PublicRoute({ children }: { children: ReactElement }) {
  const { isAuthenticated, isLoading } = useAuth();
  if (isLoading) return <LoadingScreen />;
  if (isAuthenticated) return <Navigate to="/" replace />;
  return children;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/privacy" element={<PrivacyPage />} />
      <Route path="/account/delete" element={<AccountDeletionPage />} />
      <Route path="/support" element={<SupportPage />} />
      <Route path="/login" element={<PublicRoute><AuthPage mode="login" /></PublicRoute>} />
      <Route path="/register" element={<PublicRoute><AuthPage mode="register" /></PublicRoute>} />
      <Route path="/" element={<RequireAuth><AppShell /></RequireAuth>}>
        <Route index element={<LibraryPage />} />
        <Route path="favorites" element={<LibraryPage mode="favorites" />} />
        <Route path="archive" element={<LibraryPage mode="archive" />} />
        <Route path="organize" element={<OrganizationPage />} />
        <Route path="admin" element={<AdminPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="items/:id" element={<ItemDetailPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return <AuthProvider><AppRoutes /></AuthProvider>;
}
