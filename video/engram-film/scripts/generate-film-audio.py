"""Generate local Kokoro narration and an honest measured film timing manifest."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import soundfile as sf


PROJECT = Path(__file__).resolve().parents[1]
CACHE = Path.home() / ".cache/hyperframes/tts"
MODEL = CACHE / "models/kokoro-v1.0.onnx"
VOICES = CACHE / "voices/voices-v1.0.bin"
RELEASE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"


def download(path: Path, url: str, minimum: int) -> None:
    if path.exists() and path.stat().st_size > minimum:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".film-download")
    if path == MODEL:
        # Official release endpoint supports byte ranges; preserve partial bytes
        # and use four bounded parallel streams for the remaining weight file.
        size = 325_532_387
        prefix = temporary.stat().st_size if temporary.exists() else 0
        if prefix > size:
            raise RuntimeError("Partial model is larger than official release asset")
        remaining = size - prefix
        def piece(item: tuple[int, int, int]) -> Path:
            number, start, end = item
            part = temporary.with_name(temporary.name + f".part{number}")
            request = urllib.request.Request(url + f"?film={time.time_ns()}-{number}", headers={"User-Agent": "ENGRAM-local-film/1.0", "Range": f"bytes={start}-{end}"})
            with urllib.request.urlopen(request, timeout=35) as response, part.open("wb") as handle:
                if response.status != 206:
                    raise RuntimeError("Official model download did not honor byte range")
                began = time.monotonic()
                while chunk := response.read(256 * 1024):
                    if time.monotonic() - began > 480:
                        raise TimeoutError("Model range download exceeded eight minutes")
                    handle.write(chunk)
            if part.stat().st_size != end - start + 1:
                raise RuntimeError("Official model range content length mismatch")
            print(f"Model range {number}: {part.stat().st_size:,} bytes complete", flush=True)
            return part
        if remaining:
            ranges = [(n, prefix + remaining * n // 4, prefix + remaining * (n + 1) // 4 - 1) for n in range(4)]
            print(f"Resuming official model at {prefix:,} bytes using four range streams", flush=True)
            with ThreadPoolExecutor(max_workers=4) as pool:
                parts = list(pool.map(piece, ranges))
            with temporary.open("ab") as handle:
                for part in parts:
                    with part.open("rb") as source:
                        while chunk := source.read(1024 * 1024):
                            handle.write(chunk)
                    part.unlink()
        if temporary.stat().st_size != size:
            raise RuntimeError("Assembled official model content length mismatch")
        os.replace(temporary, path)
        print(f"Downloaded {path.name}: {path.stat().st_size:,} bytes", flush=True)
        return
    started = time.monotonic()
    request = urllib.request.Request(url, headers={"User-Agent": "ENGRAM-local-film/1.0"})
    with urllib.request.urlopen(request, timeout=40) as response, temporary.open("wb") as handle:
        total = int(response.headers.get("Content-Length", 0))
        count = 0
        next_report = 32 * 1024 * 1024
        while True:
            if time.monotonic() - started > 600:
                raise TimeoutError("Model download exceeded 10 minutes")
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            handle.write(chunk)
            count += len(chunk)
            if count >= next_report:
                print(f"Downloading {path.name}: {count:,} / {total:,} bytes", flush=True)
                next_report += 32 * 1024 * 1024
    if temporary.stat().st_size < minimum:
        raise RuntimeError(f"Downloaded model too small: {temporary.stat().st_size}")
    if total and temporary.stat().st_size != total:
        raise RuntimeError("Model download content length mismatch")
    os.replace(temporary, path)
    print(f"Downloaded {path.name}: {path.stat().st_size:,} bytes", flush=True)


def timestamp(seconds: float) -> str:
    millis = round(seconds * 1000)
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    secs, millis = divmod(millis, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"


def caption_groups(text: str, speech_duration: float) -> list[str]:
    """Balance sentence chunks so a final word never becomes a flashing cue."""
    groups = []
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        words = sentence.split()
        count = math.ceil(len(words) / 10)
        if not count:
            continue
        size, extra = divmod(len(words), count)
        cursor = 0
        for index in range(count):
            end = cursor + size + (index < extra)
            groups.append(" ".join(words[cursor:end]))
            cursor = end
    # This is proportional authored timing, not an invented ASR alignment.
    while len(groups) > 1:
        total = sum(map(len, groups))
        short = next((i for i, line in enumerate(groups)
                      if speech_duration * len(line) / total < 1.1), None)
        if short is None:
            break
        previous = max(0, short - 1)
        if short == 0:
            groups[0:2] = [groups[0] + " " + groups[1]]
        else:
            groups[previous:short + 1] = [groups[previous] + " " + groups[short]]
    return groups


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cached-only", action="store_true",
                        help="Require matching existing voice clips; never download or synthesize")
    args = parser.parse_args()
    engine = None
    scenes = json.loads((PROJECT / "SCENES.json").read_text(encoding="utf-8"))
    audio_dir = PROJECT / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    timing = []
    concatenated = []
    subtitles = []
    offset = 0.0
    sample_rate = 24_000
    for index, scene in enumerate(scenes):
        target = audio_dir / f"{scene['id']}.wav"
        text = scene["narration"]
        fingerprint = hashlib.sha256(("af_heart|1.0|" + text).encode()).hexdigest()
        metadata_path = target.with_suffix(".json")
        cached = metadata_path.exists() and json.loads(metadata_path.read_text(encoding="utf-8")).get("input_sha256") == fingerprint
        if target.exists() and cached:
            samples, sample_rate = sf.read(target, dtype="float32")
        else:
            if args.cached_only:
                raise RuntimeError(f"Missing or outdated cached narration for {scene['id']}")
            if engine is None:
                download(MODEL, RELEASE + MODEL.name, 100_000_000)
                download(VOICES, RELEASE + VOICES.name, 20_000_000)
                from kokoro_onnx import Kokoro
                os.environ.setdefault("OMP_NUM_THREADS", "4")
                print("Loading official Kokoro-82M ONNX model", flush=True)
                engine = Kokoro(str(MODEL), str(VOICES))
            print(f"Synthesizing {scene['id']} with af_heart", flush=True)
            samples, sample_rate = engine.create(text, voice="af_heart", speed=1.0, lang="en-us")
            samples = np.asarray(samples, dtype=np.float32)
            if not np.isfinite(samples).all() or len(samples) < sample_rate:
                raise RuntimeError("Invalid synthesized audio")
            sf.write(target, samples, sample_rate, subtype="PCM_16")
            metadata_path.write_text(json.dumps({"input_sha256": fingerprint, "voice": "af_heart", "speed": 1.0, "text": text}, indent=2), encoding="utf-8")
        duration = len(samples) / sample_rate
        # All authored entrances finish by 12.2s. Intro's last reveal lands at
        # 10.1s; 12s preserves that reveal without the previous six-second gap.
        # Final padding stays below two seconds, including frame rounding and
        # the cached clip's short natural trailing silence.
        final_scene = index == len(scenes) - 1
        minimum_slot = 12.0 if scene["id"] == "01-intro" else (14.0 if final_scene else 16.0)
        padding = 1.8 if final_scene else 1.5
        slot = math.ceil(max(minimum_slot, duration + padding) * 30) / 30
        pad_samples = round(slot * sample_rate) - len(samples)
        concatenated.extend([samples, np.zeros(pad_samples, dtype=np.float32)])
        record = {"id": scene["id"], "title": scene["title"], "start_s": round(offset, 6), "speech_duration_s": round(duration, 6), "duration_s": round(slot, 6), "end_s": round(offset + slot, 6), "audio": f"audio/{target.name}", "voice": "af_heart", "sample_rate": sample_rate, "wav_sha256": hashlib.sha256(target.read_bytes()).hexdigest()}
        timing.append(record)
        # Authored captions: short readable groups; measured speech span, not ASR.
        sentences = caption_groups(text, duration)
        weights = [len(s) for s in sentences]
        cursor = offset
        for sentence, weight in zip(sentences, weights):
            end = cursor + duration * weight / sum(weights)
            subtitles.append((cursor, end, sentence))
            cursor = end
        print(f"{scene['id']}: speech {duration:.3f}s; scene slot {slot:.3f}s", flush=True)
        offset += slot
    output = audio_dir / "narration.wav"
    sf.write(output, np.concatenate(concatenated), sample_rate, subtype="PCM_16")
    info = sf.info(output)
    manifest = {"engine": "Kokoro-82M / kokoro-onnx", "voice": "af_heart", "speed": 1.0, "model_source": RELEASE + MODEL.name, "model_sha256": hashlib.sha256(MODEL.read_bytes()).hexdigest(), "sample_rate": sample_rate, "total_duration_s": info.duration, "caption_timing": "Authored subtitles; short text groups proportionally aligned to measured generated narration, not ASR word timings", "narration": "audio/narration.wav", "scenes": timing}
    (PROJECT / "TIMING.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (PROJECT / "subtitles.srt").write_text("\n\n".join(f"{i}\n{timestamp(start)} --> {timestamp(end)}\n{text}" for i, (start, end, text) in enumerate(subtitles, 1)) + "\n", encoding="utf-8")
    print(f"COMPLETE: {info.duration:.3f}s, {info.samplerate}Hz, {info.channels} channel; {len(subtitles)} authored captions", flush=True)


if __name__ == "__main__":
    main()
