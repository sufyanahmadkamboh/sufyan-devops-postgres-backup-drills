"""Building blocks for the short's visuals (used by script.py)."""

from __future__ import annotations

import html


def crop(path: str, x: int, y: int, w: int, h: int, box: int = 1000, iw: int = 1920, at: float = 0) -> str:
    """A screenshot (iw px wide) cropped to one panel (x, y, w, h), shown <box> px wide."""
    k = box / w
    return (f'<div class="shot" data-at="{at}" style="width:{box}px;height:{round(h * k)}px;'
            f"background-image:url('{path}');background-size:{round(iw * k)}px auto;"
            f'background-position:{-round(x * k)}px {-round(y * k)}px"></div>')


def logo(file: str, text: str, at: float = 0, size: int = 92) -> str:
    """A tool logo (logos/<file>) with its name; file=None gives a text-only badge."""
    img = f'<img src="logos/{file}" style="height:{size}px">' if file else ""
    return f'<div class="tool" data-at="{at}">{img}{text}</div>'


def term(lines: list[tuple[float, str, str]], title: str = "") -> str:
    """A terminal with real log lines: (appear-at seconds, text, colour c|r|g|y|'')."""
    bar = f'<div class="tbar">{html.escape(title)}</div>' if title else ""
    body = "".join(f'<div class="{c}" data-at="{a}">{html.escape(t)}</div>' for a, t, c in lines)
    return f'<div class="term" data-at="0">{bar}{body}</div>'


def stats(items: list[tuple[float, str, str, str]]) -> str:
    """Stat tiles: (appear-at, value, label, colour class)."""
    return '<div class="grid2">' + "".join(
        f'<div class="stat" data-at="{a}"><b class="{c}">{v}</b><span>{lab}</span></div>' for a, v, lab, c in items) + "</div>"


# The DevOps infinity loop: Dev (blue) on the left, Ops (green) on the right, security in the middle.
LOOP = """<svg class="loop" viewBox="0 0 1000 520" width="{w}"><defs><linearGradient id="lg{w}" x1="0" x2="1">
<stop offset="0" stop-color="#3b8cff"/><stop offset=".5" stop-color="#9b6bff"/><stop offset="1" stop-color="#38e08a"/></linearGradient></defs>
<path d="M500 260 C 420 120, 120 90, 120 260 C 120 430, 420 400, 500 260 C 580 120, 880 90, 880 260 C 880 430, 580 400, 500 260 Z"
 fill="none" stroke="url(#lg{w})" stroke-width="46" stroke-linejoin="round"/>
<g font-family="Inter,Segoe UI,sans-serif" font-weight="900" font-size="34" fill="#f4f8ff" text-anchor="middle">
<text x="300" y="150">PLAN</text><text x="190" y="272">CODE</text><text x="300" y="392">BUILD</text><text x="378" y="272">TEST</text>
<text x="640" y="272">RELEASE</text><text x="700" y="150">DEPLOY</text><text x="822" y="272">OPERATE</text><text x="700" y="392">MONITOR</text></g>
<text x="300" y="70" font-size="64" font-weight="900" fill="#3b8cff" text-anchor="middle" font-family="Inter,Segoe UI">DEV</text>
<text x="700" y="70" font-size="64" font-weight="900" fill="#38e08a" text-anchor="middle" font-family="Inter,Segoe UI">OPS</text>
<circle cx="500" cy="260" r="50" fill="#070d17" stroke="#ffc23d" stroke-width="8"/>
<text x="500" y="279" font-size="50" text-anchor="middle">🛡️</text>
<text x="500" y="490" font-size="44" font-weight="900" fill="#ffc23d" text-anchor="middle" font-family="Inter,Segoe UI">+ SEC</text></svg>"""


def end_card(logo_files: list[str], what: str) -> str:
    """The last line: DevOps loop, tool logos, "Full DevSecOps project FREE", FOLLOW."""
    imgs = "".join(f'<img src="logos/{f}">' for f in logo_files)
    return (f'<div data-at="0">{LOOP.format(w=760)}</div><div class="logos" data-at="0.4">{imgs}</div>'
            f'<div class="title sm" data-at="0.8">{what} <span class="ok">FREE</span></div>'
            '<div class="follow" data-at="1.8">FOLLOW ➜</div>')
