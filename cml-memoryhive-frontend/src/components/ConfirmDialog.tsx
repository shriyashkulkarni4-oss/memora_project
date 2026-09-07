import { AlertTriangle } from 'lucide-react';

export default function ConfirmDialog({
  title,
  description,
  confirmLabel,
  cancelLabel = 'Cancel',
  danger = false,
  busy = false,
  onCancel,
  onConfirm,
}: {
  title: string;
  description: string;
  confirmLabel: string;
  cancelLabel?: string;
  danger?: boolean;
  busy?: boolean;
  onCancel: () => void;
  onConfirm: () => void | Promise<void>;
}) {
  return (
    <div className="dialog-layer" role="presentation" onMouseDown={() => !busy && onCancel()}>
      <section
        className="confirm-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="confirm-title"
        aria-describedby="confirm-description"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="confirm-dialog-header">
          <span className={danger ? 'confirm-icon danger' : 'confirm-icon'}>
            <AlertTriangle size={19} />
          </span>
          <div>
            <h2 id="confirm-title">{title}</h2>
            <p id="confirm-description">{description}</p>
          </div>
        </header>
        <footer className="dialog-actions">
          <button className="button secondary" type="button" disabled={busy} onClick={onCancel}>
            {cancelLabel}
          </button>
          <button className={danger ? 'button danger' : 'button primary'} type="button" disabled={busy} onClick={() => void onConfirm()}>
            {busy ? 'Working' : confirmLabel}
          </button>
        </footer>
      </section>
    </div>
  );
}
