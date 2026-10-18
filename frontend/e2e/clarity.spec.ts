import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";

const description =
  "ENGRAM Collective is a team of AI agents that shares persistent graph memory, coordinates work, and traces how changing knowledge affects its decisions.";

test("clear first steps preserve every feature without starting model work", async ({
  page,
}, testInfo) => {
  test.skip(
    process.env.ENGRAM_INFRA_UI_TESTS !== "1",
    "Uses the existing real infrastructure fixture",
  );
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/");
  await expect(page.getByText(description, { exact: true })).toBeVisible();
  await expect(page.locator(".mini-services")).toBeHidden();
  await page.getByText("Connection details", { exact: true }).click();
  await expect(page.locator(".mini-services")).toBeVisible();
  const report = JSON.parse(
    readFileSync(
      "../data/collective/film-infrastructure-evidence.json",
      "utf8",
    ),
  );
  expect(
    (
      await page.request.post("/api/auth/login", {
        headers: { "X-Engram-Request": "1" },
        data: {
          email: report.fixture.email,
          password: "Integration-password-123",
        },
      })
    ).ok(),
  ).toBe(true);
  const mutations: string[] = [];
  page.on("request", (request) => {
    if (request.method() === "POST")
      mutations.push(new URL(request.url()).pathname);
  });
  await page.reload();
  await page
    .getByLabel("Project", { exact: true })
    .selectOption(report.fixture.project);
  await expect(page.getByText(description, { exact: true })).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Start a task", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".nav-inspect")).not.toHaveAttribute("open");
  await expect(
    page.getByRole("button", { name: "Knowledge graph", exact: true }),
  ).toBeHidden();
  const mission = await page.locator(".mission").boundingBox();
  const stats = await page.locator(".stats-grid").boundingBox();
  expect(mission!.y).toBeLessThan(stats!.y);
  await page
    .getByRole("button", { name: "Use an example goal", exact: true })
    .click();
  await expect(page.getByLabel("Team objective")).toHaveValue(
    /release checklist/,
  );
  await expect(page.getByLabel("Shared memory only")).toBeHidden();
  await page.getByText("Memory settings", { exact: true }).click();
  await page.getByLabel("Shared memory only").check();
  await expect(page.getByLabel("Shared memory only")).toBeChecked();
  await page.getByText("Memory settings", { exact: true }).click();
  await page.screenshot({
    path: testInfo.outputPath("workspace-desktop.png"),
    fullPage: false,
  });
  await page
    .getByRole("button", { name: "See what is remembered", exact: false })
    .click();
  await expect(
    page.getByRole("heading", { name: "Add something to remember" }),
  ).toBeVisible();
  for (const label of [
    "All memories",
    "Past activity",
    "Facts",
    "Ways of working",
  ]) {
    await page.getByRole("button", { name: label, exact: true }).click();
  }
  await page
    .getByRole("button", { name: "Causal timeline", exact: true })
    .click();
  await expect(page.locator(".graph-evidence").first()).not.toHaveAttribute(
    "open",
  );
  await page
    .locator(".graph-evidence")
    .first()
    .locator("summary")
    .first()
    .click();
  await expect(
    page
      .locator(".graph-witness")
      .first()
      .getByText(/SUPERSEDES edge/),
  ).toBeVisible();
  await page.getByRole("button", { name: "Procedures", exact: true }).click();
  await expect(page.locator(".version-details").first()).not.toHaveAttribute(
    "open",
  );
  await page
    .locator(".version-details")
    .first()
    .locator("summary")
    .first()
    .click();
  await expect(
    page.locator(".version-details").first().locator(".manifest-row").first(),
  ).toBeVisible();
  await page
    .locator(".version-details")
    .first()
    .locator("summary")
    .first()
    .click();
  await page
    .locator(".procedure-benchmark")
    .first()
    .locator("summary")
    .first()
    .click();
  await expect(
    page
      .locator(".procedure-benchmark")
      .first()
      .getByText("Verified procedure", { exact: true }),
  ).toBeVisible();
  await page.locator(".nav-inspect > summary").click();
  for (const label of [
    "Knowledge graph",
    "Claim resolution",
    "Run timeline",
    "Sandbox console",
    "System & access",
  ]) {
    await page.getByRole("button", { name: label, exact: true }).click();
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await expect(page.getByRole("alert")).toHaveCount(0);
  }
  await page.getByRole("button", { name: "Artifacts", exact: true }).click();
  await expect(
    page.getByRole("link", { name: "Download", exact: true }).first(),
  ).toBeVisible();
  await expect(page.locator(".checksum").first()).toBeHidden();
  await page.getByText("File details", { exact: true }).first().click();
  await expect(page.locator(".checksum").first()).toBeVisible();
  await page.getByRole("button", { name: "Workspace", exact: true }).click();
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(
    page.getByRole("button", { name: "Understand changes", exact: false }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth + 1,
    ),
  ).toBe(true);
  await page.screenshot({
    path: testInfo.outputPath("workspace-mobile.png"),
    fullPage: true,
  });
  expect(mutations).toEqual([]);
});
