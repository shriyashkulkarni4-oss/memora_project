// @vitest-environment jsdom

import axe from 'axe-core';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { fixtureCategories, fixtureItems, fixtureTags } from '../data/fixtures';
import { useLibraryStore } from '../store/libraryStore';
import CaptureDialog from './CaptureDialog';
import LibraryPage from './LibraryPage';

function renderLibrary() {
  return render(
    <MemoryRouter>
      <main>
        <LibraryPage />
      </main>
      <CaptureDialog />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  useLibraryStore.setState({
    items: fixtureItems,
    searchResults: null,
    categories: fixtureCategories,
    tags: fixtureTags,
    query: '',
    typeFilter: 'all',
    viewMode: 'grid',
    captureOpen: false,
  });
});

afterEach(cleanup);

describe('library experience', () => {
  it('filters captures by text and type', async () => {
    const user = userEvent.setup();
    renderLibrary();

    const search = screen.getByRole('searchbox', { name: 'Search library' });
    await user.type(search, 'distributed');
    expect(screen.getAllByRole('article')).toHaveLength(1);
    expect(screen.getByRole('link', { name: /Patterns of distributed systems/i })).toBeTruthy();

    await user.clear(search);
    await user.click(screen.getByRole('button', { name: 'Screenshots' }));
    expect(screen.getAllByRole('article')).toHaveLength(1);
    expect(screen.getByRole('link', { name: /Building durable habits/i })).toBeTruthy();
  });

  it('captures text with optional metadata and closes on Escape', async () => {
    const user = userEvent.setup();
    renderLibrary();

    await user.click(screen.getByRole('button', { name: 'Capture' }));
    expect(screen.getByRole('dialog', { name: 'Save to Memoryhive' })).toBeTruthy();
    await user.click(screen.getByRole('tab', { name: 'Text' }));
    await user.type(screen.getByLabelText('Text'), 'A durable note saved from the capture dialog.');
    await user.type(screen.getByLabelText(/Title/), 'Durable note');
    await user.click(screen.getByRole('button', { name: 'Details' }));
    await user.type(screen.getByRole('textbox', { name: /^Tags/ }), 'notes, durable');
    await user.click(screen.getByRole('button', { name: 'Save item' }));

    expect(useLibraryStore.getState().items[0].title).toBe('Durable note');
    expect(useLibraryStore.getState().items[0].tags.map((tag) => tag.name)).toEqual([
      'notes',
      'durable',
    ]);
    expect(screen.queryByRole('dialog')).toBeNull();

    useLibraryStore.getState().setCaptureOpen(true);
    await waitFor(() => expect(screen.getByRole('dialog')).toBeTruthy());
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(screen.queryByRole('dialog')).toBeNull();
  });

  it('has no detectable automated accessibility violations', async () => {
    const { container } = renderLibrary();
    const result = await axe.run(container, {
      rules: { 'color-contrast': { enabled: false } },
    });

    expect(result.violations).toEqual([]);
  });
});
