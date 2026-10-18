import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e",
  use: { baseURL: process.env.ENGRAM_BASE_URL || "http://127.0.0.1:8088", headless: true },
  reporter: "list",
  workers: 1,
});
