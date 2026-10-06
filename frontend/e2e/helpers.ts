import { expect, type Page } from "@playwright/test";

export const PASSWORD = "e2e-password-123";

export function uniqueEmail(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.floor(Math.random() * 1e6)}@example.com`;
}

/** Open /login or /signup and wait until the form is interactive. */
export async function openAuthPage(page: Page, path: "/login" | "/signup") {
  await page.goto(path);
  await waitForAuthForm(page);
}

export async function waitForAuthForm(page: Page) {
  await expect(page.locator('form[data-ready="true"]')).toBeVisible({ timeout: 60_000 });
}

export async function signUp(page: Page, email: string, password = PASSWORD) {
  await openAuthPage(page, "/signup");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByLabel("Confirm password").fill(password);
  await page.getByRole("button", { name: "Sign up" }).click();
  // Lands on the dashboard with the user's email in the Nav. The first time
  // a page is opened, `next dev` compiles it, which can take a while.
  await expect(page.getByText(email)).toBeVisible({ timeout: 60_000 });
}