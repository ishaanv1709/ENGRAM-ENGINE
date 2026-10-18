import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";

test("public Quickstart covers every feature without em dashes or inference", async ({
  page,
}, testInfo) => {
  const posts: string[] = [];
  page.on("request", (r) => {
    if (r.method() === "POST") posts.push(r.url());
  });
  await page.goto("/quickstart");
  await expect(
    page.getByRole("heading", { name: "Quickstart", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".quick-card")).toHaveCount(17);
  await expect(page.locator(".beginner-lesson")).toHaveCount(8);
  await expect(
    page.getByRole("link", {
      name: "Download beginner Python project",
      exact: true,
    }),
  ).toBeVisible();
  const beginner = await page.request.get(
    "/examples/engram-beginner-python.zip",
  );
  expect(beginner.status()).toBe(200);
  expect((await beginner.body()).subarray(0, 2).toString()).toBe("PK");
  await expect(
    page.getByRole("heading", { name: "What the sandbox enforces." }),
  ).toBeVisible();
  expect(await page.locator(".quickstart").innerText()).not.toContain("\u2014");
  await page.getByRole("link", { name: "Every feature", exact: true }).click();
  await page.screenshot({
    path: testInfo.outputPath("quickstart-desktop.png"),
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth + 1,
    ),
  ).toBe(true);
  await page.screenshot({
    path: testInfo.outputPath("quickstart-mobile.png"),
    fullPage: true,
  });
  expect(posts).toEqual([]);
});

test("page menu reaches every feature and preserves the selected page on reload", async ({
  page,
}) => {
  test.skip(
    process.env.ENGRAM_INFRA_UI_TESTS !== "1",
    "Requires actual local fixture",
  );
  const fixture = JSON.parse(
    readFileSync(
      "../data/collective/film-infrastructure-evidence.json",
      "utf8",
    ),
  ).fixture;
  const login = await page.request.post("/api/auth/login", {
    headers: { "X-Engram-Request": "1" },
    data: { email: fixture.email, password: "Integration-password-123" },
  });
  expect(login.ok()).toBe(true);
  await page.goto("/#/quickstart");
  await page
    .getByLabel("Project", { exact: true })
    .selectOption(fixture.project);
  await expect(page.locator(".quickstart")).toBeVisible();
  const mutations: string[] = [];
  page.on("request", (r) => {
    if (r.method() === "POST") mutations.push(r.url());
  });
  const picker = page.getByLabel("Go to page", { exact: true });
  const options = await picker
    .locator("option")
    .evaluateAll((nodes) => nodes.map((n) => (n as HTMLOptionElement).value));
  expect(options).toHaveLength(15);
  for (const destination of options) {
    await picker.selectOption(destination);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await expect(page.getByRole("alert")).toHaveCount(0);
  }
  await picker.selectOption("quickstart");
  await page.reload();
  await expect(picker).toHaveValue("quickstart");
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(picker).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth + 1,
    ),
  ).toBe(true);
  expect(mutations).toEqual([]);
});
