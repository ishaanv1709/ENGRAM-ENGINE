import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";

test("memory passports and recovered handoffs render actual persisted evidence", async ({
  page,
  playwright,
  baseURL,
}, testInfo) => {
  test.skip(
    process.env.ENGRAM_TRACK2_UI !== "1",
    "Requires the completed real reliability fixture",
  );
  test.setTimeout(90_000);
  const root = "../data/collective/track2-upgrade/";
  const report = JSON.parse(readFileSync(root + "reliability.json", "utf8"));
  expect(report.passed).toBe(true);
  const cookies = JSON.parse(
    readFileSync(root + "browser-session.json", "utf8"),
  );
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
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await page
    .getByLabel("Project", { exact: true })
    .selectOption(report.fixture.project);
  await page.getByLabel("Go to page").selectOption("procedures");
  const passports = page.locator(".memory-passports");
  await passports.locator("summary").first().click();
  await expect(passports).toContainText("recovery");
  await expect(passports).toContainText("projection tokens");
  const handoffs = page.locator(".handoff-deliveries");
  await handoffs.locator("summary").first().click();
  await expect(handoffs).toContainText("acknowledged");
  await expect(handoffs).toContainText(report.pending_id.slice(0, 8));
  const actual = await (
    await page.request.get(
      `/api/projects/${report.fixture.project}/coordination`,
    )
  ).json();
  expect(actual.passports.length).toBeGreaterThanOrEqual(17);
  expect(actual.deliveries).toHaveLength(2);
  expect(
    actual.deliveries.filter(
      (d: { acknowledged_at: unknown }) => d.acknowledged_at,
    ),
  ).toHaveLength(1);
  await page.screenshot({
    path: testInfo.outputPath("track2-passports-desktop.png"),
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth + 1,
    ),
  ).toBe(true);
  await page.screenshot({
    path: testInfo.outputPath("track2-passports-mobile.png"),
    fullPage: true,
  });
  const outsider = await playwright.request.newContext({ baseURL });
  try {
    expect(
      (
        await outsider.post("/api/auth/start", {
          headers: { "X-Engram-Request": "1" },
        })
      ).ok(),
    ).toBe(true);
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
  expect(errors).toEqual([]);
  await expect(page.getByRole("alert")).toHaveCount(0);
});

test("four-pair live comparison shows actual successful measurements", async ({
  page,
}, testInfo) => {
  test.skip(
    process.env.ENGRAM_TRACK2_UI !== "1",
    "Requires completed live measurements",
  );
  test.setTimeout(90_000);
  const report = JSON.parse(
    readFileSync("../data/collective/track2-upgrade/live-series.json", "utf8"),
  );
  expect(report.passed).toBe(true);
  const cookies = JSON.parse(
    readFileSync(
      "../data/collective/submission-live-2026-10-18/session.json",
      "utf8",
    ),
  );
  await page
    .context()
    .addCookies(
      Object.entries(cookies).map(([name, value]) => ({
        name,
        value: String(value),
        domain: "127.0.0.1",
        path: "/",
        httpOnly: true,
        sameSite: "Strict" as const,
      })),
    );
  await page.goto("/");
  await page
    .getByLabel("Project", { exact: true })
    .selectOption(report.project_id);
  await page.getByLabel("Go to page").selectOption("procedures");
  await page
    .getByText("Repeated live memory comparison", { exact: true })
    .click();
  const comparison = page.locator(".procedure-benchmark[open]");
  await expect(comparison).toContainText("4 alternating pairs");
  await expect(comparison).toContainText("1,416.5");
  await expect(comparison).toContainText("1,782");
  await expect(comparison).toContainText("365.5");
  await comparison.screenshot({
    path: testInfo.outputPath("track2-live-series.png"),
  });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth + 1,
    ),
  ).toBe(true);
  await expect(page.getByRole("alert")).toHaveCount(0);
});
