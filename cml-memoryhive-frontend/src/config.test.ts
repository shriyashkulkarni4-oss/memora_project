import { afterEach, describe, expect, it, vi } from 'vitest';

async function loadConfig() {
  vi.resetModules();
  return import('./config');
}

afterEach(() => {
  vi.unstubAllEnvs();
  vi.resetModules();
});

describe('frontend config', () => {
  it('uses a configured public support email', async () => {
    vi.stubEnv('VITE_SUPPORT_EMAIL', 'help@memoryhive.com');

    const config = await loadConfig();

    expect(config.SUPPORT_EMAIL).toBe('help@memoryhive.com');
    expect(config.SUPPORT_MAILTO).toBe('mailto:help@memoryhive.com');
  });

  it('falls back when the configured support email is blank', async () => {
    vi.stubEnv('VITE_SUPPORT_EMAIL', '   ');

    const config = await loadConfig();

    expect(config.SUPPORT_EMAIL).toBe('support@memoryhive.example.com');
    expect(config.SUPPORT_MAILTO).toBe('mailto:support@memoryhive.example.com');
  });
});
