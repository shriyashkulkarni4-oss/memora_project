import { expect, test } from '@playwright/test';
import path from 'node:path';

test('server-backed capture and lifecycle workflow', async ({ page }) => {
  const email = `browser-${Date.now()}@example.com`;
  await page.goto('/register');
  await page.getByRole('textbox', { name: 'Name Optional' }).fill('Browser User');
  await page.getByRole('textbox', { name: 'Email' }).fill(email);
  await page.getByLabel('Password').fill('correct-horse-battery');
  await page.getByRole('button', { name: 'Create account' }).click();
  await expect(page.getByRole('heading', { name: 'Library' })).toBeVisible();
  await expect(page.getByText('0 items')).toBeVisible();

  await page.getByRole('link', { name: 'Organize' }).first().click();
  await page.getByRole('textbox', { name: 'Category name' }).fill('Engineering');
  await page.getByRole('button', { name: 'Add' }).click();
  await expect(page.getByText('Engineering', { exact: true })).toBeVisible();

  await page.getByRole('button', { name: 'Capture' }).click();
  await page.getByRole('textbox', { name: 'URL' }).fill('https://example.com/reference');
  await page.getByRole('textbox', { name: 'Title Optional' }).fill('Live API reference');
  await page.getByRole('button', { name: 'Details' }).click();
  await page.getByRole('textbox', { name: /^Tags/ }).fill('integration, api');
  await page.getByRole('combobox', { name: 'Category' }).selectOption({ label: 'Engineering' });
  await page.getByRole('button', { name: 'Save item' }).click();
  await expect(page.getByRole('heading', { name: 'Live API reference' })).toBeVisible();

  await page.route('**/items/*/favorite', async (route) => {
    await route.fulfill({
      status: 503,
      contentType: 'application/json',
      body: JSON.stringify({ error: { code: 'unavailable', message: 'Synthetic service failure' } }),
    });
  }, { times: 1 });
  await page.getByTitle('Add to favorites').click();
  await expect(page.getByRole('alert')).toContainText('Synthetic service failure');
  await expect(page.getByTitle('Add to favorites')).toBeVisible();
  await page.getByRole('button', { name: 'Dismiss message' }).click();

  await page.getByTitle('Add to favorites').click();
  await page.getByRole('button', { name: 'Archive item' }).click();
  await page.getByRole('link', { name: 'Archive' }).first().click();
  await expect(page.getByRole('link', { name: 'Live API reference' })).toBeVisible();
  await page.getByRole('link', { name: 'Live API reference' }).click();
  await page.getByRole('button', { name: 'Restore item' }).click();

  await page.getByRole('button', { name: 'Capture' }).click();
  await page.getByRole('tab', { name: 'Text' }).click();
  await page.getByLabel('Text').fill('Persisted text is searchable after a full browser reload.');
  await page.getByRole('textbox', { name: 'Title Optional' }).fill('Persistent text note');
  await page.getByRole('button', { name: 'Save item' }).click();
  await expect(page.getByRole('heading', { name: 'Persistent text note' })).toBeVisible();
  await page.reload();
  await expect(page.getByRole('heading', { name: 'Persistent text note' })).toBeVisible();
  await page.evaluate(() => localStorage.setItem('memoryhive.accessToken', 'expired-access-token'));
  await page.reload();
  await expect(page.getByRole('heading', { name: 'Persistent text note' })).toBeVisible();

  await page.getByRole('button', { name: 'Capture' }).click();
  await page.getByRole('tab', { name: 'Screenshot' }).click();
  await page.locator('input[type="file"]').setInputFiles(path.resolve('public/fixtures/habits-capture.png'));
  await page.getByRole('textbox', { name: 'Title Optional' }).fill('Private screenshot');
  await page.getByRole('button', { name: 'Save item' }).click();
  await expect(page.getByRole('heading', { name: 'Private screenshot' })).toBeVisible();
  await page.getByRole('link', { name: 'Back' }).click();
  await expect(page.locator('.item-preview img')).toHaveCount(1);
  await expect(page.locator('.item-preview img')).toHaveJSProperty('naturalWidth', 972);

  await page.getByRole('searchbox', { name: /Search library/ }).fill('Persistent text');
  await page.getByRole('link', { name: 'Persistent text note' }).click();
  await page.getByRole('button', { name: 'Edit' }).click();
  await page.getByRole('textbox', { name: 'Title' }).fill('Edited persistent note');
  await page.getByRole('button', { name: 'Save' }).click();
  await expect(page.getByRole('heading', { name: 'Edited persistent note' })).toBeVisible();

  page.once('dialog', (dialog) => dialog.accept());
  await page.getByRole('button', { name: 'Delete item' }).click();
  await expect(page.getByRole('heading', { name: 'Library' })).toBeVisible();
  await page.getByRole('button', { name: 'Clear search' }).click();
  await expect(page.getByText('2 items')).toBeVisible();
});
