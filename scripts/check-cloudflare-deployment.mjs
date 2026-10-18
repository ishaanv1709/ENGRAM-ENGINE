import { chromium } from "../frontend/node_modules/@playwright/test/index.mjs";
import { readFileSync, mkdirSync, writeFileSync } from "node:fs";
import { createHash } from "node:crypto";
import assert from "node:assert/strict";

const origin = "https://engram-collective.spring-cherry-c778.workers.dev";
const directory = "data/collective/deploy";
mkdirSync(directory, { recursive: true });
const report = { url: origin, verified_at: new Date().toISOString(), passed: false, layouts: [], assets: [] };
const browser = await chromium.launch();
try {
  const page = await browser.newPage();
  const errors = [];
  page.on("pageerror", error => errors.push(error.message));
  const status = await (await page.request.get(origin + "/deployment-status")).json();
  assert.equal(status.website, "cloudflare-workers");
  assert.equal(status.backend, "laptop-tunnel");
  assert.equal(status.laptop_independent_backend, false);
  report.deployment_status = status;
  const digest = bytes => createHash("sha256").update(bytes).digest("hex");
  for (const file of ["evidence/live/track2-upgrade.json", "evidence/live/track2/track2-live-series.png", "examples/engram-beginner-python.zip"]) {
    const response = await page.request.get(`${origin}/${file}`);
    assert.equal(response.status(), 200);
    const hash = digest(await response.body());
    assert.equal(hash, digest(readFileSync(`frontend/dist/${file}`)));
    report.assets.push({ file, sha256: hash });
  }
  // Block every agent API request in the browser. Static guides and evidence
  // must still render, demonstrating that their delivery needs no local API.
  await page.route("**/api/**", route => route.abort());
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 900 });
    for (const path of ["/quickstart", "/evidence/live/"]) {
      await page.goto(origin + path, { waitUntil: "networkidle" });
      await page.getByRole("complementary", { name: "Deployment status" }).waitFor();
      const layout = await page.evaluate(() => ({
        overflow: document.documentElement.scrollWidth > innerWidth + 1,
        missing_images: [...document.images].filter(image => !image.complete || !image.naturalWidth).map(image => image.src),
        text: document.body.innerText,
      }));
      assert.equal(layout.overflow, false);
      assert.deepEqual(layout.missing_images, []);
      assert.ok(layout.text.includes(path === "/quickstart" ? "Quickstart" : "1,416.5"));
      report.layouts.push({ path, width, api_blocked: true, overflow: false, missing_images: [] });
      await page.screenshot({ path: `${directory}/cloudflare-${path.includes("evidence") ? "evidence" : "quickstart"}-${width}.png`, fullPage: true });
    }
  }
  assert.deepEqual(errors, []);
  report.public_app_check = JSON.parse(readFileSync("data/collective/public-verification.json", "utf8"));
  assert.equal(report.public_app_check.url, origin);
  assert.equal(report.public_app_check.passed, true);
  report.passed = true;
  console.log(JSON.stringify(report));
} finally {
  writeFileSync(`${directory}/cloudflare-verification.json`, JSON.stringify(report, null, 2));
  await browser.close();
}
