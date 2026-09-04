# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: library.e2e.ts >> library and capture remain usable at the target viewport
- Location: e2e/library.e2e.ts:3:1

# Error details

```
Test timeout of 30000ms exceeded.
```

```
Error: locator.click: Test timeout of 30000ms exceeded.
Call log:
  - waiting for locator('.page-header').getByRole('button', { name: 'Capture' })

```

# Page snapshot

```yaml
- generic [ref=e3]:
  - banner [ref=e4]:
    - link "Memoryhive library" [ref=e5] [cursor=pointer]:
      - /url: /
      - generic [ref=e10]: Memoryhive
    - button "Capture item" [ref=e11] [cursor=pointer]
  - main [ref=e14]:
    - generic [ref=e15]:
      - generic [ref=e17]:
        - generic [ref=e18]: Personal knowledge
        - heading "Library" [level=1] [ref=e19]
        - paragraph [ref=e20]: 4 items
      - generic "Library summary" [ref=e21]:
        - generic [ref=e22]:
          - strong [ref=e23]: "4"
          - text: saved
        - generic [ref=e24]:
          - strong [ref=e27]: "2"
          - text: favorites
        - generic [ref=e28]:
          - strong [ref=e31]: "1"
          - text: processing
        - generic [ref=e32]:
          - strong [ref=e36]: "1"
          - text: archived
      - region "Library filters" [ref=e37]:
        - generic [ref=e38]:
          - generic [ref=e42]: Search library
          - searchbox "Search library" [ref=e43]
        - generic [ref=e44]:
          - generic "Item type" [ref=e45]:
            - button "All" [pressed] [ref=e46] [cursor=pointer]
            - button "Links" [ref=e47] [cursor=pointer]
            - button "Screenshots" [ref=e48] [cursor=pointer]
            - button "Text" [ref=e49] [cursor=pointer]
          - generic [ref=e50]:
            - generic [ref=e51]:
              - generic [ref=e52]: Category
              - combobox "Category" [ref=e53]:
                - option "All categories" [selected]
                - option "Research"
                - option "Ideas"
                - option "Design"
            - generic [ref=e54]:
              - generic [ref=e55]: Sort
              - combobox "Sort" [ref=e56]:
                - option "Newest first" [selected]
                - option "Oldest first"
                - option "Title"
      - generic [ref=e57]:
        - article [ref=e58]:
          - link [ref=e59] [cursor=pointer]:
            - /url: /items/0d74711b-70cf-4f45-935a-43c8bb08d83b
          - generic [ref=e60]:
            - generic [ref=e61]:
              - generic [ref=e62]: screenshot
              - generic [ref=e67]: about 10 hours ago
            - heading [level=2] [ref=e68]:
              - link "Building durable habits" [ref=e69] [cursor=pointer]:
                - /url: /items/0d74711b-70cf-4f45-935a-43c8bb08d83b
            - paragraph [ref=e70]: A visual habit system built around consistency and low-friction routines.
            - generic "Tags" [ref=e71]:
              - generic [ref=e72]: "#systems"
              - generic [ref=e73]: "#habits"
            - generic [ref=e74]:
              - generic [ref=e75]: screenshot
              - generic [ref=e76]:
                - button "Remove from favorites" [ref=e77] [cursor=pointer]
                - button "Archive" [ref=e81] [cursor=pointer]
        - article [ref=e86]:
          - generic [ref=e87]:
            - generic [ref=e88]:
              - generic [ref=e89]: link
              - generic [ref=e93]: about 16 hours ago
            - heading [level=2] [ref=e94]:
              - link "Recognition rather than recall" [ref=e95] [cursor=pointer]:
                - /url: /items/2fde1c9c-e002-43bf-b773-73f44a3f96a7
            - paragraph [ref=e96]: Make actions and choices visible so users can recognize options instead of recalling them.
            - generic "Tags" [ref=e97]:
              - generic [ref=e98]: "#product"
              - generic [ref=e99]: "#design"
            - generic [ref=e100]:
              - generic [ref=e101]: nngroup.com
              - generic [ref=e106]:
                - button "Remove from favorites" [ref=e107] [cursor=pointer]
                - button "Archive" [ref=e111] [cursor=pointer]
        - article [ref=e116]:
          - generic [ref=e117]:
            - generic [ref=e118]:
              - generic [ref=e119]: text
              - generic [ref=e123]: 1 day ago
            - heading [level=2] [ref=e124]:
              - link "Capture should disappear" [ref=e125] [cursor=pointer]:
                - /url: /items/5ce76e50-1bba-4c3e-a6fe-e1e294de68a0
            - blockquote [ref=e126]: A useful knowledge system should make capture nearly invisible and retrieval deliberate.
            - generic "Tags" [ref=e127]:
              - generic [ref=e128]: "#systems"
              - generic [ref=e129]: "#product"
            - generic [ref=e130]:
              - generic [ref=e131]: manual
              - generic [ref=e132]:
                - button "Add to favorites" [ref=e133] [cursor=pointer]
                - button "Archive" [ref=e137] [cursor=pointer]
        - article [ref=e142]:
          - generic [ref=e143]:
            - generic [ref=e144]:
              - generic [ref=e145]: link
              - generic [ref=e149]: Processing
              - generic [ref=e151]: 3 days ago
            - heading [level=2] [ref=e152]:
              - link "Patterns of distributed systems" [ref=e153] [cursor=pointer]:
                - /url: /items/d63b31cc-4ad8-4032-b681-033d03b3df65
            - paragraph [ref=e154]: A catalog of patterns for reliable distributed applications.
            - generic "Tags" [ref=e155]:
              - generic [ref=e156]: "#systems"
              - generic [ref=e157]: "#research"
            - generic [ref=e158]:
              - generic [ref=e159]: martinfowler.com
              - generic [ref=e164]:
                - button "Add to favorites" [ref=e165] [cursor=pointer]
                - button "Archive" [ref=e169] [cursor=pointer]
  - navigation "Mobile navigation" [ref=e174]:
    - link "Library" [ref=e175] [cursor=pointer]:
      - /url: /
    - link "Favorites" [ref=e179] [cursor=pointer]:
      - /url: /favorites
    - link "Archive" [ref=e183] [cursor=pointer]:
      - /url: /archive
    - link "Organize" [ref=e188] [cursor=pointer]:
      - /url: /organize
    - button "Search" [ref=e195] [cursor=pointer]
```

# Test source

```ts
  1  | import { expect, test } from '@playwright/test';
  2  | 
  3  | test('library and capture remain usable at the target viewport', async ({ page }, testInfo) => {
  4  |   await page.goto('/');
  5  | 
  6  |   await expect(page.getByRole('heading', { name: 'Library' })).toBeVisible();
  7  |   await expect(page.getByRole('article')).toHaveCount(4);
  8  |   await expect(page.locator('.item-preview img')).toHaveJSProperty('complete', true);
  9  | 
  10 |   const viewportFits = await page.evaluate(
  11 |     () => document.documentElement.scrollWidth <= window.innerWidth,
  12 |   );
  13 |   expect(viewportFits).toBe(true);
  14 | 
> 15 |   await page.locator('.page-header').getByRole('button', { name: 'Capture' }).click();
     |                                                                               ^ Error: locator.click: Test timeout of 30000ms exceeded.
  16 |   await expect(page.getByRole('dialog', { name: 'Save to Memoryhive' })).toBeVisible();
  17 |   await page.getByRole('tab', { name: 'Text' }).click();
  18 |   await page.getByLabel('Text').fill('A browser-tested capture that remains readable at every viewport.');
  19 |   await page.getByRole('textbox', { name: 'Title Optional' }).fill('Browser-tested capture');
  20 |   await page.getByRole('button', { name: 'Save item' }).click();
  21 |   await expect(page.getByRole('heading', { name: 'Browser-tested capture' })).toBeVisible();
  22 | 
  23 |   const path = `/tmp/memoryhive-${testInfo.project.name}.png`;
  24 |   await page.screenshot({ path, fullPage: true });
  25 |   testInfo.attachments.push({ name: 'viewport', path, contentType: 'image/png' });
  26 | });
  27 | 
```