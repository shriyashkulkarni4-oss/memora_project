// @vitest-environment jsdom

import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import AccountDeletionPage from './AccountDeletionPage';
import PrivacyPage from './PrivacyPage';
import SupportPage from './SupportPage';

afterEach(cleanup);

describe('public compliance pages', () => {
  it('renders privacy policy content and account controls', () => {
    render(
      <MemoryRouter>
        <PrivacyPage />
      </MemoryRouter>,
    );

    expect(screen.getByRole('heading', { name: 'Privacy Policy' })).toBeTruthy();
    expect(screen.getByText(/Memoryhive stores account details/i)).toBeTruthy();
    expect(screen.getByRole('link', { name: 'Account deletion help' }).getAttribute('href')).toBe(
      '/account/delete',
    );
    expect(screen.getByRole('link', { name: 'Support' }).getAttribute('href')).toBe('/support');
    expect(screen.getByRole('link', { name: 'support@memoryhive.example.com' }).getAttribute('href')).toBe(
      'mailto:support@memoryhive.example.com',
    );
  });

  it('renders web account deletion instructions for uninstalled mobile users', () => {
    render(
      <MemoryRouter>
        <AccountDeletionPage />
      </MemoryRouter>,
    );

    expect(screen.getByRole('heading', { name: 'Delete Your Memoryhive Account' })).toBeTruthy();
    expect(screen.getByText(/even if the mobile app is no longer installed/i)).toBeTruthy();
    expect(screen.getByRole('link', { name: 'Open settings' }).getAttribute('href')).toBe('/settings');
    expect(screen.getByRole('link', { name: 'Support' }).getAttribute('href')).toBe('/support');
    expect(screen.getByRole('link', { name: 'support@memoryhive.example.com' }).getAttribute('href')).toBe(
      'mailto:support@memoryhive.example.com',
    );
  });

  it('renders public support contact and privacy links', () => {
    render(
      <MemoryRouter>
        <SupportPage />
      </MemoryRouter>,
    );

    expect(screen.getByRole('heading', { name: 'Memoryhive Support' })).toBeTruthy();
    expect(screen.getByRole('link', { name: 'support@memoryhive.example.com' }).getAttribute('href')).toBe(
      'mailto:support@memoryhive.example.com',
    );
    expect(screen.getByRole('link', { name: 'Privacy policy' }).getAttribute('href')).toBe('/privacy');
  });
});
