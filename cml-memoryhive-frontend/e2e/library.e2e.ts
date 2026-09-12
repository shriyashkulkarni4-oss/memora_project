import { expect, test } from '@playwright/test';

test('library and capture remain usable at the target viewport', async ({ page }, testInfo) => {
  await page.goto('/');

  await expect(page.getByRole('heading', { name: 'Library' })).toBeVisible();
  await expect(page.getByRole('article')).toHaveCount(4);
  await expect(page.locator('.item-preview img')).toHaveJSProperty('complete', true);

  const viewportFits = await page.evaluate(
    () => document.documentElement.scrollWidth <= window.innerWidth,
  );
  expect(viewportFits).toBe(true);
  const summaryLabelsFit = await page.locator('.library-summary > span').evaluateAll(
    (labels) => labels.every((label) => label.scrollWidth <= label.clientWidth),
  );
  expect(summaryLabelsFit).toBe(true);

  const libraryPath = `/tmp/memoryhive-library-${testInfo.project.name}.png`;
  await page.screenshot({ path: libraryPath, fullPage: true });

  const captureButton = testInfo.project.name === 'mobile'
    ? page.getByRole('button', { name: 'Capture item' })
    : page.locator('.page-header').getByRole('button', { name: 'Capture' });
  await captureButton.click();
  await expect(page.getByRole('dialog', { name: 'Save to Memoryhive' })).toBeVisible();
  await page.getByRole('tab', { name: 'Text' }).click();
  await page.getByLabel('Text').fill('A browser-tested capture that remains readable at every viewport.');
  await page.getByRole('textbox', { name: 'Title Optional' }).fill('Browser-tested capture');
  await page.getByRole('button', { name: 'Save item' }).click();
  await expect(page.getByRole('heading', { name: 'Browser-tested capture' })).toBeVisible();

  const path = `/tmp/memoryhive-detail-${testInfo.project.name}.png`;
  await page.screenshot({ path, fullPage: true });
  testInfo.attachments.push({ name: 'viewport', path, contentType: 'image/png' });
});

test('AI explanations, suggestions, provenance, and degraded states remain visible', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('link', { name: 'Building durable habits' }).click();
  await expect(page.getByText('AI suggestions')).toBeVisible();
  await expect(page.getByText('ollama / fixture-local')).toBeVisible();
  await page.getByRole('button', { name: 'Accept practice' }).click();
  await expect(page.getByText('accepted')).toBeVisible();
  await page.getByRole('button', { name: 'Undo' }).click();
  await expect(page.getByText('pending').first()).toBeVisible();

  await page.getByRole('link', { name: 'Back' }).click();
  await page.getByRole('searchbox', { name: /Search library/ }).fill('Recognition');
  await expect(page.getByLabel('Why this result matched')).toContainText('semantic passage');

  await page.getByRole('searchbox', { name: /Search library/ }).fill('Patterns of distributed systems');
  await page.getByRole('link', { name: 'Patterns of distributed systems' }).click();
  await expect(page.getByText('degraded', { exact: true })).toBeVisible();
  await expect(page.getByText('provider_unavailable')).toBeVisible();
});
