import { expect, test } from "@playwright/test";
import { signUp, uniqueEmail } from "./helpers";

test("an attack preset is blocked and raises a critical alert", async ({ page }) => {
  await signUp(page, uniqueEmail("attack"));

  await page.goto("/playground");
  await expect(page.getByRole("heading", { name: "Agent Sandbox" })).toBeVisible();
  // Wait until the session exists (the chat input becomes enabled).
  await expect(page.getByPlaceholder("Ask the sandbox agent to do something...")).toBeEnabled();

  await page.getByRole("button", { name: "Attack presets" }).click();
  await page.getByRole("button", { name: /Ignore previous instructions \(EN\)/ }).click();

  await expect(page.getByText(/SentinelAI blocked this message before it reached the agent/)).toBeVisible();

  await page.goto("/alerts");
  await expect(page.getByText(/Blocked: prompt_injection/).first()).toBeVisible();
});

test("a benign message is allowed through", async ({ page }) => {
  await signUp(page, uniqueEmail("benign"));
  await page.goto("/playground");
  const input = page.getByPlaceholder("Ask the sandbox agent to do something...");
  await expect(input).toBeEnabled();

  await input.fill("What's on the agenda for today's standup?");
  await input.press("Enter");
  // No Groq key in E2E, so the agent answers in degraded mode — but it is NOT blocked.
  await expect(page.getByText(/Degraded mode: no GROQ_API_KEY configured/)).toBeVisible();
  await expect(page.getByText(/SentinelAI blocked this message/)).toHaveCount(0);
});