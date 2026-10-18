# ENGRAM film review plan

This is preparation, not a completed film review. Run these commands only after the real voiced MP4 exists. Delivery contract: 1920 × 1080, 30 fps, audible narration. Do not attest playback or approve from source code or isolated stills.

## Tool provenance and readiness

The downloaded [video-review-loop skill](https://github.com/imMamdouhaboammar/motion-graphics-skills/tree/main/skills/video-review-loop) requires two sibling Python modules. Only these missing modules were downloaded, from upstream commit `29919c1ff91d0e0a242ffc0d085b838fa9575584`:

- [gpu_policy.py](https://raw.githubusercontent.com/imMamdouhaboammar/motion-graphics-skills/29919c1ff91d0e0a242ffc0d085b838fa9575584/skills/motion-director/scripts/gpu_policy.py), SHA-256 `23164876af155282cb5601653fe8eabaca9512d25d466f4d638a29152167fa90`.
- [reference_fidelity.py](https://raw.githubusercontent.com/imMamdouhaboammar/motion-graphics-skills/29919c1ff91d0e0a242ffc0d085b838fa9575584/skills/motion-director/scripts/reference_fidelity.py), SHA-256 `f1d800566dd0733311ef617bc6b285b9536717ef10f366185529b1aadfef8faa`.

Paths and hashes are also recorded in `../skills/motion-director/scripts/DOWNLOAD-PROVENANCE.json`. Both modules use only Python's standard library. Actual dynamic imports from the review scripts passed. `review_video.py --help`, `review_video.py review --help`, `strict_video_signals.py --help`, and `review_round.py --help` ran successfully.

The runtime capability probe detected NVIDIA GeForce RTX 3050 Laptop GPU, CUDA decode, and FFmpeg's `h264_nvenc` encoder. This establishes candidate capabilities only. The review scripts must verify decoding against the actual MP4; it does not prove that the final film was encoded or rendered using a GPU.

## Real MP4 technical review

Run in PowerShell. Set `filmPath` to the final export's actual location; the example filename is the intended delivery name. Leave CPU fallback disabled while the supported GPU path exists.

```powershell
Set-Location D:\Neurohacks\video\engram-film
$pythonPath = 'D:\Neurohacks\.venv-collective311\Scripts\python.exe'
$reviewScript = 'D:\Neurohacks\video\skills\video-review-loop\scripts\review_video.py'
$signalsScript = 'D:\Neurohacks\video\skills\video-review-loop\scripts\strict_video_signals.py'
$roundScript = 'D:\Neurohacks\video\skills\video-review-loop\scripts\review_round.py'
$filmPath = (Resolve-Path '.\output\engram-collective.mp4').Path

$reviewOutput = & $pythonPath $reviewScript review $filmPath `
  --expect-width 1920 --expect-height 1080 --expect-fps 30 --expect-audio
$reviewExitCode = $LASTEXITCODE
$reviewOutput
$reviewResult = ($reviewOutput -join "`n") | ConvertFrom-Json
if (-not $reviewResult.round_dir) { throw 'Review did not produce an evidence round; inspect the error.' }
$roundDir = (Resolve-Path $reviewResult.round_dir).Path

& $pythonPath $signalsScript $filmPath --output (Join-Path $roundDir 'strict-signals.json')
if ($LASTEXITCODE -ne 0) { throw 'Strict signal audit failed; inspect the GPU/decode error.' }

Get-Content -LiteralPath (Join-Path $roundDir 'technical.json')
Get-Content -LiteralPath (Join-Path $roundDir 'findings.json')
Get-Content -LiteralPath (Join-Path $roundDir 'strict-signals.json')
& $pythonPath $roundScript status $roundDir
```

If a duration was locked from the final narration timeline, also pass `--expect-duration` with that real measured target. Add `--expect-end-hold` only when a deliberate still hold is actually part of the final cut; do not invent an end-hold requirement for ambient motion.

The technical tool's nonzero exit code can indicate hard findings while still producing a useful evidence round. Preserve that round and inspect the findings. A status command must remain nonzero until its required review evidence has actually been supplied.

## Review the final motion and sound

1. Play the whole MP4 at normal speed with audio. Check narration clarity, cuts, synchronization, and abrupt sound endings.
2. Play it again muted. Inspect narrative hierarchy, camera motion, screenshot crops, and any false product claims.
3. Inspect the first second densely, every scene seam, the ending, and every machine warning at its actual timestamp.
4. Check the contact sheet at phone scale. Confirm the correction retains the old fact, competing claims remain visible, and procedural measurements do not invent savings.
5. Record confirmed issues in the generated round using `review_round.py add`. Fix the responsible source, render a new actual MP4, and review the new file. A source edit alone does not resolve a video finding.

Example finding command, to be filled with a genuinely observed defect:

```powershell
& $pythonPath $roundScript add $roundDir `
  --time '00:00.000' --severity review `
  --defect 'Replace with the observed defect' `
  --fix 'Replace with the concrete source fix' `
  --evidence 'Replace with the actual playback and frame evidence inspected'
```

Only after completing those inspections, attest the inspections actually performed:

```powershell
& $pythonPath $roundScript attest $roundDir `
  --watched-with-audio --watched-muted --first-second-inspected `
  --transitions-inspected --ending-inspected --strict-signals-inspected `
  --machine-findings-inspected
& $pythonPath $roundScript status $roundDir
```

No benchmark reference film was assigned, so reference-comparison flags are intentionally absent. Do not use the attestation command if any listed inspection was not actually performed. Passing machine checks and sampled frames alone are insufficient evidence for full audiovisual signoff.
