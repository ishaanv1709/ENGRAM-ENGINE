import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";
import { createHash } from "node:crypto";

test("live agent artifacts and graph are visible through authenticated UI", async ({
  page,
  playwright,
}) => {
  test.skip(
    process.env.ENGRAM_LIVE_UI_TESTS !== "1",
    "Requires real provider-produced artifacts",
  );
  const report = JSON.parse(
    readFileSync("../data/collective/live-ui-fixture.json", "utf8"),
  );
  expect(report.workflow.artifacts.length).toBeGreaterThanOrEqual(2);
  const response = await page.request.post("/api/auth/login", {
    headers: { "X-Engram-Request": "1" },
    data: {
      email: report.fixture.email,
      password: "Live-verification-password-123",
    },
  });
  expect(response.ok()).toBe(true);
  for (const artifact of report.workflow.artifacts) {
    const download = await page.request.get(
      `/api/artifacts/${artifact.id}/download`,
    );
    expect(download.ok()).toBe(true);
    const bytes = await download.body();
    expect(bytes.length).toBeGreaterThan(0);
    expect(createHash("sha256").update(bytes).digest("hex")).toBe(
      artifact.sha256,
    );
  }
  const outsider = await playwright.request.newContext({
    baseURL: "http://127.0.0.1:8088",
  });
  try {
    const registration = await outsider.post("/api/auth/register", {
      headers: { "X-Engram-Request": "1" },
      data: {
        email: `artifact-isolation-${Date.now()}@example.test`,
        password: "Artifact-isolation-password-123",
        name: "Isolation test",
        workspace: "Isolation test",
      },
    });
    expect(registration.ok()).toBe(true);
    const denied = await outsider.get(
      `/api/artifacts/${report.workflow.artifacts[0].id}/download`,
    );
    expect(denied.status()).toBe(404);
  } finally {
    await outsider.dispose();
  }
  await page.goto("/");
  await page.getByRole("button", { name: "Artifacts", exact: true }).click();
  await expect(
    page.getByText("calculator.py", { exact: true }).first(),
  ).toBeVisible();
  await expect(
    page.getByText("test_calculator.py", { exact: true }).first(),
  ).toBeVisible();
  await page.screenshot({
    path: "test-results/live-artifacts.png",
    fullPage: true,
  });
  if (
    !(await page
      .locator(".nav-inspect")
      .evaluate((el: HTMLDetailsElement) => el.open))
  )
    await page.locator(".nav-inspect > summary").click();
  await page
    .getByRole("button", { name: "Knowledge graph", exact: true })
    .click();
  await expect(
    page.getByRole("img", { name: "Connected memory graph" }),
  ).toBeVisible();
  await page.screenshot({
    path: "test-results/live-graph.png",
    fullPage: true,
  });
});
