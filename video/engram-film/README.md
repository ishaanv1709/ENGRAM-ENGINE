# ENGRAM Collective walkthrough

Nine animated scenes covering the team, memory types, causal corrections, competing claims, procedure versions, sandbox boundaries and persistence. The new memory-loop identity appears in the app captures, title cards and film signature.

Target export: `renders/ENGRAM-Collective-demo.mp4`, 1920×1080, 30 fps, approximately 2:37 with local Kokoro narration and authored captions. The exact encoded metadata belongs in the final delivery manifest.

This is an **architecture and validation walkthrough**, not a claim that the full autonomous Qwen workflow passed. Capture provenance identifies earlier partial Qwen work separately from production infrastructure tools invoked directly by an integration driver. The latter uses real databases and Docker checks, no model inference and no mocked services. The full provider workflow remains quota-blocked; the separate long-argument fidelity failure is documented in `../../docs/DEMO-STATUS.md`.

```powershell
# Run from D:\Neurohacks\video\engram-film
npx hyperframes@0.8.162 preview --port 3017 --background --no-open
npx hyperframes@0.8.162 check --json --samples 9 --snapshots
$env:HF_CAPTURE_PARALLEL_STREAM='true'
npx hyperframes@0.8.162 render --output renders/ENGRAM-Collective-demo.mp4 --quality standard --fps 30 --workers 2 --gpu
```

Regenerate narration from the repository root with `.venv-video/Scripts/python.exe video/engram-film/scripts/generate-film-audio.py`, then assemble with `.venv-collective311/Scripts/python.exe video/engram-film/scripts/assemble-film.py`. Unchanged clips reuse their measured audio cache. Captions use authored text groups proportionally aligned to speech; they are not ASR word timestamps.

`SCENES.json`, `SCRIPT.md`, `TIMING.json`, `subtitles.srt`, `compositions/frames/` and `index.html` remain editable. Source checks and encoded-media reviews are distinct. Technical inspection and sampled frames do not constitute a full normal-speed audio audition.

Motion skills and source credits: `../../docs/DEMO-STATUS.md` and `REVIEW-PLAN.md`. Fonts retain their bundled OFL licenses. No public deployment is performed.
