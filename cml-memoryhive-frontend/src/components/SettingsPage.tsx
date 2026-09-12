import { AlertCircle, Cloud, Database, Download, LockKeyhole, ShieldCheck, Trash2, UserRound, X } from 'lucide-react';
import { FormEvent, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { accountApi, authApi } from '../services/api';
import { useLibraryStore } from '../store/libraryStore';
import ConfirmDialog from './ConfirmDialog';

function SettingToggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: () => void }) {
  return (
    <button className="setting-toggle" type="button" role="switch" aria-checked={checked} onClick={onChange}>
      <span>{label}</span><i className={checked ? 'on' : ''}><b /></i>
    </button>
  );
}

const demoMode = import.meta.env.VITE_DEMO_MODE === 'true';

export default function SettingsPage() {
  const { user, logout, setAIExternalProcessing } = useAuth();
  const navigate = useNavigate();
  const clear = useLibraryStore((state) => state.clear);
  const [sync, setSync] = useState(true);
  const [processing, setProcessing] = useState(true);
  const [dark, setDark] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [changeOpen, setChangeOpen] = useState(false);
  const [changeConfirmOpen, setChangeConfirmOpen] = useState(false);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [repeatPassword, setRepeatPassword] = useState('');
  const [changingPassword, setChangingPassword] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [password, setPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState('');
  const [privacyBusy, setPrivacyBusy] = useState(false);

  const toggleExternalAI = async () => {
    setPrivacyBusy(true);
    setError('');
    try {
      await setAIExternalProcessing(!user?.ai_external_processing_allowed);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Unable to update AI privacy preference');
    } finally {
      setPrivacyBusy(false);
    }
  };

  const exportData = async () => {
    setExporting(true);
    setError('');
    try {
      const { blob, disposition } = await accountApi.export();
      const filename = disposition?.match(/filename="?([^";]+)"?/)?.[1] || 'memoryhive-export.zip';
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      link.click();
      URL.revokeObjectURL(url);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Export failed');
    } finally {
      setExporting(false);
    }
  };

  const deleteAccount = async (event: FormEvent) => {
    event.preventDefault();
    setDeleting(true);
    setError('');
    try {
      await accountApi.remove(password);
      await logout();
      clear();
      navigate('/login', { replace: true });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Account deletion failed');
      setDeleting(false);
    }
  };

  const resetPasswordForm = () => {
    setCurrentPassword('');
    setNewPassword('');
    setRepeatPassword('');
    setChangeConfirmOpen(false);
  };

  const requestPasswordChange = (event: FormEvent) => {
    event.preventDefault();
    setError('');
    if (newPassword !== repeatPassword) {
      setError('New passwords do not match');
      return;
    }
    setChangeConfirmOpen(true);
  };

  const changePassword = async () => {
    setChangingPassword(true);
    setError('');
    try {
      if (!demoMode) {
        await authApi.changePassword({
          current_password: currentPassword,
          new_password: newPassword,
        });
      }
      resetPasswordForm();
      setChangeOpen(false);
      await logout({ localOnly: true });
      clear();
      navigate('/login', {
        replace: true,
        state: { notice: 'Password changed successfully. Sign in with your new password.' },
      });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Password change failed');
    } finally {
      setChangingPassword(false);
    }
  };

  return (
    <div className="page settings-page">
      <header className="page-header"><div><span className="eyebrow">Account</span><h1>Settings</h1><p>Preferences and data</p></div></header>

      <section className="settings-section">
        <div className="settings-title"><UserRound size={19} /><div><h2>Profile</h2><p>{user?.email || 'mahesh@example.com'}</p></div></div>
        <div className="profile-fields">
          <label className="field"><span>Name</span><input defaultValue={user?.name || 'Mahesh'} /></label>
          <label className="field"><span>Email</span><input type="email" defaultValue={user?.email || 'mahesh@example.com'} /></label>
          <button className="button secondary" type="button">Save profile</button>
        </div>
      </section>

      <section className="settings-section">
        <div className="settings-title"><Cloud size={19} /><div><h2>Sync and processing</h2><p>Background services</p></div></div>
        <div className="settings-controls">
          <SettingToggle label="Cloud sync" checked={sync} onChange={() => setSync(!sync)} />
          <SettingToggle label="Content processing" checked={processing} onChange={() => setProcessing(!processing)} />
          <SettingToggle label="Dark appearance" checked={dark} onChange={() => setDark(!dark)} />
        </div>
      </section>

      <section className="settings-section">
        <div className="settings-title"><ShieldCheck size={19} /><div><h2>AI privacy</h2><p>External model processing is off by default</p></div></div>
        <div className="settings-controls">
          <SettingToggle label={privacyBusy ? 'Updating external AI processing' : 'Allow approved external AI providers'} checked={Boolean(user?.ai_external_processing_allowed)} onChange={() => { if (!privacyBusy) void toggleExternalAI(); }} />
        </div>
        <p className="privacy-note">When off, Memoryhive permits only local or self-hosted AI routes. Turning it on allows the operator-approved third-party providers listed in the privacy policy. Capture and keyword search continue either way.</p>
      </section>

      <section className="settings-section">
        <div className="settings-title"><LockKeyhole size={19} /><div><h2>Security</h2><p>Password and active sessions</p></div></div>
        <div className="settings-actions">
          <button className="button secondary" type="button" onClick={() => { setError(''); setChangeOpen(true); }}>
            <LockKeyhole size={17} /> Change password
          </button>
          <span className="privacy-note"><ShieldCheck size={16} /> Changes sign out all sessions</span>
        </div>
      </section>

      <section className="settings-section">
        <div className="settings-title"><Database size={19} /><div><h2>Data</h2><p>Portable and user-owned</p></div></div>
        <div className="settings-actions">
          <button className="button secondary" type="button" disabled={exporting} onClick={() => void exportData()}><Download size={17} /> {exporting ? 'Preparing export' : 'Export data'}</button>
          <Link className="button secondary" to="/privacy"><ShieldCheck size={16} /> Privacy policy</Link>
          <span className="privacy-note"><ShieldCheck size={16} /> Private storage</span>
        </div>
      </section>

      <section className="settings-section danger-zone">
        <div className="settings-title"><Trash2 size={19} /><div><h2>Delete account</h2><p>Permanently removes all stored data</p></div></div>
        <div className="settings-actions">
          <button className="button danger" type="button" onClick={() => { setError(''); setDeleteOpen(true); }}>Delete account</button>
          <Link className="privacy-note" to="/account/delete">Web deletion instructions</Link>
        </div>
      </section>

      {error && !deleteOpen && !changeOpen && <div className="form-error" role="alert"><AlertCircle size={17} />{error}</div>}
      {changeOpen && (
        <div className="dialog-layer" role="presentation" onMouseDown={() => !changingPassword && setChangeOpen(false)}>
          <section className="edit-dialog" role="dialog" aria-modal="true" aria-labelledby="change-password-title" onMouseDown={(event) => event.stopPropagation()}>
            <header className="dialog-header">
              <div><span className="eyebrow">Security</span><h2 id="change-password-title">Change password</h2></div>
              <button className="icon-button" type="button" disabled={changingPassword} onClick={() => setChangeOpen(false)}><X size={20} /><span className="sr-only">Close</span></button>
            </header>
            <form className="capture-form" onSubmit={requestPasswordChange}>
              {error && <div className="form-error" role="alert"><AlertCircle size={17} />{error}</div>}
              <label className="field"><span>Current password</span><input type="password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} autoComplete="current-password" required /></label>
              <label className="field"><span>New password</span><input type="password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} autoComplete="new-password" minLength={8} required /></label>
              <label className="field"><span>Confirm new password</span><input type="password" value={repeatPassword} onChange={(event) => setRepeatPassword(event.target.value)} autoComplete="new-password" minLength={8} required /></label>
              <footer className="dialog-actions">
                <button className="button secondary" type="button" disabled={changingPassword} onClick={() => setChangeOpen(false)}>Cancel</button>
                <button className="button primary" type="submit" disabled={changingPassword}><LockKeyhole size={17} /> Continue</button>
              </footer>
            </form>
          </section>
        </div>
      )}
      {changeConfirmOpen && (
        <ConfirmDialog
          title="Change password?"
          description="Your password will be updated and every active session will be signed out."
          confirmLabel="Change password"
          busy={changingPassword}
          onCancel={() => setChangeConfirmOpen(false)}
          onConfirm={changePassword}
        />
      )}
      {deleteOpen && (
        <div className="dialog-layer" role="presentation" onMouseDown={() => !deleting && setDeleteOpen(false)}>
          <section className="edit-dialog" role="dialog" aria-modal="true" aria-labelledby="delete-account-title" onMouseDown={(event) => event.stopPropagation()}>
            <header className="dialog-header">
              <div><span className="eyebrow">Permanent action</span><h2 id="delete-account-title">Delete account</h2></div>
              <button className="icon-button" type="button" disabled={deleting} onClick={() => setDeleteOpen(false)}><X size={20} /><span className="sr-only">Close</span></button>
            </header>
            <form className="capture-form" onSubmit={deleteAccount}>
              {error && <div className="form-error" role="alert"><AlertCircle size={17} />{error}</div>}
              <label className="field"><span>Password</span><input type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" required /></label>
              <label className="field"><span>Type DELETE to confirm</span><input value={confirmation} onChange={(event) => setConfirmation(event.target.value)} required /></label>
              <footer className="dialog-actions">
                <button className="button secondary" type="button" disabled={deleting} onClick={() => setDeleteOpen(false)}>Cancel</button>
                <button className="button danger" type="submit" disabled={deleting || confirmation !== 'DELETE'}><Trash2 size={17} /> {deleting ? 'Deleting' : 'Delete permanently'}</button>
              </footer>
            </form>
          </section>
        </div>
      )}
    </div>
  );
}
