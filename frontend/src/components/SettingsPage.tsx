import { AlertCircle, Cloud, Database, Download, ShieldCheck, Trash2, UserRound, X } from 'lucide-react';
import { FormEvent, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { accountApi } from '../services/api';
import { useLibraryStore } from '../store/libraryStore';

function SettingToggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: () => void }) {
  return (
    <button className="setting-toggle" type="button" role="switch" aria-checked={checked} onClick={onChange}>
      <span>{label}</span><i className={checked ? 'on' : ''}><b /></i>
    </button>
  );
}

export default function SettingsPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const clear = useLibraryStore((state) => state.clear);
  const [sync, setSync] = useState(true);
  const [processing, setProcessing] = useState(true);
  const [dark, setDark] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [password, setPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState('');

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
        <div className="settings-title"><Database size={19} /><div><h2>Data</h2><p>Portable and user-owned</p></div></div>
        <div className="settings-actions">
          <button className="button secondary" type="button" disabled={exporting} onClick={() => void exportData()}><Download size={17} /> {exporting ? 'Preparing export' : 'Export data'}</button>
          <span className="privacy-note"><ShieldCheck size={16} /> Private storage</span>
        </div>
      </section>

      <section className="settings-section danger-zone">
        <div className="settings-title"><Trash2 size={19} /><div><h2>Delete account</h2><p>Permanently removes all stored data</p></div></div>
        <button className="button danger" type="button" onClick={() => { setError(''); setDeleteOpen(true); }}>Delete account</button>
      </section>

      {error && !deleteOpen && <div className="form-error" role="alert"><AlertCircle size={17} />{error}</div>}
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
