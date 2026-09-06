import { X } from 'lucide-react';

export interface FilterPill {
  id: string;
  label: string;
  onRemove: () => void;
}

export default function FilterPills({
  pills,
  onClear,
}: {
  pills: FilterPill[];
  onClear?: () => void;
}) {
  if (!pills.length) return null;

  return (
    <div className="filter-pills" aria-label="Active filters">
      {pills.map((pill) => (
        <span className="filter-pill" key={pill.id}>
          {pill.label}
          <button type="button" onClick={pill.onRemove} aria-label={`Remove ${pill.label}`}>
            <X size={13} />
          </button>
        </span>
      ))}
      {onClear && (
        <button className="clear-filter-pills" type="button" onClick={onClear}>
          Clear all
        </button>
      )}
    </div>
  );
}
