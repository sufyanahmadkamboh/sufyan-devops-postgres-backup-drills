"""Builds the 1-minute vertical short (1080x1920, 30 fps) from script.py and the recorded voiceover.

    python video/short/build_short.py

Steps: decode the voiceover → timeline (each visual lasts exactly as long as its line) → page.html with
time-driven animations and word-by-word captions → every frame rendered by headless Edge (render.mjs) →
voice + sound effects (no music), -14 LUFS → out/short/<NAME>-full.mp4 and -silent.mp4 (identical picture).
Word timings come from voiceover/words.json (speech recognition on each recorded line, done once).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import wave
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
from script import HEADER, LINES, NAME  # noqa: E402

try:                                            # the sound effects of this repository's long video
    import audio_assets as sfx_module  # noqa: E402
except ImportError:
    import sound_effects as sfx_module  # noqa: E402
OUT = HERE.parent / "out" / "short"
VO = HERE / "voiceover"
FPS, W, H = 30, 1080, 1920
GAP = 0.12                      # seconds of silence between lines: fast pace
TEMPO = 1.07                    # voice 7% faster (pitch kept): the whole short stays under 60 s
RATE = 24000
FFMPEG_IMAGE = "linuxserver/ffmpeg@sha256:a7182d4fe498feea393622b43513cfaecb3fd073dcd3c7f38e9d74a10a4e8702"


def ff(*args: str, capture: bool = False) -> str:
    r = subprocess.run(["docker", "run", "--rm", "-v", f"{OUT}:/work", "-v", f"{VO}:/vo:ro", "-w", "/work",
                        "--entrypoint", "ffmpeg", FFMPEG_IMAGE, "-hide_banner", "-y", *args],
                       check=True, capture_output=capture, text=True)
    return r.stderr if capture else ""


def decode() -> dict[str, float]:
    (OUT / "audio").mkdir(parents=True, exist_ok=True)
    script = "".join(f"ffmpeg -y -loglevel error -i /vo/{ln['id']}.flac -af atempo={TEMPO} -ac 1 -ar {RATE} -sample_fmt s16 "
                     f"/work/audio/{ln['id']}.wav\n" for ln in LINES)
    subprocess.run(["docker", "run", "--rm", "-v", f"{OUT}:/work", "-v", f"{VO}:/vo:ro", "--entrypoint", "bash",
                    FFMPEG_IMAGE, "-c", script], check=True)
    out = {}
    for ln in LINES:
        with wave.open(str(OUT / "audio" / f"{ln['id']}.wav")) as w:
            out[ln["id"]] = w.getnframes() / w.getframerate()
    return out


def chunks(say: str, words: list[dict], start: float, dur: float) -> list[dict]:
    """Caption groups of up to 3 words; each word gets a time from the recognised word timings."""
    toks = say.split()
    marks = [w["start"] / TEMPO for w in words] or [0.0]
    n, m = len(toks), len(marks)
    times = [start + marks[min(m - 1, round(i * (m - 1) / max(n - 1, 1)))] if m > 1 else start + dur * i / n
             for i in range(n)]
    groups, cur = [], []
    for i, tok in enumerate(toks):
        cur.append(i)
        if len(cur) == 3 or re.search(r"[.,?!:]$", tok) or i == n - 1:
            groups.append(cur)
            cur = []
    out = []
    for g in groups:
        out.append({"t": times[g[0]], "words": [{"w": toks[i], "t": times[i]} for i in g]})
    return out


CSS = """
:root{--bg:#070d17;--ink:#f4f8ff;--muted:#9fb3cc;--ok:#38e08a;--bad:#ff4d5e;--amber:#ffc23d;--sky:#7cc4ff}
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:1080px;height:1920px;overflow:hidden;background:var(--bg);font-family:Inter,"Segoe UI",sans-serif;color:var(--ink)}
body::before{content:"";position:absolute;inset:0;background:radial-gradient(900px 700px at 50% 35%,rgba(56,140,255,.20),transparent 70%),
 linear-gradient(rgba(124,196,255,.05) 1px,transparent 1px),linear-gradient(90deg,rgba(124,196,255,.05) 1px,transparent 1px);background-size:auto,60px 60px,60px 60px}
#bar{position:absolute;left:0;top:0;height:12px;background:linear-gradient(90deg,var(--ok),var(--sky));width:0}
#head{position:absolute;left:40px;right:40px;top:44px;height:120px;display:flex;align-items:center;gap:22px;
 background:rgba(18,32,56,.92);border:4px solid #2f5585;border-radius:30px;padding:0 26px}
#head img{height:76px}
#head .pill{font-size:44px;font-weight:900;color:#0b1424;background:linear-gradient(90deg,var(--amber),#ff8a3d);border-radius:18px;padding:8px 20px;letter-spacing:1px}
#head .topic{font-size:38px;white-space:nowrap;font-weight:900;line-height:1.05}#head .topic small{display:block;font-size:30px;color:var(--muted);font-weight:800}
.tool{display:flex;align-items:center;gap:22px;font-size:60px;font-weight:900;background:#122038;border:5px solid #2f5585;border-radius:28px;padding:14px 34px}
.inl{height:64px;vertical-align:middle;margin-right:10px}
.down{display:flex;align-items:center;gap:30px}.down img{height:230px;filter:grayscale(1) brightness(.7)}.down span{font-size:170px}
.logos{display:flex;gap:44px}.logos img{height:120px}
.title.sm{font-size:84px}
.term{width:1000px;background:#0a0f18;border:5px solid #2f5585;border-radius:26px;padding:22px 30px;text-align:left;font:600 36px/1.45 "JetBrains Mono",Consolas,monospace;color:#c9d6e6}
.term div{white-space:pre-wrap;word-break:break-word}.term .tbar{color:var(--muted);font-size:28px;margin-bottom:8px;opacity:1;transform:none}
.term .c{color:var(--sky)}.term .r{color:#ff6b7a}.term .g{color:var(--ok)}.term .y{color:var(--amber)}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:24px;width:1000px}.stat{background:#122038;border:5px solid #2f5585;border-radius:26px;padding:22px 26px}
.stat b{display:block;font-size:92px;font-weight:900;line-height:1.05}.stat span{font-size:34px;color:var(--muted);font-weight:800}
.scene{position:absolute;left:0;right:0;top:190px;height:1030px;display:none;flex-direction:column;align-items:center;justify-content:center;gap:34px;text-align:center}
.scene.on{display:flex}
[data-at]{opacity:0;transform:scale(.6)}
.stamp{font-size:90px;font-weight:900;letter-spacing:2px;padding:18px 40px;border:10px solid;border-radius:26px;transform:rotate(-6deg)}
.big{font-size:330px;font-weight:900;line-height:.9;letter-spacing:-8px}.big small{font-size:140px;letter-spacing:0}
.label{font-size:56px;font-weight:900;letter-spacing:2px}
.title{font-size:118px;font-weight:900;line-height:1.02;letter-spacing:-2px}
.emoji{font-size:230px;line-height:1}
.ok{color:var(--ok)}.bad{color:var(--bad)}.amber{color:var(--amber)}.dim{color:var(--muted)}
.stamp.bad{border-color:var(--bad)}
.pods{display:flex;gap:22px}
.pod{width:170px;height:200px;border-radius:28px;background:#14233a;border:6px solid #2f5585;display:flex;align-items:center;justify-content:center;font-size:66px;font-weight:900;position:relative}
.pod i{font-style:normal;color:var(--amber)}.pod.flip i{position:absolute;opacity:var(--flip,0)}.pod.flip b{opacity:calc(1 - var(--flip,0))}
.pod.red{border-color:var(--bad);background:#3a1219}.pod.red i{color:var(--bad)}
.pod.canary{border-color:var(--amber);background:#3a2e10;box-shadow:0 0 50px rgba(255,194,61,.5)}
.users{font-size:76px;font-weight:900}
.clock{font-size:110px;font-weight:900}.clock b{color:var(--sky)}
.checks{display:flex;flex-direction:column;gap:26px}.check{font-size:68px;font-weight:800;background:#122038;border:5px solid #2f5585;border-radius:24px;padding:20px 40px}
.check span{color:var(--ok);margin-left:18px}
.shot{border-radius:34px;border:6px solid #2f5585;background-repeat:no-repeat;background-color:#181b1f;box-shadow:0 30px 80px rgba(0,0,0,.6)}
.tag{font-size:72px;font-weight:900;padding:18px 36px;border-radius:22px;background:#0b1424;border:6px solid currentColor}
.meter{position:relative;width:900px;height:120px;border-radius:60px;background:#14233a;overflow:hidden;border:6px solid #2f5585}
.meter .fill{position:absolute;left:0;top:0;bottom:0;width:calc(var(--fill,0) * 100%);background:linear-gradient(90deg,#ff8a3d,var(--bad));transform:none;opacity:1}
.meter .limit{position:absolute;left:23.6%;top:0;bottom:0;width:8px;background:var(--ok);z-index:2;transform:none}
.meter .limit span{position:absolute;left:16px;top:20px;font-size:38px;font-weight:900;color:var(--ok);white-space:nowrap}
.strikes{font-size:200px;display:flex;gap:40px}
.chips{display:flex;flex-wrap:wrap;gap:24px;justify-content:center;width:980px}.chips span{font-size:62px;font-weight:900;background:#122038;border:5px solid var(--sky);border-radius:60px;padding:18px 40px}
.follow{font-size:96px;font-weight:900;background:var(--bad);color:#fff;border-radius:30px;padding:22px 60px}
#cap{position:absolute;left:40px;right:40px;top:1260px;height:330px;display:flex;flex-wrap:wrap;align-content:center;justify-content:center;gap:0 26px;text-align:center}
#cap span{font-size:104px;font-weight:900;line-height:1.12;color:#fff;-webkit-text-stroke:4px #000;paint-order:stroke fill;text-shadow:0 8px 0 #000}
#cap span.now{color:var(--amber);transform:scale(1.08)}
#brand{position:absolute;left:0;right:0;bottom:120px;text-align:center;font-size:40px;font-weight:800;color:var(--muted)}#brand b{color:var(--ink)}
"""

JS = """
const ease = x => 1 - Math.pow(1 - Math.min(1, Math.max(0, x)), 3);
const pop = x => { x = Math.min(1, Math.max(0, x)); return x < 1 ? 1 + 0.12 * Math.sin(x * Math.PI) * (1 - x) * 3 : 1; };
function render(t) {
  document.getElementById('bar').style.width = (100 * Math.min(1, t / TOTAL)) + '%';
  let cur = 0; TL.forEach((s, i) => { if (t >= s.start) cur = i; });
  document.querySelectorAll('.scene').forEach((el, i) => el.classList.toggle('on', i === cur));
  const s = TL[cur], lt = t - s.start, sc = document.querySelectorAll('.scene')[cur];
  sc.style.transform = 'scale(' + (1 + 0.035 * lt / s.dur) + ')';
  sc.querySelectorAll('[data-at]').forEach(el => {
    const a = parseFloat(el.dataset.at), p = (lt - a) / 0.22;
    if (el.classList.contains('fill')) { el.style.opacity = 1; el.style.setProperty('--fill', 0.95 * ease((lt - a) / 1.0)); return; }
    if (el.classList.contains('limit')) { el.style.opacity = lt >= a ? 1 : 0; return; }
    el.style.opacity = lt >= a ? 1 : 0;
    const base = el.classList.contains('stamp') ? ' rotate(-6deg)' : '';
    el.style.transform = lt >= a ? 'scale(' + (0.6 + 0.4 * ease(p)) * pop(p) + ')' + base : 'scale(.6)';
    if (el.classList.contains('zoom')) el.style.backgroundSize = (230 + 25 * (lt / s.dur)) + '%';
    if (el.classList.contains('flip')) el.style.setProperty('--flip', ease((lt - a) / 0.3));
  });
  sc.querySelectorAll('[data-count]').forEach(el => {
    const host = el.closest('[data-at]'), a = host ? parseFloat(host.dataset.at) : 0, n = +el.dataset.count;
    el.textContent = Math.round(n * ease((lt - a) / 0.8));
  });
  let g = null; CAP.forEach(c => { if (t >= c.t) g = c; });
  const cap = document.getElementById('cap');
  if (!g || t > g.end) { cap.innerHTML = ''; return; }
  cap.innerHTML = g.words.map((w, i) => {
    const next = g.words[i + 1] ? g.words[i + 1].t : g.end;
    return '<span class="' + (t >= w.t && t < next ? 'now' : '') + '">' + w.w + '</span>';
  }).join('');
}
window.render = render; window.__ready = true;
"""


def page(tl: list[dict], caps: list[dict], total: float) -> Path:
    scenes = "".join(f'<section class="scene">{ln["body"]}</section>' for ln in LINES)
    html = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><title>short</title>'
            '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@700;800;900&family=JetBrains+Mono:wght@600&display=swap" rel="stylesheet">'
            f'<style>{CSS}</style></head><body><div id="bar"></div>'
            f'<div id="head"><img src="logos/{HEADER["logo"]}"><span class="pill">DevSecOps</span>'
            f'<span class="topic">{HEADER["topic"]}<small>{HEADER["sub"]}</small></span></div>'
            f'{scenes}<div id="cap"></div>'
            '<div id="brand"><b>Sufyan Ahmad</b> · DevOps</div>'
            f'<script>const TL={json.dumps(tl)};const CAP={json.dumps(caps)};const TOTAL={total};{JS}</script></body></html>')
    out = HERE / "page.html"                  # next to script.py so ../../shots resolves to video/shots
    out.write_text(html, encoding="utf-8", newline="\n")
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    durs = decode()
    words = json.loads((VO / "words.json").read_text(encoding="utf-8"))
    tl, caps, t = [], [], 0.0
    for ln in LINES:
        d = durs[ln["id"]] + GAP
        tl.append({"id": ln["id"], "start": round(t, 3), "dur": round(d, 3), "sfx": ln["sfx"]})
        for c in chunks(ln["say"], words[ln["id"]], t, durs[ln["id"]]):
            caps.append(c)
        t += d
    total = t + 0.4
    for i, c in enumerate(caps):                # each caption group stays until the next one starts
        c["end"] = caps[i + 1]["t"] if i + 1 < len(caps) else total
    print(f"short: {len(LINES)} lines, {total:.1f} s")
    url = page(tl, caps, total).as_uri()

    frames = OUT / "frames"
    frames.mkdir(exist_ok=True)
    for old in frames.glob("*.jpg"):
        old.unlink()
    n = int(total * FPS)
    subprocess.run(["node", str(HERE / "render.mjs"), url, str(frames), str(n), str(FPS), str(OUT / "profile")], check=True)

    # narration: each line at its start time
    with wave.open(str(OUT / "narration.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        for s in tl:
            with wave.open(str(OUT / "audio" / f"{s['id']}.wav")) as r:
                data = r.readframes(r.getnframes())
            w.writeframes(data + b"\0\0" * (round(s["dur"] * RATE) - len(data) // 2))
        w.writeframes(b"\0\0" * round(0.4 * RATE))
    ff("-loglevel", "error", "-i", "narration.wav", "-af",
       "highpass=f=80,equalizer=f=3200:t=q:w=1.2:g=2.5,equalizer=f=250:t=q:w=1:g=-1.5,"
       "acompressor=threshold=-26dB:ratio=3:attack=5:release=160:makeup=4dB,loudnorm=I=-16:TP=-2:LRA=9,aresample=48000",
       "-ac", "1", "voice.wav")
    events = [(s["start"], s["sfx"]) for s in tl]
    sfx_module.render_mix(OUT / "voice.wav", OUT / "mix.wav", total, events)
    m = json.loads(re.search(r"\{[^{}]*\}", ff("-nostats", "-i", "mix.wav", "-af",
                   "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-", capture=True)).group(0))
    ff("-loglevel", "error", "-i", "mix.wav", "-af",
       f"loudnorm=I=-14:TP=-1.5:LRA=11:linear=true:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
       f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']},aresample=48000",
       "final.wav")
    ff("-loglevel", "error", "-framerate", str(FPS), "-i", "frames/%05d.jpg", "-frames:v", str(n), "-c:v", "libx264",
       "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p", "-r", str(FPS), "-movflags", "+faststart", "video.mp4")
    ff("-loglevel", "error", "-i", "video.mp4", "-i", "final.wav", "-map", "0:v", "-map", "1:a", "-c:v", "copy",
       "-c:a", "aac", "-b:a", "320k", "-ar", "48000", "-ac", "2", "-shortest", "-movflags", "+faststart", f"{NAME}-full.mp4")
    ff("-loglevel", "error", "-i", "video.mp4", "-map", "0:v", "-c:v", "copy", "-an", "-movflags", "+faststart",
       f"{NAME}-silent.mp4")
    (HERE / "timeline.json").write_text(json.dumps({"total": total, "lines": tl}, indent=1), encoding="utf-8",
                                        newline="\n")
    print(f"-> {OUT / (NAME + '-full.mp4')} and -silent.mp4")


if __name__ == "__main__":
    main()
