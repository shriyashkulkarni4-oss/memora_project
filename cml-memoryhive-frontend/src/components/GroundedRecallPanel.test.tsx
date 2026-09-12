// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { itemsApi } from '../services/api';
import GroundedRecallPanel from './GroundedRecallPanel';

vi.mock('../services/api', () => ({ itemsApi: { recall: vi.fn() } }));

describe('GroundedRecallPanel', () => {
  beforeEach(() => vi.stubEnv('VITE_GROUNDED_RECALL_ENABLED', 'true'));
  afterEach(() => {
    cleanup();
    vi.unstubAllEnvs();
    vi.clearAllMocks();
  });

  it('renders an answer with a working saved-item citation', async () => {
    vi.mocked(itemsApi.recall).mockResolvedValue({
      answer: 'Temporal preserves event history. [1]',
      claims: [{ text: 'Temporal preserves event history.', citation_ids: [1] }],
      citations: [{ citation_id: 1, item_id: 'item-1', title: 'Temporal note', passage: 'Temporal preserves event history.' }],
      insufficient_evidence: false,
      provider: 'ollama',
      model: 'test',
      latency_ms: 12,
    });
    render(<MemoryRouter><GroundedRecallPanel /></MemoryRouter>);
    fireEvent.change(screen.getByPlaceholderText('What have I saved about…?'), { target: { value: 'What does Temporal preserve?' } });
    fireEvent.click(screen.getByLabelText('Ask memories'));
    await waitFor(() => expect(screen.getByText('Temporal preserves event history. [1]')).toBeTruthy());
    expect(screen.getByRole('link', { name: '[1] Temporal note' }).getAttribute('href')).toBe('/items/item-1');
    expect(screen.getByText(/No web search was used/)).toBeTruthy();
  });
});
