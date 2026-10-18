import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";

test("120B restart changes approval action and preserves unrelated verification", async ({
  page,
}, testInfo) => {
  test.skip(
    process.env.ENGRAM_TRACK2_MISSION_UI !== "1",
    "Requires the actual completed 120B workflow",
  );
  test.setTimeout(90_000);
  const report = JSON.parse(
    readFileSync(
      "../data/collective/track2-upgrade/memory-mission.json",
      "utf8",
    ),
  );
  expect(report.passed).toBe(true);
  expect(report.model).toBe("openai/gpt-oss-120b");
  expect(report.mem0_correction.status).toBe("committed");
  expect(report.revised_action.result.summary).toContain("Priya");
  expect(report.parallel_snapshot.run_ids.length).toBeGreaterThanOrEqual(2);
  expect(
    report.handoffs.every(
      (h: { acknowledged_at: string }) => h.acknowledged_at,
    ),
  ).toBe(true);
  for (const verifier of report.preserved_verifier_runs) {
    expect(verifier.status).toBe("completed");
    expect(report.affected_runs).not.toContain(verifier.id);
  }
  expect(
    report.execution_receipts.some(
      (e: { kind: string; payload: { stdout?: string; exit_code?: number } }) =>
        e.kind === "tool.executed" &&
        e.payload.exit_code === 0 &&
        /10 passed/.test(e.payload.stdout || ""),
    ),
  ).toBe(true);
  const cookies = JSON.parse(
    readFileSync(
      "../data/collective/submission-live-2026-10-18/session.json",
      "utf8",
    ),
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
    .selectOption(report.project_id);
  await page.getByLabel("Go to page").selectOption("causes");
  const cause = page.locator(".causal-card").filter({
    has: page.getByText(`Correction #${report.correction_event}`, {
      exact: true,
    }),
  });
  await expect(cause).toHaveCount(1);
  await expect(cause).toContainText("Maya");
  await expect(cause).toContainText("Priya");
  await expect(cause.locator(".revised-plan")).toContainText("completed");
  await expect(cause.locator(".revised-plan")).toContainText("Priya");
  await cause.getByText("See graph evidence", { exact: true }).click();
  await expect(cause.locator(".graph-evidence")).toContainText("DEPENDS_ON");
  await expect(cause.locator(".graph-evidence")).toContainText("REPLANS");
  await cause.screenshot({
    path: testInfo.outputPath("track2-120b-causal-action.png"),
  });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth + 1,
    ),
  ).toBe(true);
  await cause.screenshot({
    path: testInfo.outputPath("track2-120b-causal-mobile.png"),
  });
  expect(errors).toEqual([]);
  await expect(page.getByRole("alert")).toHaveCount(0);
});
