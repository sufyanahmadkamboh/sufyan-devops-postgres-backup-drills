# Video tutorial

> The YouTube upload package (`youtube/`) is written by the build and kept locally; it is not published in this repository.

A 16-minute explainer of this project, built entirely from code: every frame is an HTML scene rendered by a headless browser,
the voiceover is a recorded AI voice (SpeakSay), and ffmpeg assembles the result. There is no music: the soundtrack
is the voice plus a few short sound effects.

| File | What it is |
|---|---|
| `scenes.py` | the script: the scenes, the narration steps, and the visuals for each step |
| `components.py` | building blocks: cards, tiles, diagrams, highlighted code excerpts, terminals |
| `build.py` | the pipeline: page → frames → narration → encode → captions and chapters → post-production |
| `shot.mjs` | screenshots the scenes with one headless Edge/Chrome (DevTools protocol) |
| `voiceover/` | the recorded voiceover: one FLAC per narration step (SpeakSay, voice "Steve"), and `lines.json`, the exact text each file says |
| `sound_effects.py` | the sound effects (whooshes on cuts, intro sting, outro chord), synthesised in code |
| `tts.ps1` | fallback narration with the Windows speech engine, used only when `voiceover/` is missing |
| `AUDIO-LICENSES.md` | every audio asset, its license and when it plays |
| `thumbnail.html` | the YouTube thumbnail (1280×720) |
| `youtube/` | upload package: title options, description (with chapters), tags, captions (SRT), thumbnail, pinned comment |

## Build

Requirements: Python 3 with `pygments`, `Pillow`, `numpy` and `scipy`, Node.js 22+, Microsoft Edge (or set
`BROWSER`), and Docker (ffmpeg runs in a container pinned by digest).

```bash
python video/build.py            # everything; output: video/out/postgresql-backups-restore-drills-{full,silent}.mp4
python video/build.py frames     # only re-render the visuals after editing scenes.py
python video/build.py audio      # only re-read the narration (from voiceover/)
python video/build.py video      # only re-encode, and rewrite captions, chapters and the description
python video/build.py post       # voice clean-up, sound effects, -14 LUFS, the full and silent MP4s
python video/build.py licenses   # AUDIO-LICENSES.md
```

How it fits together:
- Each narration step becomes one frame. Elements marked `data-s="n"` appear at step `n`, and the newest one is
  highlighted. Code excerpts highlight the lines the narration talks about.
- Each step's frame stays on screen exactly as long as its narration plus a short pause, rounded to whole video
  frames. The audio track is built from the same timings, so picture and voice cannot drift apart.
- Captions come from the same text as the narration, split into sentences and timed in proportion to their length.
- Words a voice would mispronounce (pgBackRest, WAL, RTO, S3, …) are respelled for the voice only; the exact
  spoken text of every step is in `voiceover/lines.json`. The captions keep the real spelling.
- The voice is cleaned up (high-pass, presence EQ, gentle compression), the sound effects are mixed in, and the
  result is normalised to −14 LUFS, YouTube's playback loudness.

## Facts in the video

Every number comes from [docs/test-results.md](../docs/test-results.md) (one clean end-to-end run, and the same
test in CI) and the raw logs in [reports/](../reports/). Every code excerpt is shortened from the real file named in
its title bar. The dashboard is the real screenshot in `docs/images/grafana-dashboard.png`.

## Upload checklist

1. Upload `out/postgresql-backups-restore-drills-full.mp4`, and use the first title in `youtube/title.txt`. The
   `-silent.mp4` version has the identical picture and no audio track (for re-voicing or other platforms).
2. Paste `youtube/description.md` as the description. Its chapter list turns into YouTube chapters.
3. Set `youtube/thumbnail.png` as the thumbnail, and add the tags from `youtube/tags.txt`.
4. Under Subtitles, upload `youtube/captions.srt` (English), so captions are accurate and searchable.
5. After publishing, pin the comment in `youtube/pinned-comment.txt`.
