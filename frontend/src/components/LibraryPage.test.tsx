// @vitest-environment jsdom

import axe from 'axe-core';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
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
      'durable',
      'notes',
    ]);
    expect(screen.queryByRole('dialog')).toBeNull();

    useLibraryStore.getState().setCaptureOpen(true);
    await waitFor(() => expect(screen.getByRole('dialog')).toBeTruthy());
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(screen.queryByRole('dialog')).toBeNull();
  });

  it('uses summary filters and removable active filter pills', async () => {
    const user = userEvent.setup();
    renderLibrary();

    expect(screen.getAllByRole('article')).toHaveLength(4);
    await user.click(screen.getByRole('button', { name: /2 favorites/i }));
    expect(screen.getAllByRole('article')).toHaveLength(2);
    expect(screen.getByText('Favorites')).toBeTruthy();

    await user.click(screen.getByRole('button', { name: 'Remove Favorites' }));
    expect(screen.getAllByRole('article')).toHaveLength(4);
  });

  it('confirms favorite changes from item cards', async () => {
    const user = userEvent.setup();
    renderLibrary();

    const target = useLibraryStore.getState().items.find((item) => item.title === 'Capture should disappear');
    expect(target?.is_favorite).toBe(false);

    await user.click(screen.getAllByRole('button', { name: 'Add to favorites' })[0]);
    expect(screen.getByRole('dialog', { name: 'Add favorite?' })).toBeTruthy();
    await user.click(screen.getByRole('button', { name: 'Add favorite' }));

    expect(useLibraryStore.getState().items.find((item) => item.id === target?.id)?.is_favorite).toBe(true);
  });

  it('cancels and confirms archive changes from item cards', async () => {
    const user = userEvent.setup();
    renderLibrary();

    const target = useLibraryStore.getState().items.find((item) => item.title === 'Capture should disappear');
    const targetCard = screen.getByText('Capture should disappear').closest('article');
    if (!targetCard) throw new Error('Expected target item card');

    await user.click(within(targetCard).getByRole('button', { name: 'Archive' }));
    expect(screen.getByRole('dialog', { name: 'Archive item?' })).toBeTruthy();
    await user.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(useLibraryStore.getState().items.find((item) => item.id === target?.id)?.is_archived).toBe(false);

    await user.click(within(targetCard).getByRole('button', { name: 'Archive' }));
    const confirmation = screen.getByRole('dialog', { name: 'Archive item?' });
    await user.click(within(confirmation).getByRole('button', { name: 'Archive' }));
    expect(useLibraryStore.getState().items.find((item) => item.id === target?.id)?.is_archived).toBe(true);
  });

  it('has no detectable automated accessibility violations', async () => {
    const { container } = renderLibrary();
    const result = await axe.run(container, {
      rules: { 'color-contrast': { enabled: false } },
    });

    expect(result.violations).toEqual([]);
  });
});
