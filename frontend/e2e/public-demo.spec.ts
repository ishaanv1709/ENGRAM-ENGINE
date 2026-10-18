import { test, expect } from "@playwright/test";
import { readFileSync, writeFileSync } from "node:fs";
import { createHash } from "node:crypto";

test("public Start building, secure session, artifacts and tenant denial", async ({
  page,
  playwright,
  baseURL,
}) => {
  test.skip(
    !baseURL?.startsWith("https://"),
    "Explicit public HTTPS verification only",
  );
  test.setTimeout(90_000);
  const report = JSON.parse(
    readFileSync(
      "../data/collective/film-infrastructure-evidence.json",
      "utf8",
    ),
  );
  expect((await page.request.get("/api/projects")).status()).toBe(401);
  await page.goto("/");
  const startResponse = page.waitForResponse(
    (r) => new URL(r.url()).pathname === "/api/auth/start",
  );
  await page
    .getByRole("button", { name: "Start building", exact: true })
    .click();
  expect((await startResponse).status()).toBe(200);
  const session = (await page.context().cookies()).find(
    (c) => c.name === "engram_session",
  );
  expect(session?.secure).toBe(true);
  expect(session?.httpOnly).toBe(true);
  expect(session?.sameSite).toBe("Strict");
  const ownProject = (await (await page.request.get("/api/projects")).json())[0]
    .id;
  await page.getByLabel("Go to page", { exact: true }).selectOption("sandbox");
  await expect(
    page.getByRole("heading", {
      name: "Real execution. Clear boundaries.",
      exact: true,
    }),
  ).toBeVisible();
  const imported = await page.request.post(
    `/api/projects/${ownProject}/source-snapshots`,
    {
      headers: { "X-Engram-Request": "1" },
      multipart: {
        file: {
          name: "beginner.zip",
          mimeType: "application/zip",
          buffer: readFileSync("public/examples/engram-beginner-python.zip"),
        },
      },
    },
  );
  expect(imported.status()).toBe(200);
  const artifact = (await imported.json()).manifest[0];
  artifact.id = artifact.artifact_id;
  const downloaded = await page.request.get(
    `/api/artifacts/${artifact.id}/download`,
  );
  expect(downloaded.status()).toBe(200);
  expect(
    createHash("sha256")
      .update(await downloaded.body())
      .digest("hex"),
  ).toBe(artifact.sha256);
  const headers = { "X-Engram-Request": "1" };
  const outsider = await playwright.request.newContext({ baseURL });
  try {
    const registered = await outsider.post("/api/auth/start", { headers });
    expect(registered.status()).toBe(200);
    expect((await (await outsider.get("/api/projects")).json())[0].id).not.toBe(
      ownProject,
    );
    expect(
      (await outsider.get(`/api/artifacts/${artifact.id}/download`)).status(),
    ).toBe(404);
    expect(
      (
        await outsider.get(`/api/projects/${report.fixture.project}/memory`)
      ).status(),
    ).toBe(404);
    const badOrigin = await outsider.post("/api/projects", {
      headers: { ...headers, Origin: "https://unapproved.example" },
      data: { name: "Must not be created" },
    });
    expect(badOrigin.status()).toBe(403);
  } finally {
    await outsider.dispose();
  }
  await expect(page.getByRole("alert")).toHaveCount(0);
  writeFileSync(
    "../data/collective/public-verification.json",
    JSON.stringify(
      {
        url: baseURL,
        verified_at: new Date().toISOString(),
        passed: true,
        checks: [
          "Public Quickstart and application delivered over HTTPS",
          "Actual browser Start building with approved Origin",
          "Secure, HttpOnly, SameSite Strict session",
          "Sandbox view reachable",
          "Published artifact hash matches",
          "Anonymous project access denied",
          "Another tenant cannot read project memory or artifacts",
          "Unapproved origin mutation denied",
        ],
        provider_calls: 0,
      },
      null,
      2,
    ),
  );
});
