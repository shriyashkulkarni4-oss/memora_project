import { KeyboardEvent, useMemo, useState } from 'react';
import type { ManagedTag } from '../types/api';
import FilterPills from './FilterPills';

function normalizeTag(value: string) {
  return value.trim().toLowerCase().replace(/\s+/g, ' ');
}

export default function TagPicker({
  label = 'Tags',
  selected,
  available,
  onChange,
  onInputChange,
}: {
  label?: string;
  selected: string[];
  available: ManagedTag[];
  onChange: (tags: string[]) => void;
  onInputChange?: (value: string) => void;
}) {
  const [input, setInput] = useState('');
  const selectedSet = useMemo(() => new Set(selected.map(normalizeTag)), [selected]);
  const value = normalizeTag(input);
  const suggestions = useMemo(() => available
    .filter((tag) => !selectedSet.has(normalizeTag(tag.name)))
    .filter((tag) => !value || tag.name.toLowerCase().includes(value))
    .slice(0, 6), [available, selectedSet, value]);

  const addTag = (raw: string) => {
    const tag = normalizeTag(raw);
    if (!tag || selectedSet.has(tag)) return;
    onChange([...selected, tag].sort());
    setInput('');
    onInputChange?.('');
  };

  const removeTag = (tag: string) => {
    onChange(selected.filter((name) => normalizeTag(name) !== normalizeTag(tag)));
  };

  const addPendingTags = () => {
    if (!input.trim()) return;
    const next = new Set(selected.map(normalizeTag));
    input.split(',').map(normalizeTag).filter(Boolean).forEach((tag) => next.add(tag));
    onChange([...next].sort());
    setInput('');
    onInputChange?.('');
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key !== 'Enter' && event.key !== ',') return;
    event.preventDefault();
    addPendingTags();
  };

  return (
    <div className="tag-picker">
      <label className="field">
        <span>{label}</span>
        <input
          value={input}
          onBlur={addPendingTags}
          onChange={(event) => {
            setInput(event.target.value);
            onInputChange?.(event.target.value);
          }}
          onKeyDown={handleKeyDown}
          placeholder="Search or add tag"
        />
      </label>
      <FilterPills
        pills={selected.map((tag) => ({
          id: tag,
          label: `#${tag}`,
          onRemove: () => removeTag(tag),
        }))}
      />
      {suggestions.length ? (
        <div className="tag-suggestions" aria-label="Tag suggestions">
          {suggestions.map((tag) => (
            <button key={tag.id} type="button" onClick={() => addTag(tag.name)}>
              <i style={{ background: tag.color }} />
              #{tag.name}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}
