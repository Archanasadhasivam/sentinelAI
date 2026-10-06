/**
 * End-to-end tests (item 6). Run with:  npm run test:e2e
 *
 * Playwright starts its OWN copy of the real backend and frontend on spare
 * ports (8100 / 3100), so it never touches the servers you use for
 * development or your real database:
 *   - backend: SANDBOX_MODE=memory (no Docker), no Groq key, eager alert
 *     queue with no SIEM (no Redis), and a throwaway e2e_test.db
 *   - frontend: `next dev` pointed at that backend
 *
 * One-time setup:  npx playwright install chromium
 */
import { defineConfig, devices } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

const BACKEND_PORT = 8100;
const FRONTEND_PORT = 3100;
const backendDir = path.resolve(__dirname, "../backend");
const python =
  process.env.SENTINELAI_PYTHON ||
  (process.platform === "win32"
    ? path.join(backendDir, ".venv", "Scripts", "python.exe")
    : path.join(backendDir, ".venv", "bin", "python"));

// Fresh database for every run (only in the main process, not in workers).
if (!process.env.TEST_WORKER_INDEX) {
  fs.rmSync(path.join(backendDir, "e2e_test.db"), { force: true });
}

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 120_000,
  expect: { timeout: 30_000 },
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: `http://localhost:${FRONTEND_PORT}`,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: `"${python}" -m uvicorn app.main:app --port ${BACKEND_PORT}`,
      cwd: backendDir,
      url: `http://localhost:${BACKEND_PORT}/health`,
      reuseExistingServer: false,
      timeout: 120_000,
      env: {
        SANDBOX_MODE: "memory",
        GROQ_API_KEY: "",
        ALERT_QUEUE_MODE: "eager",
        SIEM_WEBHOOK_URL: "",
        JWT_SECRET: "e2e-only-secret-not-for-real-use",
        DATABASE_URL: "sqlite+aiosqlite:///./e2e_test.db",
        CORS_ORIGIN: `http://localhost:${FRONTEND_PORT}`,
      },
    },
    {
      command: `npx next dev --port ${FRONTEND_PORT}`,
      url: `http://localhost:${FRONTEND_PORT}/login`,
      reuseExistingServer: false,
      timeout: 180_000,
      env: {
        NEXT_PUBLIC_API_URL: `http://localhost:${BACKEND_PORT}`,
        NEXT_DIST_DIR: ".next-e2e",
      },
    },
  ],
});