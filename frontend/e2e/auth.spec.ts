import { expect, test } from "@playwright/test";
import { PASSWORD, openAuthPage, signUp, uniqueEmail, waitForAuthForm } from "./helpers";

test("logged-out visitors are sent to the login page", async ({ page }) => {
  await page.goto("/alerts");
  await expect(page).toHaveURL(/\/login\?next=%2Falerts/, { timeout: 60_000 });
  await expect(page.getByRole("button", { name: "Log in" })).toBeVisible();
});

test("sign up, log out, and log back in", async ({ page }) => {
  const email = uniqueEmail("auth");
  await signUp(page, email);

  await page.getByRole("button", { name: "Log out" }).click();
  await expect(page).toHaveURL(/\/login/);

  // Logged out: protected pages redirect again.
  await page.goto("/policy");
  await expect(page).toHaveURL(/\/login\?next=%2Fpolicy/);

  // Log in again — lands back on the page we were trying to reach.
  await waitForAuthForm(page);
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Log in" }).click();
  await expect(page).toHaveURL(/\/policy$/);
  await expect(page.getByText(email)).toBeVisible();
});

test("wrong password shows an error and stays logged out", async ({ page }) => {
  const email = uniqueEmail("wrongpw");
  await signUp(page, email);
  await page.getByRole("button", { name: "Log out" }).click();
  await expect(page).toHaveURL(/\/login/);
  await waitForAuthForm(page);

  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("not-the-password");
  await page.getByRole("button", { name: "Log in" }).click();
  await expect(page.getByTestId("form-error")).toHaveText("incorrect email or password");
  await expect(page).toHaveURL(/\/login/);
});

test("sign-up rejects mismatched passwords", async ({ page }) => {
  await openAuthPage(page, "/signup");
  await page.getByLabel("Email").fill(uniqueEmail("mismatch"));
  await page.getByLabel("Password", { exact: true }).fill("first-password-1");
  await page.getByLabel("Confirm password").fill("second-password-2");
  await page.getByRole("button", { name: "Sign up" }).click();
  await expect(page.getByTestId("form-error")).toHaveText("Passwords do not match.");
});