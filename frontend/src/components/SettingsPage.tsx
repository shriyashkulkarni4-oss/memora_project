import { Cloud, Database, Download, ShieldCheck, Trash2, UserRound } from 'lucide-react';
import { useState } from 'react';
import { useAuth } from '../hooks/useAuth';

function SettingToggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: () => void }) {
  return (
    <button className="setting-toggle" type="button" role="switch" aria-checked={checked} onClick={onChange}>
      <span>{label}</span><i className={checked ? 'on' : ''}><b /></i>
    </button>
  );
}

export default function SettingsPage() {
  const { user } = useAuth();
  const [sync, setSync] = useState(true);
  const [processing, setProcessing] = useState(true);
  const [dark, setDark] = useState(false);

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
          <button className="button secondary" type="button"><Download size={17} /> Export data</button>
          <span className="privacy-note"><ShieldCheck size={16} /> Private storage</span>
        </div>
      </section>

      <section className="settings-section danger-zone">
        <div className="settings-title"><Trash2 size={19} /><div><h2>Delete account</h2><p>Permanently removes all stored data</p></div></div>
        <button className="button danger" type="button">Delete account</button>
      </section>
    </div>
  );
}
