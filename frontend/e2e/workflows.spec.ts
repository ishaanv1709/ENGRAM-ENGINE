import { test, expect } from "@playwright/test";
import { writeFileSync, readFileSync } from "node:fs";

test("create a scoped specialist and durable workflow draft without inference", async ({
  page,
}, testInfo) => {
  test.skip(
    process.env.ENGRAM_INFRA_UI_TESTS !== "1",
    "Requires actual local services",
  );
  const headers = { "X-Engram-Request": "1" };
  const response = await page.request.post("/api/auth/start", { headers });
  expect(response.ok()).toBe(true);
  const created = await page.request.post("/api/projects", {
    headers,
    data: { name: "Workflow browser check; no inference" },
  });
  expect(created.ok()).toBe(true);
  const project = await created.json();
  const modelMutations: string[] = [];
  page.on("request", (r) => {
    if (
      r.method() === "POST" &&
      /\/(start|resume|runs|memory|documents|evaluate|search)$/.test(
        new URL(r.url()).pathname,
      )
    )
      modelMutations.push(r.url());
  });
  await page.goto("/");
  await page.getByLabel("Project", { exact: true }).selectOption(project.id);
  await page.locator(".nav-inspect > summary").click();
  await page
    .getByRole("button", { name: "Custom agents", exact: true })
    .click();
  await page.getByLabel("Specialist name").fill("Repository evidence reviewer");
  await page
    .getByLabel("Specialist instructions")
    .fill(
      "Inspect source files and retain concrete evidence. Do not execute or mutate code.",
    );
  await page
    .getByRole("button", { name: "Create specialist", exact: true })
    .click();
  await expect(
    page.getByRole("heading", {
      name: "Repository evidence reviewer",
      exact: true,
    }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Workflows", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Goal → Plan → Progress → Results" }),
  ).toBeVisible();
  await page
    .getByLabel("Workflow goal")
    .fill(
      "Investigate a source change, implement it, check independently and prepare a review packet.",
    );
  await page
    .getByLabel("Import source ZIP", { exact: true })
    .setInputFiles("e2e/fixtures/workflow-source.zip");
  await expect(page.getByLabel("Source snapshot")).not.toHaveValue("");
  const research = page.locator(".milestone-editor article").nth(1);
  await research.locator("summary").click();
  const profiles = await (
    await page.request.get(`/api/projects/${project.id}/agent-profiles`)
  ).json();
  await research
    .getByLabel("Custom specialist")
    .selectOption(profiles.profiles[0].id);
  await page
    .getByRole("button", { name: "Save workflow draft", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Start workflow", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".workflow-stages article")).toHaveCount(5);
  await expect(page.locator(".workflow-stages article").first()).toContainText(
    "Plan the work",
  );
  await expect(page.locator(".workflow-stages article").nth(1)).toContainText(
    "Repository evidence reviewer",
  );
  const id = await page.getByLabel("Select workflow").inputValue();
  const before = await (await page.request.get(`/api/workflows/${id}`)).json();
  expect(before.workflow.status).toBe("draft");
  expect(before.runs).toEqual([]);
  expect(before.steps.map((s: any) => s.key)).toEqual([
    "plan",
    "research",
    "implement",
    "verify",
    "review",
  ]);
  expect(before.steps[4].needs_approval).toBe(true);
  writeFileSync(
    "../data/collective/workflow-browser-state.json",
    JSON.stringify(
      {
        project: project.id,
        id,
        before,
        storage: await page.context().storageState(),
      },
      null,
      2,
    ),
  );
  await page.reload();
  await page.getByLabel("Project", { exact: true }).selectOption(project.id);
  await page.getByRole("button", { name: "Workflows", exact: true }).click();
  await page.getByLabel("Select workflow").selectOption(id);
  await expect(
    page.getByRole("button", { name: "Start workflow", exact: true }),
  ).toBeVisible();
  await page.screenshot({
    path: testInfo.outputPath("workflow-desktop.png"),
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth + 1,
    ),
  ).toBe(true);
  await page.screenshot({
    path: testInfo.outputPath("workflow-mobile.png"),
    fullPage: true,
  });
  await expect(page.getByRole("alert")).toHaveCount(0);
  expect(modelMutations).toEqual([]);
});

test("workflow draft survives an actual API and worker restart", async ({
  page,
}) => {
  test.skip(
    process.env.ENGRAM_WORKFLOW_RESTART_TEST !== "1",
    "Run explicitly after scripts/restart-app.ps1",
  );
  const state = JSON.parse(
    readFileSync("../data/collective/workflow-browser-state.json", "utf8"),
  );
  await page.context().addCookies(state.storage.cookies);
  const response = await page.request.get(`/api/workflows/${state.id}`);
  expect(response.ok()).toBe(true);
  const after = await response.json();
  expect(after.workflow).toEqual(state.before.workflow);
  expect(after.steps).toEqual(state.before.steps);
  expect(after.runs).toEqual([]);
  expect(after.usage).toEqual([]);
});
