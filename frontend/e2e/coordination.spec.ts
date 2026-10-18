import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";

test("real causal replan, preserved claims and versioned reuse are visible", async ({
  page,
  playwright,
}) => {
  test.skip(
    process.env.ENGRAM_CAUSAL_UI_TESTS !== "1",
    "Requires the completed real provider demo",
  );
  const report = JSON.parse(
    readFileSync("../data/collective/causal-demo.json", "utf8"),
  );
  expect(report.passed).toBe(true);
  const response = await page.request.post("/api/auth/login", {
    headers: { "X-Engram-Request": "1" },
    data: {
      email: report.fixture.email,
      password: "Live-verification-password-123",
    },
  });
  expect(response.ok()).toBe(true);
  await page.goto("/");
  await page
    .getByLabel("Project", { exact: true })
    .selectOption(report.fixture.project);
  await page
    .locator("nav")
    .getByRole("button", { name: "Causal timeline", exact: true })
    .click();
  await expect(
    page.getByText("See the impact of a corrected fact."),
  ).toBeVisible();
  await expect(page.locator(".causal-card").first()).toContainText("Priya");
  await expect(page.locator(".revised-plan").first()).toContainText(
    "completed",
  );
  if (
    !(await page
      .locator(".nav-inspect")
      .evaluate((el: HTMLDetailsElement) => el.open))
  )
    await page.locator(".nav-inspect > summary").click();
  await page
    .locator("nav")
    .getByRole("button", { name: "Claim resolution", exact: true })
    .click();
  await expect(page.locator(".claim-grid").first()).toContainText("Maya");
  await expect(page.locator(".claim-grid").first()).toContainText("Priya");
  await expect(page.locator(".claim.winner").first()).toContainText("Priya");
  await page
    .locator("nav")
    .getByRole("button", { name: "Procedures", exact: true })
    .click();
  await page
    .locator(".version-details")
    .first()
    .locator("summary")
    .first()
    .click();
  await expect(page.locator(".manifest-row").first()).toBeVisible();
  await expect(
    page.getByText("reuse verified", { exact: true }).first(),
  ).toBeVisible();
  const outsider = await playwright.request.newContext({
    baseURL: "http://127.0.0.1:8088",
  });
  try {
    const registration = await outsider.post("/api/auth/register", {
      headers: { "X-Engram-Request": "1" },
      data: {
        email: `coordination-isolation-${Date.now()}@example.test`,
        password: "Isolation-password-123",
        name: "Isolation",
        workspace: "Isolation",
      },
    });
    expect(registration.ok()).toBe(true);
    expect(
      (
        await outsider.get(
          `/api/projects/${report.fixture.project}/coordination`,
        )
      ).status(),
    ).toBe(404);
  } finally {
    await outsider.dispose();
  }
});
