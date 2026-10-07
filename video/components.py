"""HTML building blocks for the video scenes (1920x1080).

Every element that should appear at a given narration step carries data-s="<step>". The page shows an element
when the current step is >= its data-s, and highlights it while the step is exactly its data-s.
"""

from __future__ import annotations

import html

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name

TONES = {"blue": "#3b82d6", "ok": "#4cc286", "bad": "#ff6b6b", "amber": "#ffc94d", "sky": "#9cc3f0", "violet": "#b48cff"}


def esc(text: str) -> str:
    return html.escape(text, quote=True)


def card(s: int, icon: str, title: str, text: str = "", tone: str = "blue") -> str:
    return (f'<div class="card st" data-s="{s}" style="--tone:{TONES[tone]}">'
            f'<div class="card-icon">{icon}</div><div><div class="card-title">{title}</div>'
            f'<div class="card-text">{text}</div></div></div>')


def grid(cards: list[str], cols: int = 3, gap: int = 26) -> str:
    return f'<div class="grid" style="grid-template-columns:repeat({cols},1fr);gap:{gap}px">{"".join(cards)}</div>'


def tile(s: int, icon: str, label: str, value: str, tone: str = "ok", note: str = "") -> str:
    return (f'<div class="tile st" data-s="{s}" style="--tone:{TONES[tone]}"><div class="tile-icon">{icon}</div>'
            f'<div class="tile-label">{label}</div><div class="tile-value">{value}</div>'
            f'<div class="tile-note">{note}</div></div>')


def notes(items: list[tuple[int, str, str]]) -> str:
    out = "".join(f'<li class="st" data-s="{s}"><b>{t}</b><span>{x}</span></li>' for s, t, x in items)
    return f'<ul class="notes">{out}</ul>'


def checklist(items: list[tuple[int, str, str, str]]) -> str:
    out = "".join(f'<li class="st" data-s="{s}"><div class="num">{n}</div><div><b>{t}</b><span>{x}</span></div></li>'
                  for s, n, t, x in items)
    return f'<ul class="checklist">{out}</ul>'


def code(path: str, src: str, lang: str = "yaml", size: int = 21) -> str:
    """A syntax-highlighted file excerpt; every line is <span id="L-n"> so steps can highlight line ranges."""
    lexer = get_lexer_by_name(lang)
    lines = highlight(src.strip("\n"), lexer, HtmlFormatter(nowrap=True)).rstrip("\n").split("\n")
    body = "".join(f'<span id="L-{i}">{line or " "}</span>' for i, line in enumerate(lines, 1))
    return (f'<div class="code" style="--fs:{size}px"><div class="code-bar"><i></i><i></i><i></i>'
            f'<span>{esc(path)}</span></div><pre>{body}</pre></div>')


def terminal(lines: list[tuple[int, str, str]], title: str = "terminal") -> str:
    out = "".join(f'<div class="tl st {cls}" data-s="{s}">{esc(t)}</div>' for s, t, cls in lines)
    return f'<div class="term"><div class="code-bar"><i></i><i></i><i></i><span>{esc(title)}</span></div>{out}</div>'


def svg(inner: str, w: int = 1720, h: int = 740) -> str:
    return f'<svg class="dia" viewBox="0 0 {w} {h}" width="{w}" height="{h}">{inner}</svg>'


# Arrow markers live in one always-rendered <svg> at the top of the page (build.py):
# markers defined inside a hidden scene do not render anywhere.
SVG_DEFS = """<svg width="0" height="0" style="position:absolute"><defs>
<marker id="ar" markerUnits="userSpaceOnUse" markerWidth="26" markerHeight="26" refX="20" refY="13" orient="auto"><path d="M0,0 L26,13 L0,26 z" fill="#9cc3f0"/></marker>
<marker id="arr" markerUnits="userSpaceOnUse" markerWidth="26" markerHeight="26" refX="20" refY="13" orient="auto"><path d="M0,0 L26,13 L0,26 z" fill="#ff6b6b"/></marker>
<marker id="arg" markerUnits="userSpaceOnUse" markerWidth="26" markerHeight="26" refX="20" refY="13" orient="auto"><path d="M0,0 L26,13 L0,26 z" fill="#4cc286"/></marker>
</defs></svg>"""


def box(s: int, x: int, y: int, w: int, h: int, icon: str, title: str, lines: list[str] = (), tone: str = "blue",
        fill: str = "#13233a") -> str:
    """An SVG box with an emoji icon, a title and up to 4 small lines."""
    t = TONES[tone]
    sub = "".join(f'<text x="{x + 24}" y="{y + 96 + i * 32}" font-size="23" fill="#c9d6e6">{esc(line)}</text>'
                  for i, line in enumerate(lines))
    return (f'<g class="st" data-s="{s}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="22" fill="{fill}" '
            f'stroke="{t}" stroke-width="3"/><text x="{x + 22}" y="{y + 56}" font-size="40">{icon}</text>'
            f'<text x="{x + 80}" y="{y + 52}" font-size="29" font-weight="800" fill="#f1f6fc">{esc(title)}</text>{sub}</g>')


def arrow(s: int, x1: int, y1: int, x2: int, y2: int, tone: str = "sky", dash: bool = False, label: str = "") -> str:
    m = {"sky": "ar", "bad": "arr", "ok": "arg"}[tone]
    d = ' stroke-dasharray="14 10"' if dash else ""
    lab = (f'<text x="{(x1 + x2) / 2}" y="{(y1 + y2) / 2 - 16}" text-anchor="middle" font-size="21" font-weight="700" '
           f'fill="{TONES[tone]}">{esc(label)}</text>') if label else ""
    return (f'<g class="st" data-s="{s}"><line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{TONES[tone]}" '
            f'stroke-width="6"{d} marker-end="url(#{m})"/>{lab}</g>')


def label(s: int, x: int, y: int, text: str, size: int = 26, tone: str = "sky", anchor: str = "start",
          weight: int = 700) -> str:
    return (f'<text class="st" data-s="{s}" x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
            f'fill="{TONES.get(tone, tone)}" text-anchor="{anchor}">{esc(text)}</text>')
