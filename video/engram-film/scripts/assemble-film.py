"""Assemble the verified scene files and authored subtitle timing without network calls."""
from pathlib import Path
import html
import json
import math
import re

ROOT=Path(__file__).resolve().parents[1]
timing=json.loads((ROOT/'TIMING.json').read_text(encoding='utf-8'))
duration_s = float(timing['total_duration_s'])
if not math.isfinite(duration_s) or duration_s <= 0:
    raise ValueError('TIMING.json must contain a finite positive total duration')
if abs(float(timing['scenes'][-1]['end_s']) - duration_s) > 1 / 30:
    raise ValueError('Last scene end does not match the measured narration timeline')
DURATION=f'{duration_s:.6f}'
def timestamp(value):
    h,m,s=re.split('[:,]',value)[:3]
    milliseconds=value.rsplit(',',1)[1]
    return int(h)*3600+int(m)*60+int(s)+int(milliseconds)/1000

scene_hosts=[]
for scene in timing['scenes']:
    scene_hosts.append(f'''    <div id="host-{scene['id']}" class="clip film-scene" data-composition-id="{scene['id']}" data-composition-src="compositions/frames/{scene['id']}.html" data-start="{scene['start_s']:.6f}" data-duration="{scene['duration_s']:.6f}" data-track-index="1" data-width="1920" data-height="1080"></div>''')
caption_clips=[]
for block in re.split(r'\n\s*\n',(ROOT/'subtitles.srt').read_text(encoding='utf-8').strip()):
    lines=block.strip().splitlines()
    cue=int(lines[0]);start,end=lines[1].split(' --> ')
    start_s,end_s=timestamp(start),timestamp(end)
    text=html.escape(' '.join(lines[2:]))
    caption_clips.append(f'''    <div id="caption-{cue:02d}" class="clip film-caption" data-start="{start_s:.3f}" data-duration="{end_s-start_s:.3f}" data-track-index="20"><span class="film-caption-text">{text}</span></div>''')
source='''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=1920,height=1080" />
<title>ENGRAM Collective — Graph Hacks Demo</title>
<script src="assets/gsap.min.js"></script>
<style>
@font-face{font-family:FilmCaption;src:url('assets/DM-Sans.ttf');font-weight:100 900;font-display:block}
html,body{margin:0;width:1920px;height:1080px;overflow:hidden;background:#0B100E}
#engram-film-root{position:relative;width:100%;height:100%;overflow:hidden;color:#DCE5DF}
.film-ground{position:absolute;inset:0;background:#0B100E}
.film-scene{position:absolute;inset:0;width:100%;height:100%}
.film-caption-rail{position:absolute;left:96px;right:96px;top:943px;height:88px;border-top:1px solid #253029;background:linear-gradient(90deg,#11191400,#111914cc 18%,#111914cc 82%,#11191400);z-index:50;box-sizing:border-box}
.film-caption{position:absolute;left:130px;right:130px;top:966px;height:55px;display:flex;align-items:center;justify-content:center;z-index:51;box-sizing:border-box}
.film-caption-text{font-family:FilmCaption,sans-serif;font-size:32px;line-height:1.3;font-weight:500;letter-spacing:.05px;text-align:center;color:#DCE5DF;text-shadow:0 2px 12px #000;max-width:1630px}
.film-progress{position:absolute;left:96px;right:96px;bottom:21px;height:2px;background:#253029;z-index:52}
.film-progress-fill{width:100%;height:2px;background:#C5E6AD;transform-origin:left center}
.film-signature{position:absolute;right:40px;top:34px;width:34px;height:34px;object-fit:contain;opacity:.8;z-index:55}
.film-evidence-label{position:absolute;left:96px;top:37px;z-index:55;font:500 17px FilmCaption,sans-serif;letter-spacing:1.4px;color:#87958C}
</style>
</head>
<body>
<div id="engram-film-root" data-composition-id="main" data-width="1920" data-height="1080" data-start="0" data-duration="DURATION">
    <div id="film-ground" class="clip film-ground" data-start="0" data-duration="DURATION" data-track-index="0"></div>
SCENE_HOSTS
    <div id="film-caption-rail" class="clip film-caption-rail" data-start="0" data-duration="DURATION" data-track-index="19"></div>
CAPTION_CLIPS
    <div class="film-progress"><div class="film-progress-fill"></div></div>
    <img id="film-signature" class="film-signature" src="assets/engram-mark.svg" alt="ENGRAM memory loop" />
    <div id="film-evidence-label" class="film-evidence-label">LOCAL BUILD WALKTHROUGH · REAL UI &amp; INFRASTRUCTURE VALIDATION</div>
    <audio id="film-narration" src="audio/narration.wav" data-start="0" data-duration="DURATION" data-track-index="30" data-volume="1" preload="auto"></audio>
</div>
<script>
(()=>{
  const timeline=gsap.timeline({paused:true});
  timeline.fromTo('.film-progress-fill',{scaleX:0},{scaleX:1,duration:DURATION,ease:'none'},0);
  window.__timelines=window.__timelines||{};
  window.__timelines.main=timeline;
})();
</script>
</body>
</html>
'''.replace('DURATION',DURATION).replace('SCENE_HOSTS','\n'.join(scene_hosts)).replace('CAPTION_CLIPS','\n'.join(caption_clips))
(ROOT/'index.html').write_text(source,encoding='utf-8')
print(json.dumps({'root_duration_s':float(DURATION),'scenes':len(scene_hosts),'caption_clips':len(caption_clips),'audio':timing['narration']}))
