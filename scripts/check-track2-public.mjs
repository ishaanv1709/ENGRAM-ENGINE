import { chromium } from "../frontend/node_modules/@playwright/test/index.mjs";
import { readFileSync, writeFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";
import assert from "node:assert/strict";

const root = resolve(import.meta.dirname, "..");
const origin = process.env.ENGRAM_PUBLIC_URL || JSON.parse(readFileSync(resolve(root, "data/collective/public-tunnel.json"), "utf8").replace(/^\uFEFF/, "")).url;
const base = origin.replace(/\/$/, "") + "/evidence/live/";
const digest = (bytes) => createHash("sha256").update(bytes).digest("hex");
const browser = await chromium.launch();
const report = { passed: false, url: base, public_files: [], layouts: [], errors: [] };
try {
  const page = await browser.newPage();
  page.on("pageerror", (e) => report.errors.push(e.message));
  for (const file of ["index.html", "evidence.json", "track2-upgrade.json", "brand.svg", "track2/track2-passports-desktop.png", "track2/track2-live-series.png", "track2/track2-120b-causal-action.png"]) {
    const response = await page.request.get(base + file, { timeout: 30000 });
    assert.equal(response.status(), 200);
    const remote = digest(await response.body());
    assert.equal(remote, digest(readFileSync(resolve(root, "outputs/submission-live", file))));
    report.public_files.push({ file, status: 200, sha256: remote });
  }
  for (const [name, url] of [["public", base], ["blog", pathToFileURL(resolve(root, "docs/blog/index.html")).href]]) {
    for (const width of [1440, 390]) {
      await page.setViewportSize({ width, height: 900 });
      await page.goto(url, { waitUntil: "networkidle" });
      await page.evaluate(() => document.fonts.ready);
      const layout = await page.evaluate(() => ({
        images: document.images.length,
        missing: [...document.images].filter((i) => !i.complete || !i.naturalWidth).map((i) => i.getAttribute("src")),
        overflow: document.documentElement.scrollWidth > innerWidth + 1,
        liveText: document.body.innerText.includes("1,416.5"),
      }));
      assert.deepEqual(layout.missing, []);
      if (layout.overflow) console.log(JSON.stringify({ name, width, layout, oversized: await page.locator("body *").evaluateAll((elements) => elements.filter((e) => e.getBoundingClientRect().right > innerWidth + 1).slice(0,15).map((e) => ({ tag:e.tagName, cls:e.className, width:e.getBoundingClientRect().width, text:e.textContent?.slice(0,70) }))) }));
      assert.equal(layout.overflow, false, `${name} ${width}`);
      assert.equal(layout.liveText, true);
      report.layouts.push({ name, width, ...layout });
      await page.screenshot({ path: resolve(root, name === "blog" ? `docs/blog/${width === 390 ? "mobile" : "desktop"}-preview.png` : `outputs/submission-live/track2/public-evidence-${width}.png`), fullPage: true });
    }
  }
  assert.deepEqual(report.errors, []);
  report.passed = true;
  writeFileSync(resolve(root, "outputs/submission-live/track2/public-check.json"), JSON.stringify(report, null, 2));
  writeFileSync(resolve(root, "docs/blog/live-render-check.json"), JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report));
} finally {
  await browser.close();
}
