import { test, expect } from "@playwright/test";

test.afterEach(async ({ page }) => {
  const projects = await page.request.get("/api/projects");
  if (!projects.ok()) return;
  for (const project of await projects.json()) {
    const response = await page.request.get(`/api/projects/${project.id}/runs`);
    if (!response.ok()) continue;
    for (const run of await response.json()) {
      if (["queued", "running", "waiting"].includes(run.status)) {
        await page.request.post(`/api/runs/${run.id}/cancel`, {
          headers: { "X-Engram-Request": "1" },
        });
      }
    }
  }
});

test("private browser workspace, real project, key requirement and navigation", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByRole("button", { name: "Start building", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Start a task", exact: true }),
  ).toBeVisible();
  page.once("dialog", (dialog) =>
    dialog.accept("Browser verification project"),
  );
  await page
    .getByRole("button", { name: "Create project", exact: true })
    .click();
  await expect(page.getByLabel("Project", { exact: true })).toHaveValue(/.+/);
  await page
    .getByLabel("Team objective")
    .fill(
      "Inspect uploaded project documents and report the available evidence.",
    );
  await page
    .getByRole("button", { name: "Start working", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText("Profile & settings");
  const project = await page
    .getByLabel("Project", { exact: true })
    .inputValue();
  expect(
    await (await page.request.get(`/api/projects/${project}/runs`)).json(),
  ).toEqual([]);
  await page
    .getByRole("button", { name: "Dismiss error", exact: true })
    .click();
  await page.getByLabel("Go to page", { exact: true }).selectOption("settings");
  await expect(
    page.getByRole("heading", { name: "Service readiness", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("needs key", { exact: true }).first(),
  ).toBeVisible();
  await page.getByLabel("Go to page", { exact: true }).selectOption("memory");
  await expect(
    page.getByRole("heading", {
      name: "Add something to remember",
      exact: true,
    }),
  ).toBeVisible();
  await expect(page.getByRole("alert")).toHaveCount(0);
});
