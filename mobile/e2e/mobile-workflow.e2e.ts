import { expect, test } from "@playwright/test";

const password = "correct-horse-battery";
let disposableEmail: string | undefined;

test.afterEach(async ({ request }) => {
  if (!disposableEmail) return;
  const login = await request.post("http://127.0.0.1:8000/api/v1/auth/login", {
    data: { email: disposableEmail, password },
  });
  if (!login.ok()) return;
  const { access_token: accessToken } = await login.json();
  await request.delete("http://127.0.0.1:8000/api/v1/account", {
    data: { password, confirmation: "DELETE" },
    headers: { Authorization: `Bearer ${accessToken}` },
  });
});

test("mobile web registration, sync, search, persistence, and seeded login", async ({
  page,
  request,
}) => {
  const email = `mobile-${Date.now()}@example.com`;
  disposableEmail = email;
  const title = `Mobile sync note ${Date.now()}`;

  await page.goto("/register");
  const registrationFields = page.locator("input");
  await registrationFields.nth(0).fill("Mobile Test User");
  await registrationFields.nth(1).fill(email);
  await registrationFields.nth(2).fill(password);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByText("0 saved items")).toBeVisible();

  await page.getByText("Capture", { exact: true }).last().click();
  await page.getByRole("tab", { name: "Note" }).click();
  await page.getByPlaceholder("A useful name").fill(title);
  await page.getByPlaceholder("What do you want to remember?").fill(
    "A note created by the mobile integration workflow.",
  );
  await page.getByPlaceholder("research, design, later").fill("mobile, integration");
  await page.getByRole("button", { name: "Save to library" }).click();
  await expect(page.getByText("1 saved item")).toBeVisible();
  await expect(page.getByText(title)).toBeVisible();

  await page.getByText("Search", { exact: true }).last().click();
  await page.getByLabel("Search saved items").fill("Mobile sync note");
  await expect(page.getByRole("button", { name: new RegExp(title) })).toBeVisible();

  await page.reload();
  await expect(page.getByRole("button", { name: new RegExp(title) })).toBeVisible();
  await page.getByText("Settings", { exact: true }).last().click();
  await expect(page.getByText(email)).toBeVisible();

  const accessToken = await page.evaluate(() =>
    window.localStorage.getItem("memoryhive.access-token"),
  );
  expect(accessToken).toBeTruthy();
  const deletion = await request.delete("http://127.0.0.1:8000/api/v1/account", {
    data: { password, confirmation: "DELETE" },
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  expect(deletion.status()).toBe(204);

  await page.evaluate(() => window.localStorage.clear());
  await page.goto("/login");
  const loginFields = page.locator("input");
  await loginFields.nth(0).fill("engineer@demo.memoryhive.app");
  await loginFields.nth(1).fill("MemoryhiveDemo123!");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByText(/\d+ saved items/)).toBeVisible();
  await page.getByText("Settings", { exact: true }).last().click();
  await expect(page.getByText("engineer@demo.memoryhive.app")).toBeVisible();
});
