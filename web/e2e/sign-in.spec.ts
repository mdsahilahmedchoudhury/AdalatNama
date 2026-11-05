import { execSync } from "node:child_process";
import path from "node:path";

import { expect, test } from "@playwright/test";

/**
 * Phase 0 smoke test: a signed-out visitor is sent to /login, can request a
 * link, and a valid link signs them in to the app shell (chamber name, user
 * name and role in the top bar), from where they can sign out again.
 *
 * Email is not available in tests, so the link is minted with the operator CLI
 * (`python -m app.cli login-link EMAIL`), which uses the same token store.
 * E2E_LOGIN_LINK_CMD overrides how the CLI is reached (CI runs it inside the
 * api container); the email is appended as the last argument.
 */
const OWNER_EMAIL = process.env.E2E_EMAIL ?? "owner@demo-chambers.example";
const REPO_ROOT = path.resolve(__dirname, "../..");
const LOGIN_LINK_CMD =
  process.env.E2E_LOGIN_LINK_CMD ?? "cd api && uv run --no-sync python -m app.cli login-link";

function mintLoginLink(email: string): string {
  const output = execSync(`${LOGIN_LINK_CMD} ${email}`, {
    cwd: REPO_ROOT,
    encoding: "utf8",
    stdio: ["ignore", "pipe", "ignore"],
  });
  const link = output.split("\n").find((line) => line.includes("/auth/verify#token="));
  if (!link) throw new Error(`login-link printed no link: ${output}`);
  return link.trim();
}

test("sign in with a magic link and sign out", async ({ page, baseURL }) => {
  await page.goto("/");
  await expect(page).toHaveURL(/\/login$/);

  await page.getByLabel("Email").fill(OWNER_EMAIL);
  await page.getByRole("button", { name: "Email me a sign-in link" }).click();
  await expect(page.getByRole("status")).toContainText("Check your email");

  const link = new URL(mintLoginLink(OWNER_EMAIL));
  await page.goto(`${baseURL}${link.pathname}${link.hash}`);
  await page.getByRole("button", { name: "Continue" }).click();

  await expect(page).toHaveURL(new RegExp(`${baseURL}/?$`));
  const header = page.getByRole("banner");
  await expect(header).toContainText("Demo Law Chambers");
  await expect(header).toContainText("Owner");
  await expect(page.getByRole("heading", { name: "No cases yet" })).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Main" })).toContainText("Home");

  await page.getByRole("button", { name: "Open menu" }).click();
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(page).toHaveURL(/\/login$/);
});

test("a used or broken link is refused", async ({ page }) => {
  await page.goto("/auth/verify#token=not-a-real-token-value");
  await page.getByRole("button", { name: "Continue" }).click();
  await expect(page.getByRole("alert").filter({ hasText: "invalid" })).toBeVisible();
});
