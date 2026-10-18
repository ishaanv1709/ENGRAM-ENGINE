import { test, expect } from "@playwright/test";

test("Start building creates a private workspace and profile manages keys without inference", async ({
  page,
  playwright,
  baseURL,
}, testInfo) => {
  test.setTimeout(90_000);
  await page.goto("/");
  await expect(page.getByLabel("Email", { exact: true })).toHaveCount(0);
  await expect(page.getByLabel("Password", { exact: true })).toHaveCount(0);
  await page
    .getByRole("button", { name: "Start building", exact: true })
    .click();
  await expect(page.getByLabel("Project", { exact: true })).toHaveValue(/.+/);
  const me = await (await page.request.get("/api/me")).json();
  const project = await page
    .getByLabel("Project", { exact: true })
    .inputValue();
  const calls: string[] = [];
  page.on("request", (r) => {
    if (
      r.method() === "POST" &&
      /\/(test|runs|start|resume|search|memory|documents)$/.test(
        new URL(r.url()).pathname,
      )
    )
      calls.push(r.url());
  });
  await page
    .getByRole("button", { name: "Add your AI key", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Bring your own key.", exact: true }),
  ).toBeVisible();
  const providers = page.getByLabel("AI provider", { exact: true });
  await expect(providers.locator("option")).toHaveCount(11);
  for (const label of [
    "Groq",
    "Grok / xAI",
    "Anthropic",
    "Google Gemini",
    "OpenAI",
    "DeepSeek",
    "OpenCode Console / Zen",
    "OpenRouter",
  ]) {
    expect(await providers.locator("option").allTextContents()).toContain(
      label,
    );
  }
  await providers.selectOption("gemini");
  await page
    .getByLabel("Connection name", { exact: true })
    .fill("Browser key isolation check");
  await page
    .getByLabel("Exact model ID", { exact: true })
    .fill("configuration-check-only");
  const nonworkingKey = "nonworking-browser-key-check-never-sent";
  await page
    .getByLabel("Provider API key", { exact: true })
    .fill(nonworkingKey);
  await page
    .getByRole("button", { name: "Save connection", exact: true })
    .click();
  await expect(
    page.getByRole("heading", {
      name: "Browser key isolation check",
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    page.getByLabel("Provider API key", { exact: true }),
  ).toHaveValue("");
  const saved = await page.request.get("/api/profile");
  expect(await saved.text()).not.toContain(nonworkingKey);
  expect((await saved.json()).connections[0].test_status).toBe("not_tested");
  await page.screenshot({
    path: testInfo.outputPath("profile-desktop.png"),
    fullPage: false,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth + 1,
    ),
  ).toBe(true);
  await page.screenshot({
    path: testInfo.outputPath("profile-mobile.png"),
    fullPage: false,
  });
  const outsider = await playwright.request.newContext({ baseURL });
  try {
    await outsider.post("/api/auth/start", {
      headers: { "X-Engram-Request": "1" },
    });
    expect(
      (await (await outsider.get("/api/profile")).json()).connections,
    ).toEqual([]);
    expect(
      (await outsider.get(`/api/projects/${project}/memory`)).status(),
    ).toBe(404);
  } finally {
    await outsider.dispose();
  }
  await page
    .getByRole("button", {
      name: "Delete Browser key isolation check",
      exact: true,
    })
    .click();
  await expect(
    page.getByRole("heading", {
      name: "Browser key isolation check",
      exact: true,
    }),
  ).toHaveCount(0);
  await page.reload();
  expect((await (await page.request.get("/api/me")).json()).id).toBe(me.id);
  expect((await (await page.request.get("/api/me")).json()).has_provider).toBe(
    false,
  );
  expect(calls).toEqual([]);
  await expect(page.getByRole("alert")).toHaveCount(0);
});
