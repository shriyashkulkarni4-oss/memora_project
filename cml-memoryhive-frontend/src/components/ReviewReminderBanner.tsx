/**
 * ReviewReminderBanner
 *
 * Shows a reminder for items that are 3+ days old (demo; real = 7 days).
 * User gets 2 options per item:
 *  - Keep  → dismiss now, remind again in 10 days (demo; real = 30-40 days)
 *  - Delete → permanently delete the item from storage
 *
 * State is tracked per item in localStorage so reminders survive page reloads.
 */

import { Bell, Trash2, BookmarkCheck, X } from 'lucide-react';
import { useMemo, useState, useCallback, useRef } from 'react';
import type { Item } from '../types/api';
import { useLibraryStore } from '../store/libraryStore';

// ── Timing constants (demo values) ──────────────────────────────────────────
const FIRST_REMINDER_MS  = 3  * 24 * 60 * 60 * 1000; // 3 days  (real: 7 days)
const KEEP_REMINDER_MS   = 10 * 24 * 60 * 60 * 1000; // 10 days (real: 30-40 days)

// ── localStorage helpers ─────────────────────────────────────────────────────
const STORAGE_KEY = 'memoryhive:review-state-v2';

interface ItemReviewState {
  nextReminderAt?: number; // timestamp: when to show again after "Keep"
  deleted?: true;          // user chose to delete — never show again
}

type ReviewStateMap = Record<string, ItemReviewState>;

function loadState(): ReviewStateMap {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as ReviewStateMap) : {};
  } catch {
    return {};
  }
}

function saveState(state: ReviewStateMap): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch { /* ignore quota errors */ }
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function isDue(item: Item, state: ReviewStateMap): boolean {
  if (item.is_archived) return false;
  const entry = state[item.id];
  if (entry?.deleted) return false;

  const now = Date.now();
  if (entry?.nextReminderAt !== undefined) {
    // Already kept once — show again only when the 10-day window is up
    return now >= entry.nextReminderAt;
  }
  // First-time: show after 3 days from creation
  return now - new Date(item.created_at).getTime() >= FIRST_REMINDER_MS;
}

function formatRelative(isoString: string): string {
  const days = Math.floor((Date.now() - new Date(isoString).getTime()) / 86_400_000);
  if (days === 0) return 'today';
  if (days === 1) return 'yesterday';
  return `${days} days ago`;
}

// ── Component ─────────────────────────────────────────────────────────────────
interface Props {
  items: Item[];
}

export default function ReviewReminderBanner({ items }: Props) {
  const deleteItem = useLibraryStore((s) => s.deleteItem);

  // Local copy of review state — drives re-renders on user action
  const [reviewState, setReviewState] = useState<ReviewStateMap>(loadState);

  // Items currently needing attention
  const dueItems = useMemo(
    () => items.filter((item) => isDue(item, reviewState)),
    [items, reviewState],
  );

  // Track which cards are in a "confirming delete" state
  const [confirmingDelete, setConfirmingDelete] = useState<Set<string>>(new Set());

  // Track items being deleted (spinner state)
  const deletingRef = useRef<Set<string>>(new Set());
  const [, forceRender] = useState(0);

  const updateItemState = useCallback((id: string, patch: ItemReviewState) => {
    const next = { ...loadState(), [id]: { ...loadState()[id], ...patch } };
    saveState(next);
    setReviewState(next);
  }, []);

  // ── Keep ──────────────────────────────────────────────────────────────────
  const handleKeep = useCallback((id: string) => {
    updateItemState(id, { nextReminderAt: Date.now() + KEEP_REMINDER_MS });
  }, [updateItemState]);

  // ── Delete ────────────────────────────────────────────────────────────────
  const handleDelete = useCallback(async (id: string) => {
    deletingRef.current.add(id);
    forceRender((n) => n + 1);
    try {
      await deleteItem(id);
      updateItemState(id, { deleted: true });
    } catch {
      // store already shows error toast; just clear spinner
    } finally {
      deletingRef.current.delete(id);
      forceRender((n) => n + 1);
    }
  }, [deleteItem, updateItemState]);

  const toggleConfirmDelete = useCallback((id: string) => {
    setConfirmingDelete((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  if (dueItems.length === 0) return null;

  const MAX_VISIBLE = 3;
  const visible = dueItems.slice(0, MAX_VISIBLE);
  const overflow = dueItems.length - MAX_VISIBLE;

  return (
    <section className="review-reminder-section" aria-label="Review reminders">
      {/* ── Header ── */}
      <div className="review-reminder-header">
        <Bell size={15} aria-hidden="true" />
        <span>
          {dueItems.length === 1
            ? "It's been a while — review this saved item"
            : `${dueItems.length} saved items are waiting for your review`}
        </span>
      </div>

      {/* ── Cards ── */}
      <ul className="review-reminder-list" role="list">
        {visible.map((item) => {
          const isConfirming = confirmingDelete.has(item.id);
          const isDeleting   = deletingRef.current.has(item.id);
          const label = item.title || item.url || item.raw_text?.slice(0, 60) || 'Untitled item';

          return (
            <li key={item.id} className={`review-reminder-card${isConfirming ? ' confirming' : ''}`}>
              {/* Info */}
              <div className="review-reminder-card-body">
                <span className="review-reminder-title" title={label}>{label}</span>
                <span className="review-reminder-meta">
                  Saved {formatRelative(item.created_at)} · Review to keep or delete
                </span>
              </div>

              {/* Actions */}
              <div className="review-reminder-actions">
                {!isConfirming ? (
                  <>
                    {/* Keep */}
                    <button
                      type="button"
                      className="rrb-btn rrb-keep"
                      onClick={() => handleKeep(item.id)}
                      title="Keep this item — remind me again in 10 days"
                    >
                      <BookmarkCheck size={14} aria-hidden="true" />
                      Keep
                    </button>

                    {/* Delete (asks for confirmation) */}
                    <button
                      type="button"
                      className="rrb-btn rrb-delete-prompt"
                      onClick={() => toggleConfirmDelete(item.id)}
                      title="Delete this item permanently"
                    >
                      <Trash2 size={14} aria-hidden="true" />
                      Delete
                    </button>
                  </>
                ) : (
                  /* Confirmation strip */
                  <>
                    <span className="rrb-confirm-text">Delete permanently?</span>
                    <button
                      type="button"
                      className="rrb-btn rrb-confirm-yes"
                      disabled={isDeleting}
                      onClick={() => void handleDelete(item.id)}
                    >
                      {isDeleting ? 'Deleting…' : 'Yes, delete'}
                    </button>
                    <button
                      type="button"
                      className="rrb-btn rrb-confirm-no"
                      onClick={() => toggleConfirmDelete(item.id)}
                    >
                      <X size={13} aria-hidden="true" /> Cancel
                    </button>
                  </>
                )}
              </div>
            </li>
          );
        })}

        {/* Overflow indicator */}
        {overflow > 0 && (
          <li className="review-reminder-overflow">
            + {overflow} more item{overflow > 1 ? 's' : ''} need review
          </li>
        )}
      </ul>
    </section>
  );
}
