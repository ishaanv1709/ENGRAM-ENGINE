import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";
import { createHash } from "node:crypto";

test("real infrastructure evidence is visible without claiming autonomous execution", async ({
  page,
  playwright,
}, testInfo) => {
  test.skip(
    process.env.ENGRAM_INFRA_UI_TESTS !== "1",
    "Requires the explicit infrastructure evidence fixture",
  );
  const report = JSON.parse(
    readFileSync(
      "../data/collective/film-infrastructure-evidence.json",
      "utf8",
    ),
  );
  expect(report.infrastructure_passed).toBe(true);
  expect(report.autonomous_team_verified).toBe(false);
  const login = await page.request.post("/api/auth/login", {
    headers: { "X-Engram-Request": "1" },
    data: { email: report.fixture.email, password: "Integration-password-123" },
  });
  expect(login.ok()).toBe(true);
  for (const version of report.versions) {
    for (const artifact of version.manifest) {
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
  }
  await page.goto("/");
  await page
    .getByLabel("Project", { exact: true })
    .selectOption(report.fixture.project);
  await expect(page.locator(".brand-mark")).toBeVisible();
  expect(
    await page
      .locator(".brand-mark")
      .evaluate((image: HTMLImageElement) => image.naturalWidth),
  ).toBeGreaterThan(0);
  await page
    .locator("nav")
    .getByRole("button", { name: "Causal timeline", exact: true })
    .click();
  await expect(page.locator(".causal-card").first()).toContainText("Maya");
  await expect(page.locator(".causal-card").first()).toContainText("Priya");
  await expect(page.locator(".revised-plan").first()).toContainText("blocked");
  await expect(page.locator(".revised-plan").first()).toContainText(
    "quota exhausted",
  );
  await expect(page.locator(".graph-witness").first()).toContainText(
    "Why this work changed",
  );
  await expect(page.locator(".graph-witness").first()).toContainText(
    "SUPERSEDES edge confirmed",
  );
  const coordinationResponse = await page.request.get(
    `/api/projects/${report.fixture.project}/coordination`,
  );
  expect(coordinationResponse.ok()).toBe(true);
  const coordination = await coordinationResponse.json();
  const correction = coordination.causes.find(
    (event: any) => event.kind === "memory.corrected",
  );
  expect(
    correction.payload.graph_witness.direct_readers.length,
  ).toBeGreaterThan(0);
  expect(
    correction.payload.graph_witness.revision_edges.length,
  ).toBeGreaterThan(0);
  await page.screenshot({
    path: testInfo.outputPath("graph-witness.png"),
    fullPage: true,
  });
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
  await expect(page.locator(".claim.winner").first()).toContainText("Priya");
  await page
    .locator("nav")
    .getByRole("button", { name: "Procedures", exact: true })
    .click();
  await expect(page.getByText("v1", { exact: true })).toBeVisible();
  await expect(page.getByText("v2", { exact: true })).toBeVisible();
  await page
    .locator(".version-details")
    .first()
    .locator("summary")
    .first()
    .click();
  await expect(
    page.getByText("reuse verified", { exact: true }).first(),
  ).toBeVisible();
  if (process.env.ENGRAM_SHOWCASE_UI_TESTS === "1") {
    await page
      .locator(".procedure-benchmark")
      .first()
      .locator("summary")
      .first()
      .click();
    await expect(page.locator(".procedure-benchmark").first()).toContainText(
      "Measured reuse comparison",
    );
    await expect(page.locator(".procedure-benchmark").first()).toContainText(
      "Model tokens saved: 0",
    );
    expect(coordination.benchmarks[0].payload.trials).toHaveLength(10);
    expect(coordination.benchmarks[0].payload.summary.provider_calls).toBe(0);
    await page.screenshot({
      path: testInfo.outputPath("procedure-comparison.png"),
      fullPage: true,
    });
  }
  if (
    !(await page
      .locator(".nav-inspect")
      .evaluate((el: HTMLDetailsElement) => el.open))
  )
    await page.locator(".nav-inspect > summary").click();
  await page
    .locator("nav")
    .getByRole("button", { name: "Sandbox console", exact: true })
    .click();
  await expect(
    page.getByText("Restricted Docker execution", { exact: true }),
  ).toBeVisible();
  await expect(page.locator(".security-note")).toContainText(
    "probabilistic filter",
  );
  await expect(page.locator(".security-note")).toContainText(
    "host kernel is shared",
  );
  await page.screenshot({
    path: testInfo.outputPath("security-boundaries.png"),
    fullPage: true,
  });
  const outsider = await playwright.request.newContext({
    baseURL: "http://127.0.0.1:8088",
  });
  try {
    const live = JSON.parse(
      readFileSync("../data/collective/live-verification.json", "utf8"),
    );
    expect(
      (
        await outsider.post("/api/auth/login", {
          headers: { "X-Engram-Request": "1" },
          data: {
            email: live.fixture.email,
            password: "Live-verification-password-123",
          },
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
    expect(
      (
        await outsider.get(
          `/api/artifacts/${report.versions[0].manifest[0].id}/download`,
        )
      ).status(),
    ).toBe(404);
  } finally {
    await outsider.dispose();
  }
});
