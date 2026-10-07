"""The 1-minute vertical short: one entry per voiceover line (see build_short.py).

`say` is the caption; the spoken text is in voiceover/lines.json. Numbers and log lines are from
docs/test-results.md and reports/ (one clean end-to-end run); the dashboard is docs/images/grafana-dashboard.png.
"""

from parts import crop, end_card, logo, term

NAME = "postgres-backups-short"
HEADER = {"logo": "postgresql-icon.svg", "topic": "PostgreSQL backups", "sub": "restore drills · PITR · alerts"}
DASH = "../../docs/images/grafana-dashboard.png"

LINES = [
    {"id": "p01", "say": "Someone dropped the orders table in production. 10 seconds later, every order was back.",
     "sfx": "error", "body": """
<div class="stamp bad" data-at="-1">DROP TABLE orders;</div>
<div class="label dim" data-at="-1"><img class="inl" src="logos/postgresql-icon.svg">IN PRODUCTION</div>
<div class="big ok" data-at="3.0"><span data-count="10">10</span><small>s</small></div>
<div class="label ok" data-at="3.2">EVERY ORDER BACK</div>"""},
    {"id": "p02", "say": "All 123 of them.", "sfx": "success", "body": """
<div class="big ok" data-at="0" style="font-size:220px">123/123</div><div class="label" data-at="0.4">ORDERS RESTORED · 0 LOST</div>"""},
    {"id": "p03", "say": "Here's the problem. Most teams have backups. Almost nobody knows if they actually restore.",
     "sfx": "scene", "body": """
<div class="title" data-at="0.8">Backups exist.</div><div class="title" data-at="2.6"><span class="bad">Do they restore?</span></div>"""},
    {"id": "p04", "say": "Backup jobs fail silently. Files rot. Encryption keys get lost.", "sfx": "error", "body": """
<div class="checks"><div class="check" data-at="0">🤫 jobs fail silently</div><div class="check" data-at="1.4">🧱 files rot</div>
<div class="check" data-at="2.3">🔑 keys get lost</div></div>"""},
    {"id": "p05", "say": "So this database proves it, every single day.", "sfx": "chapter",
     "body": logo("grafana-icon.svg", "Grafana · real run", 0, 72) + crop(DASH, 995, 100, 565, 185, 1000, 1600) + """
<div class="tag ok" data-at="1.0">PROVED EVERY DAY</div>"""},
    {"id": "p06", "say": "Every change is archived to S3, within a minute.", "sfx": "scene",
     "body": logo("postgresql-icon.svg", "PostgreSQL → S3 (WAL)") + """
<div class="big amber" data-at="1.0">60<small>s</small></div><div class="label" data-at="1.2">MAX DATA YOU CAN LOSE</div>"""},
    {"id": "p07", "say": "Every morning, it restores the latest backup into a copy, checks every order, and scans for corruption.",
     "sfx": "scene", "body": """
<div class="checks"><div class="check" data-at="0.8">♻️ restore latest backup</div>
<div class="check" data-at="3.0">🔢 compare every order</div><div class="check" data-at="4.4">🩺 scan for corruption</div></div>"""},
    {"id": "p08", "say": "6 seconds. Zero missing orders.", "sfx": "success",
     "body": term([(0, "[restore-drill] files restored in 4 s", ""),
                   (0.4, "[restore-drill] restored 111 orders, missing 0", "g"),
                   (0.9, "[restore-drill] PASSED in 6 s", "g")], "reports/drill-1.log") + """
<div class="big ok" data-at="1.2" style="font-size:240px">6<small>s</small></div>"""},
    {"id": "p09", "say": "Then I broke it on purpose. I overwrote 4 kilobytes inside one backup file. Same size. Nothing looks wrong.",
     "sfx": "error", "body": """
<div class="stamp bad" data-at="0.3">BIT ROT 💀</div><div class="label" data-at="2.0">4 KiB OVERWRITTEN</div>
<div class="label dim" data-at="4.4">SAME SIZE · LOOKS FINE</div>"""},
    {"id": "p10", "say": "The nightly check caught it, and two alerts fired.", "sfx": "error",
     "body": term([(0.2, "$ scripts/verify.sh", "c"), (0.8, "checksum invalid: 1", "r"),
                   (1.8, "alerts firing: BackupVerifyFailed, RestoreDrillFailed", "y")], "reports/verify-damaged.log")
             + logo("prometheus-icon-color.svg", "2 alerts", 1.8, 72)},
    {"id": "p11", "say": "Storage down for 3.5 minutes? Zero orders lost.", "sfx": "scene",
     "body": crop(DASH, 805, 560, 755, 290, 1000, 1600) + """
<div class="tag ok" data-at="2.4">0 ORDERS LOST</div>"""},
    {"id": "p12", "say": "The whole database disk deleted? Rebuilt from backups in 16 seconds.", "sfx": "success", "body": """
<div class="label bad" data-at="0">💽 DISK DELETED</div><div class="big ok" data-at="2.2"><span data-count="16">16</span><small>s</small></div>
<div class="label ok" data-at="2.4">REBUILT FROM S3</div>"""},
    {"id": "p13", "say": "The full project is free. Follow, and I'll show you how to build it.", "sfx": "outro",
     "body": end_card(["postgresql-icon.svg", "prometheus-icon-color.svg", "grafana-icon.svg"], "Full DevSecOps project")},
]
