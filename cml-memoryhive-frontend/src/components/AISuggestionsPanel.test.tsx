// @vitest-environment jsdom

import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { Item } from '../types/api';
import AISuggestionsPanel from './AISuggestionsPanel';

afterEach(cleanup);

const item = {
  id: 'item-1',
  analysis_status: 'analyzed',
  analysis_version: 2,
  revision: 4,
  metadata: {
    enrichment: {
      suggested_tags: ['postgresql', 'database'],
      classification: 'reference',
      topics: ['query planning'],
      confidence: 0.94,
    },
  },
} as unknown as Item;

describe('AISuggestionsPanel', () => {
  it('shows tags separately and accepts all without changing historical output', async () => {
    const user = userEvent.setup();
    render(<AISuggestionsPanel item={item} onChanged={vi.fn()} />);
    expect(await screen.findByText('#postgresql')).toBeTruthy();
    expect(screen.getByText(/Classification:/)).toBeTruthy();
    expect(screen.getByText(/Topics:/)).toBeTruthy();
    await user.click(screen.getByRole('button', { name: 'Accept all' }));
    expect(screen.getAllByText(/accepted/).length).toBe(3);
    expect(item.metadata?.enrichment).toEqual({
      suggested_tags: ['postgresql', 'database'],
      classification: 'reference',
      topics: ['query planning'],
      confidence: 0.94,
    });
  });

  it('supports reject, never suggest, and undo', async () => {
    const user = userEvent.setup();
    render(<AISuggestionsPanel item={item} onChanged={vi.fn()} />);
    await screen.findByText('#postgresql');
    await user.click(screen.getByRole('button', { name: 'Reject database' }));
    expect(screen.getByText(/94% rejected/)).toBeTruthy();
    await user.click(screen.getAllByRole('button', { name: 'Never' })[0]);
    expect(screen.getByText(/94% never/)).toBeTruthy();
    await user.click(screen.getByRole('button', { name: 'Accept reference' }));
    await user.click(screen.getByRole('button', { name: /Undo/ }));
    expect(screen.getAllByText(/pending/).length).toBeGreaterThan(0);
  });
});
