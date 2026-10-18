# ENGRAM illustrated blog package

Read `index.html` for the styled article or edit `engram-collective.md` for publication. Updated 18 October 2026 with the recovered live workflow, four matched live reuse pairs and real concurrency/recovery measurements. The previously created private ChatGPT Page remains an older draft and has not been updated by this local build.

## Included

- Original branded diagrams, Mermaid flowcharts and measured provider-free evaluation chart.
- Actual app captures, including the completed correction/replan and matched live comparison.
- `evaluation-track2.json`: four live matched pairs, receipts, store load, selective invalidation and replay recovery; the additional 120B workflow completed across restart, with prior unsuccessful attempts retained.
- `evaluation-live.json`: sanitized live evidence with exact run, check and provider-receipt IDs.
- `evaluation-data.json` and `evaluation-trials.csv`: the separate older five-pair zero-inference experiment.
- Portable HTML, editable article, local fonts and licenses.

## Publish

1. Publish the matching code revision separately. This package does not push the repository.
2. Paste the article into your blog editor and upload its referenced assets.
3. Keep recovery history, measurement scope, signed results and security boundaries beside the claims.
4. Preview and publish from your account. No external blog publication or hackathon submission is implied.

## Rebuild

Use `.venv-video/Scripts/python.exe docs/blog/build.py` for figures and HTML. Fresh live screenshots come from `frontend/e2e/submission-live.spec.ts` with `ENGRAM_LIVE_DEMO_UI=1`, after the live report passes. Preserve its screenshot files before another Playwright run. The old `render-assets.mjs` captures the older infrastructure fixture, so it must not overwrite the newer screenshots as live evidence.

The earlier chart and evaluation remain historical measurements. Four local matched pairs support a narrow verification-reuse comparison, not general cost or latency guarantees, and no first-attempt workflow success is claimed.
