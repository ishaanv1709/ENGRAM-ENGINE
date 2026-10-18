import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";
import { createHash } from "node:crypto";

test("completed live submission has real graph, reuse and artifact evidence", async ({
  page,
}, testInfo) => {
  test.setTimeout(90_000);
  test.skip(
    process.env.ENGRAM_LIVE_DEMO_UI !== "1",
    "Requires the actual completed live demo; never substitutes responses",
  );
  const browserErrors: string[] = [];
  page.on("pageerror", (error) => browserErrors.push(error.message));
  const root = "../data/collective/submission-live-2026-10-18/";
  const report = JSON.parse(readFileSync(root + "report.json", "utf8"));
  expect(report.passed).toBe(true);
  const cookies = JSON.parse(readFileSync(root + "session.json", "utf8"));
  await page.context().addCookies(
    Object.entries(cookies).map(([name, value]) => ({
      name,
      value: String(value),
      domain: "127.0.0.1",
      path: "/",
      httpOnly: true,
      sameSite: "Strict" as const,
    })),
  );
  for (const artifact of report.artifacts) {
    const download = await page.request.get(
      `/api/artifacts/${artifact.id}/download`,
    );
    expect(download.ok()).toBe(true);
    expect(
      createHash("sha256")
        .update(await download.body())
        .digest("hex"),
    ).toBe(artifact.sha256);
  }
  await page.goto("/");
  await page
    .getByLabel("Project", { exact: true })
    .selectOption(report.fixture.project);
  await page.getByLabel("Go to page").selectOption("causes");
  const cause = page.locator(".causal-card").filter({
    has: page.getByText(`Correction #${report.correction.id}`, { exact: true }),
  });
  await expect(cause).toContainText("Maya");
  await expect(cause).toContainText("Priya");
  await expect(page.locator(".revised-plan").first()).toContainText(
    "completed",
  );
  await cause.getByText("See graph evidence", { exact: true }).click();
  await expect(cause.locator(".graph-evidence")).toContainText("DEPENDS_ON");
  await expect(cause.locator(".graph-evidence")).toContainText("REPLANS");
  await page.screenshot({
    path: testInfo.outputPath("live-causal-graph.png"),
    fullPage: true,
  });
  await page
    .locator("nav")
    .getByRole("button", { name: "Procedures", exact: true })
    .click();
  await page.getByText("Live model reuse comparison", { exact: true }).click();
  const comparison = page.locator(".procedure-benchmark[open]").first();
  await expect(comparison).toContainText("observed provider calls");
  await expect(comparison).toContainText(
    report.comparison.trials.baseline.model,
  );
  await expect(comparison).toContainText("Signed savings");
  await page.screenshot({
    path: testInfo.outputPath("live-reuse-comparison.png"),
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth + 1,
    ),
  ).toBe(true);
  await page.screenshot({
    path: testInfo.outputPath("live-reuse-mobile.png"),
    fullPage: true,
  });
  await expect(page.getByRole("alert")).toHaveCount(0);
  expect(browserErrors).toEqual([]);
});

test("public live evidence is readable without a private session", async ({
  page,
}, testInfo) => {
  test.skip(
    process.env.ENGRAM_LIVE_DEMO_UI !== "1",
    "Requires completed live evidence",
  );
  const browserErrors: string[] = [];
  page.on("pageerror", (error) => browserErrors.push(error.message));
  const response = await page.request.get("/evidence/live/evidence.json");
  expect(response.ok()).toBe(true);
  const evidence = await response.json();
  expect(evidence.passed).toBe(true);
  expect(evidence.comparison.trials.baseline.status).toBe("completed");
  expect(evidence.comparison.trials.reuse.status).toBe("completed");
  expect(evidence.graph.revised_action.result).toBeTruthy();
  await page.goto("/evidence/live/");
  await expect(
    page.getByRole("heading", { name: "The release that remembers." }),
  ).toBeVisible();
  await expect(
    page.getByRole("img", { name: "ENGRAM memory loop" }),
  ).toBeVisible();
  await page.screenshot({
    path: testInfo.outputPath("public-evidence-desktop.png"),
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth + 1,
    ),
  ).toBe(true);
  await page.screenshot({
    path: testInfo.outputPath("public-evidence-mobile.png"),
    fullPage: true,
  });
  expect(browserErrors).toEqual([]);
});
