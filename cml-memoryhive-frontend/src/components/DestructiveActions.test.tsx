// @vitest-environment jsdom

import { cleanup, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { fixtureCategories, fixtureItems, fixtureTags } from '../data/fixtures';
import { AuthProvider } from '../hooks/useAuth';
import { accountApi } from '../services/api';
import { useLibraryStore } from '../store/libraryStore';
import ItemDetailPage from './ItemDetailPage';
import OrganizationPage from './OrganizationPage';
import SettingsPage from './SettingsPage';

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
    initialized: true,
  });
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe('destructive action confirmations', () => {
  it('keeps an item until its detail-page deletion is confirmed', async () => {
    const user = userEvent.setup();
    const target = fixtureItems[2];
    render(
      <MemoryRouter initialEntries={[`/items/${target.id}`]}>
        <Routes>
          <Route path="/items/:id" element={<ItemDetailPage />} />
          <Route path="/" element={<p>Library destination</p>} />
        </Routes>
      </MemoryRouter>,
    );

    await user.click(screen.getByRole('button', { name: 'Delete item' }));
    expect(screen.getByRole('dialog', { name: 'Delete item?' })).toBeTruthy();
    await user.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(useLibraryStore.getState().items.some((item) => item.id === target.id)).toBe(true);

    await user.click(screen.getByRole('button', { name: 'Delete item' }));
    await user.click(screen.getByRole('button', { name: 'Delete' }));
    expect(await screen.findByText('Library destination')).toBeTruthy();
    expect(useLibraryStore.getState().items.some((item) => item.id === target.id)).toBe(false);
  });

  it('confirms category deletion and detaches affected items', async () => {
    const user = userEvent.setup();
    const category = fixtureCategories[0];
    render(<MemoryRouter><OrganizationPage /></MemoryRouter>);

    await user.click(screen.getByRole('button', { name: `Delete ${category.name}` }));
    expect(screen.getByRole('dialog', { name: 'Delete category?' })).toBeTruthy();
    await user.click(screen.getByRole('button', { name: 'Delete' }));

    expect(useLibraryStore.getState().categories.some((record) => record.id === category.id)).toBe(false);
    expect(useLibraryStore.getState().items.some((item) => item.category_id === category.id)).toBe(false);
  });

  it('cancels tag deletion without changing item tags', async () => {
    const user = userEvent.setup();
    const tag = fixtureTags[0];
    render(<MemoryRouter><OrganizationPage /></MemoryRouter>);

    await user.click(screen.getByRole('button', { name: `Delete ${tag.name}` }));
    expect(screen.getByRole('dialog', { name: 'Delete tag?' })).toBeTruthy();
    await user.click(screen.getByRole('button', { name: 'Cancel' }));

    expect(useLibraryStore.getState().tags.some((record) => record.id === tag.id)).toBe(true);
    expect(useLibraryStore.getState().items.some((item) => item.tags.some((record) => record.id === tag.id))).toBe(true);
  });

  it('requires password and exact typed confirmation before account deletion', async () => {
    const user = userEvent.setup();
    const remove = vi.spyOn(accountApi, 'remove').mockResolvedValue(undefined);
    render(
      <MemoryRouter initialEntries={['/settings']}>
        <AuthProvider>
          <Routes>
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/login" element={<p>Login destination</p>} />
          </Routes>
        </AuthProvider>
      </MemoryRouter>,
    );

    await user.click(screen.getByRole('button', { name: 'Delete account' }));
    const dialog = screen.getByRole('dialog', { name: 'Delete account' });
    const submit = within(dialog).getByRole('button', { name: 'Delete permanently' });
    expect((submit as HTMLButtonElement).disabled).toBe(true);

    await user.type(within(dialog).getByLabelText('Password'), 'correct-password');
    await user.type(within(dialog).getByLabelText('Type DELETE to confirm'), 'DELETE');
    expect((submit as HTMLButtonElement).disabled).toBe(false);
    await user.click(submit);

    await waitFor(() => expect(remove).toHaveBeenCalledWith('correct-password'));
    expect(await screen.findByText('Login destination')).toBeTruthy();
  });
});
