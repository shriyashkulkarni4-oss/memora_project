// @vitest-environment jsdom

import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { itemsApi } from '../services/api';
import type { Item } from '../types/api';
import MemoryConnectionsPanel from './MemoryConnectionsPanel';

vi.mock('../services/api', () => ({
  itemsApi: {
    related: vi.fn(),
    duplicates: vi.fn(),
  },
}));

afterEach(cleanup);

const item = { id: 'related-1', title: 'Durable recovery', source_domain: null } as Item;

describe('MemoryConnectionsPanel', () => {
  it('explains related and duplicate candidates without automatic merging', async () => {
    vi.mocked(itemsApi.related).mockResolvedValue([{ item, score: 0.8, reasons: ['shared concepts: temporal'], semantic_score: 0.9 }]);
    vi.mocked(itemsApi.duplicates).mockResolvedValue([{ item: { ...item, id: 'duplicate-1' }, score: 1, reasons: ['same normalized content'], semantic_score: null, duplicate_kind: 'exact_content' }]);

    render(<MemoryRouter><MemoryConnectionsPanel itemId="source" /></MemoryRouter>);

    expect(await screen.findByRole('region', { name: 'Memory connections' })).toBeTruthy();
    expect(screen.getByText(/Nothing is merged automatically/)).toBeTruthy();
    expect(screen.getByText('shared concepts: temporal')).toBeTruthy();
  });
});
