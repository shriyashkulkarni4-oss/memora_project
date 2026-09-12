import {
  AlertTriangle,
  Archive,
  BarChart3,
  Clock,
  Database,
  HardDrive,
  PlayCircle,
  RefreshCw,
  ShieldCheck,
  Terminal,
  Trash2,
  UserCog,
  UserRound,
  UserX,
  Users,
} from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { adminApi } from '../services/api';
import { useLibraryStore } from '../store/libraryStore';
import type { AdminBackupRunResult, AdminBackupStatus, AdminDashboard, AdminProcessingJob, AdminUser } from '../types/api';
import ConfirmDialog from './ConfirmDialog';

type AdminAction =
  | { kind: 'enable' | 'disable' | 'delete'; user: AdminUser }
  | { kind: 'role'; user: AdminUser; role: AdminUser['role'] }
  | null;

const demoMode = import.meta.env.VITE_DEMO_MODE === 'true';

function formatBytes(value: number) {
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${Math.round(value / 1024)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(value?: string | null) {
  if (!value) return 'Never';
  return new Date(value).toLocaleString();
}

export default function AdminPage() {
  const { user } = useAuth();
  const items = useLibraryStore((state) => state.items);
  const [dashboard, setDashboard] = useState<AdminDashboard | null>(null);
  const [backup, setBackup] = useState<AdminBackupStatus | null>(null);
  const [backupResult, setBackupResult] = useState<AdminBackupRunResult | null>(null);
  const [processingJobs, setProcessingJobs] = useState<AdminProcessingJob[]>([]);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [backupBusy, setBackupBusy] = useState(false);
  const [processingBusy, setProcessingBusy] = useState(false);
  const [error, setError] = useState('');
  const [action, setAction] = useState<AdminAction>(null);
  const [backupConfirmOpen, setBackupConfirmOpen] = useState(false);
  const [processingConfirm, setProcessingConfirm] = useState<AdminProcessingJob | null>(null);

  const demoDashboard = useMemo<AdminDashboard>(() => ({
    users_total: 1,
    active_users: 1,
    disabled_users: 0,
    admin_users: 1,
    items_total: items.filter((item) => !item.deleted_at).length,
    archived_items: items.filter((item) => item.is_archived).length,
    assets_total: items.flatMap((item) => item.assets).length,
    storage_bytes: items.flatMap((item) => item.assets).reduce((total, asset) => total + asset.size_bytes, 0),
    processing_pending: items.filter((item) => ['pending', 'processing'].includes(item.processing_status)).length,
    processing_failed: items.filter((item) => item.processing_status === 'failed').length,
    analysis_pending: items.filter((item) => ['pending', 'analyzing'].includes(item.analysis_status)).length,
    analysis_failed: items.filter((item) => item.analysis_status === 'failed').length,
  }), [items]);

  const demoProcessingJobs = useMemo<AdminProcessingJob[]>(() => (
    items
      .filter((item) => ['pending', 'processing', 'failed'].includes(item.processing_status))
      .slice(0, 8)
      .map((item, index) => ({
        id: `demo-job-${item.id}`,
        item_id: item.id,
        item_title: item.title || item.url || item.raw_text?.slice(0, 80) || 'Untitled item',
        item_type: item.type,
        item_processing_status: item.processing_status,
        user_id: user?.id || 'demo-user',
        user_email: user?.email || 'demo@example.com',
        status: item.processing_status === 'failed'
          ? 'failed'
          : item.processing_status === 'processing'
            ? 'processing'
            : 'pending',
        attempts: item.processing_status === 'failed' ? 3 : index % 2,
        max_attempts: 3,
        next_attempt_at: item.updated_at,
        locked_at: item.processing_status === 'processing' ? item.updated_at : null,
        last_error: item.processing_error,
        created_at: item.created_at,
        updated_at: item.updated_at,
        completed_at: null,
      }))
  ), [items, user]);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      if (demoMode && user) {
        setDashboard(demoDashboard);
        setUsers([{
          ...user,
          item_count: demoDashboard.items_total,
          asset_count: demoDashboard.assets_total,
          storage_bytes: demoDashboard.storage_bytes,
        }]);
        setBackup({
          configured: false,
          command: null,
          backup_root: 'backups',
          retention_days: 14,
          latest: null,
          recent: [],
        });
        setProcessingJobs(demoProcessingJobs);
        return;
      }
      const [nextDashboard, userPage, backupStatus, processingPage] = await Promise.all([
        adminApi.dashboard(),
        adminApi.users(),
        adminApi.backupStatus(),
        adminApi.processingJobs({ limit: 12 }),
      ]);
      setDashboard(nextDashboard);
      setUsers(userPage.users);
      setBackup(backupStatus);
      setProcessingJobs(processingPage.jobs);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Unable to load admin data');
    } finally {
      setLoading(false);
    }
  }, [demoDashboard, demoProcessingJobs, user]);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  const confirmAction = async () => {
    if (!action) return;
    setBusy(true);
    setError('');
    try {
      if (demoMode) {
        setUsers((records) => records
          .filter((record) => action.kind !== 'delete' || record.id !== action.user.id)
          .map((record) => {
            if (record.id !== action.user.id) return record;
            if (action.kind === 'role') return { ...record, role: action.role };
            return { ...record, is_active: action.kind === 'enable' };
          }));
      } else if (action.kind === 'delete') {
        await adminApi.removeUser(action.user.id);
        await load();
      } else if (action.kind === 'role') {
        await adminApi.updateUser(action.user.id, { role: action.role });
        await load();
      } else {
        await adminApi.updateUser(action.user.id, { is_active: action.kind === 'enable' });
        await load();
      }
      setAction(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Admin action failed');
    } finally {
      setBusy(false);
    }
  };

  const confirmBackup = async () => {
    setBackupBusy(true);
    setError('');
    try {
      if (demoMode) return;
      const result = await adminApi.runBackup();
      setBackupResult(result);
      setBackup(await adminApi.backupStatus());
      setBackupConfirmOpen(false);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Backup failed');
    } finally {
      setBackupBusy(false);
    }
  };

  const confirmProcessingRetry = async () => {
    if (!processingConfirm) return;
    setProcessingBusy(true);
    setError('');
    try {
      if (demoMode) {
        setProcessingJobs((records) => records.map((record) => (
          record.id === processingConfirm.id
            ? { ...record, status: 'pending', attempts: 0, last_error: null, item_processing_status: 'pending' }
            : record
        )));
      } else {
        await adminApi.retryProcessingJob(processingConfirm.id);
        await load();
      }
      setProcessingConfirm(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Processing retry failed');
    } finally {
      setProcessingBusy(false);
    }
  };

  const actionLabel = (() => {
    if (!action) return '';
    if (action.kind === 'disable') return 'Disable';
    if (action.kind === 'enable') return 'Enable';
    if (action.kind === 'delete') return 'Delete';
    if (action.kind === 'role') return action.role === 'admin' ? 'Promote' : 'Demote';
    return '';
  })();

  const chartRows = dashboard ? [
    { label: 'Active users', value: dashboard.active_users, max: dashboard.users_total || 1 },
    { label: 'Archived items', value: dashboard.archived_items, max: dashboard.items_total || 1 },
    { label: 'Processing queue', value: dashboard.processing_pending, max: Math.max(dashboard.processing_pending, dashboard.items_total, 1) },
    { label: 'Analysis queue', value: dashboard.analysis_pending, max: Math.max(dashboard.analysis_pending, dashboard.items_total, 1) },
  ] : [];

  return (
    <div className="page admin-page">
      <header className="page-header">
        <div>
          <span className="eyebrow">Administration</span>
          <h1>Admin</h1>
          <p>System health and user access</p>
        </div>
        <button className="button secondary" type="button" onClick={() => void load()} disabled={loading}>
          <BarChart3 size={17} />
          Refresh
        </button>
      </header>

      {error && <div className="form-error" role="alert">{error}</div>}
      {loading && !dashboard ? (
        <section className="empty-state" aria-label="Loading admin dashboard"><span className="brand-loader" /></section>
      ) : dashboard && (
        <>
          <section className="admin-metrics" aria-label="Admin metrics">
            <div><Users size={18} /><span>Users</span><strong>{dashboard.users_total}</strong></div>
            <div><ShieldCheck size={18} /><span>Admins</span><strong>{dashboard.admin_users}</strong></div>
            <div><Database size={18} /><span>Items</span><strong>{dashboard.items_total}</strong></div>
            <div><HardDrive size={18} /><span>Storage</span><strong>{formatBytes(dashboard.storage_bytes)}</strong></div>
          </section>

          <section className="admin-panel" aria-labelledby="admin-health-heading">
            <div className="section-heading">
              <div><BarChart3 size={19} /><h2 id="admin-health-heading">Operational Snapshot</h2></div>
              <span>{dashboard.processing_failed} failed jobs, {dashboard.analysis_failed} failed analyses</span>
            </div>
            <div className="admin-bars">
              {chartRows.map((row) => (
                <div key={row.label} className="admin-bar-row">
                  <span>{row.label}</span>
                  <i><b style={{ width: `${Math.min((row.value / row.max) * 100, 100)}%` }} /></i>
                  <strong>{row.value}</strong>
                </div>
              ))}
            </div>
          </section>

          <section className="admin-panel" aria-labelledby="admin-backup-heading">
            <div className="section-heading">
              <div><Archive size={19} /><h2 id="admin-backup-heading">Backups</h2></div>
              <span>{backup?.configured ? 'Runnable' : 'Configure command'}</span>
            </div>
            <div className="admin-backup-layout">
              <div className="admin-backup-card">
                <Database size={18} />
                <span>Latest backup</span>
                <strong>{formatDate(backup?.latest?.created_at)}</strong>
                <small>{backup?.latest ? `${formatBytes(backup.latest.size_bytes)} in ${backup.latest.path}` : `Watching ${backup?.backup_root || 'backups'}`}</small>
              </div>
              <div className="admin-backup-card">
                <HardDrive size={18} />
                <span>Retention</span>
                <strong>{backup?.retention_days ?? 14} days</strong>
                <small>{backup?.recent.length ?? 0} recent backup records visible to the API</small>
              </div>
              <div className="admin-backup-command">
                <div><Terminal size={17} /><span>{backup?.command || 'Set ADMIN_BACKUP_COMMAND to enable admin-triggered backups.'}</span></div>
                <button
                  className="button primary"
                  type="button"
                  disabled={!backup?.configured || backupBusy}
                  onClick={() => setBackupConfirmOpen(true)}
                >
                  <PlayCircle size={17} />
                  {backupBusy ? 'Running' : 'Run backup'}
                </button>
              </div>
            </div>
            {backupResult ? (
              <p className="admin-backup-result">Backup completed in {backupResult.duration_seconds.toFixed(1)}s. Exit code {backupResult.exit_code}.</p>
            ) : null}
            {backup?.recent.length ? (
              <div className="admin-backup-list">
                {backup.recent.map((record) => (
                  <div key={record.path} className="admin-backup-row">
                    <strong>{formatDate(record.created_at)}</strong>
                    <span>{formatBytes(record.size_bytes)}</span>
                    <span>{record.has_postgres_dump ? 'DB dump' : 'Missing DB dump'}</span>
                    <span>{record.has_minio_dir ? 'Assets' : 'Missing assets dir'}</span>
                    <span>{record.has_checksums ? 'Checksums' : 'Missing checksums'}</span>
                  </div>
                ))}
              </div>
            ) : null}
          </section>

          <section className="admin-panel" aria-labelledby="admin-processing-heading">
            <div className="section-heading">
              <div><RefreshCw size={19} /><h2 id="admin-processing-heading">Processing Queue</h2></div>
              <span>{processingJobs.length} recent jobs</span>
            </div>
            {processingJobs.length ? (
              <div className="admin-processing-table">
                {processingJobs.map((record) => (
                  <div className="admin-processing-row" key={record.id}>
                    <div>
                      <strong>{record.item_title || 'Untitled item'}</strong>
                      <small>{record.item_type} item</small>
                    </div>
                    <span className="admin-processing-user">{record.user_email}</span>
                    <span className={`job-status-badge ${record.status}`}>{record.status}</span>
                    <span>{record.attempts}/{record.max_attempts}</span>
                    <span className="admin-processing-next"><Clock size={13} /> {formatDate(record.next_attempt_at)}</span>
                    <small className="admin-processing-error">
                      {record.last_error ? <><AlertTriangle size={13} /> {record.last_error}</> : 'No error recorded'}
                    </small>
                    <div className="admin-processing-actions">
                      <button
                        className="button secondary"
                        type="button"
                        disabled={record.status !== 'failed' || processingBusy}
                        onClick={() => setProcessingConfirm(record)}
                      >
                        <RefreshCw size={15} />
                        Retry
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="admin-empty">No active or failed processing jobs.</div>
            )}
          </section>

          <section className="admin-panel" aria-labelledby="admin-users-heading">
            <div className="section-heading">
              <div><UserCog size={19} /><h2 id="admin-users-heading">Users</h2></div>
              <span>{users.length}</span>
            </div>
            <div className="admin-user-table">
              {users.map((record) => {
                const isSelf = record.id === user?.id;
                const nextRole = record.role === 'admin' ? 'user' : 'admin';
                return (
                  <div className="admin-user-row" key={record.id}>
                    <span className="avatar"><UserRound size={16} /></span>
                    <div>
                      <strong>{record.name || record.email}</strong>
                      <small>{record.email}</small>
                    </div>
                    <span className={`role-badge ${record.role}`}>{record.role}</span>
                    <span className={record.is_active ? 'status-badge active' : 'status-badge disabled'}>
                      {record.is_active ? 'Active' : 'Disabled'}
                    </span>
                    <span>{record.item_count} items</span>
                    <span>{formatBytes(record.storage_bytes)}</span>
                    <div className="admin-row-actions">
                      <button
                        className="button secondary"
                        type="button"
                        disabled={isSelf}
                        onClick={() => setAction({ kind: record.is_active ? 'disable' : 'enable', user: record })}
                      >
                        <UserX size={15} />
                        {record.is_active ? 'Disable' : 'Enable'}
                      </button>
                      <button
                        className="button secondary"
                        type="button"
                        disabled={isSelf}
                        onClick={() => setAction({ kind: 'role', user: record, role: nextRole })}
                      >
                        {nextRole === 'admin' ? 'Promote' : 'Demote'}
                      </button>
                      <button
                        className="button danger"
                        type="button"
                        disabled={isSelf}
                        onClick={() => setAction({ kind: 'delete', user: record })}
                      >
                        <Trash2 size={15} />
                        Delete
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        </>
      )}

      {action && (
        <ConfirmDialog
          title={`${actionLabel} user?`}
          description={`${action.user.email} will be ${action.kind === 'role' ? `changed to ${action.role}` : action.kind === 'delete' ? 'deleted with their data' : `${action.kind}d`}.`}
          confirmLabel={actionLabel}
          danger={action.kind === 'delete' || action.kind === 'disable'}
          busy={busy}
          onCancel={() => setAction(null)}
          onConfirm={confirmAction}
        />
      )}
      {backupConfirmOpen && (
        <ConfirmDialog
          title="Run backup?"
          description="The configured operations command will create a PostgreSQL and object-storage backup. This can take several minutes."
          confirmLabel="Run backup"
          busy={backupBusy}
          onCancel={() => setBackupConfirmOpen(false)}
          onConfirm={confirmBackup}
        />
      )}
      {processingConfirm && (
        <ConfirmDialog
          title="Retry processing?"
          description={`${processingConfirm.item_title || 'This item'} will be added back to the processing queue.`}
          confirmLabel="Retry"
          busy={processingBusy}
          onCancel={() => setProcessingConfirm(null)}
          onConfirm={confirmProcessingRetry}
        />
      )}
    </div>
  );
}
