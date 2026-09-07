// @vitest-environment jsdom

import { act, cleanup, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { fixtureCategories, fixtureItems, fixtureTags } from '../data/fixtures';
import { AuthProvider } from '../hooks/useAuth';
import { useLibraryStore } from '../store/libraryStore';
import AppShell from './AppShell';
import AuthPage from './AuthPage';
import LibraryPage from './LibraryPage';

function renderAuthenticatedShell() {
  return render(
    <MemoryRouter initialEntries={['/']}>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<AppShell />}>
            <Route index element={<LibraryPage />} />
          </Route>
          <Route path="/login" element={<AuthPage mode="login" />} />
        </Routes>
      </AuthProvider>
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
    initialized: true,
  });
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

describe('app shell session handling', () => {
  it('clears library state and shows a message when the session expires', async () => {
    renderAuthenticatedShell();

    expect(await screen.findByRole('heading', { name: 'Library' })).toBeTruthy();
    window.dispatchEvent(new CustomEvent('memoryhive:session-expired', {
      detail: { message: 'Session expired from test.' },
    }));

    expect(await screen.findByRole('heading', { name: 'Welcome back' })).toBeTruthy();
    expect(screen.getByText('Session expired from test.')).toBeTruthy();
    expect(useLibraryStore.getState().items).toEqual([]);
  });

  it('logs out after ten minutes of inactivity', async () => {
    vi.useFakeTimers();
    renderAuthenticatedShell();

    await act(async () => {});
    expect(screen.getByRole('heading', { name: 'Library' })).toBeTruthy();
    await act(async () => {
      vi.advanceTimersByTime(10 * 60_000);
    });

    expect(screen.getByRole('heading', { name: 'Welcome back' })).toBeTruthy();
    expect(screen.getByText('Signed out after 10 minutes of inactivity.')).toBeTruthy();
  });
});
