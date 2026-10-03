# LinkedIn package

| File | Use |
|---|---|
| `post.md` | Post text, written for a beginner audience |
| `carousel/carousel.pdf` | **Recommended:** upload as a *Document* post. LinkedIn shows it as a swipeable carousel |
| `carousel/slide-01.png` … `slide-11.png` | The same slides as images (1080×1350), for a multi-image post |
| `carousel/slides.html` | Source of the slides. Edit it and re-render each slide with a headless browser (`slides.html?s=N`) |
| `project-image.png` | Single architecture image (1200×627) |
| `project-summary.md` | Short technical summary |
| `hashtags.txt` | Hashtags |

## The slides (visual first: one picture per idea, short captions)

| # | Visual | Message |
|---|---|---|
| 1 | "Backup job ✓ / restore never tried" vs "restore ✓ every day, 6 s" | What the project does |
| 2 | 4-panel comic (nightly "success" → months pass → DROP TABLE → corrupt, key lost, too old) | The pain point |
| 3 | Fire-drill cycle: take backup → restore copy → compare → report | The idea |
| 4 | Icon grid + "skip it when" panel | When to use it |
| 5 | 5-step icon flow | How a team uses it |
| 6 | Architecture: app → PostgreSQL → backup host → S3, database blocked from storage | Architecture |
| 7 | Timeline: every ≤60 s, hourly, daily, nightly drill, weekly, alerts | Implementation |
| 8 | Six "broke it on purpose" result tiles | Measured results (lab) |
| 9 | Metro-map learning path through the tools + stats | Study material |
| 10 | Staircase of terminal windows | How to run it yourself |
| 11 | QR codes to the repo and portfolio | Links + question |

## How to post

1. Start a post, choose **Add a document**, and upload `carousel/carousel.pdf`.
2. Give it a title, for example *"Backups you can trust: restore drills explained simply"*.
3. Paste the text from `post.md`.
4. Optional: post `project-image.png` as a single image instead, or upload the 11 PNGs as a multi-image post.
