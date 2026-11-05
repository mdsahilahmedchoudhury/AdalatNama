import { defineConfig, devices } from "@playwright/test";

/**
 * End-to-end smoke tests against a running stack (web + API + worker + DB + Redis).
 * Start the stack first (docker compose up, or the local commands in README.md), then:
 *   E2E_BASE_URL=http://localhost:3000 npx playwright test
 */
export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["github"], ["list"]] : "list",
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3000",
    trace: "retain-on-failure",
  },
  projects: [{ name: "phone", use: { ...devices["Pixel 7"] } }],
});
