"""Build a static site in docs/ for GitHub Pages.

Copies generated reports and creates a landing page (rozcestník).
The report HTML files are self-contained (images are hot-linked from CDNs),
so docs/ needs no data/ folder.

Run:
    python mtb/scripts/publish_site.py
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

from paths import (
    MERGED_GRAVEL168,
    MERGED_MTB183,
    MERGED_ROAD168,
    MERGED_W175,
    REPORT_GRAVEL168_HTML,
    REPORT_MTB183_HTML,
    REPORT_ROAD168_HTML,
    REPORT_W175_HTML,
)

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"

REPORTS = [
    {
        "src": REPORT_MTB183_HTML,
        "out": "report-183.html",
        "merged": MERGED_MTB183,
        "title": "Trail / All-Mountain — ~183 cm",
        "fit": "velikost M / L",
        "travel": "~130–170 mm",
        "price": "€800–1900",
        "desc": "Celoodpružená trail/AM kola pro vyššího jezdce (~183 cm).",
    },
    {
        "src": REPORT_W175_HTML,
        "out": "report-175.html",
        "merged": MERGED_W175,
        "title": "Enduro / All-Mountain — ~175 cm",
        "fit": "velikost S / M",
        "travel": "~140–180 mm",
        "price": "€600–1900",
        "desc": "Enduro/AM kola pro nižší jezdkyni (~175 cm, klidně o něco méně) — flow traily, bikeparky, ale vyjede i nahoru.",
    },
    {
        "src": REPORT_ROAD168_HTML,
        "out": "report-road168.html",
        "merged": MERGED_ROAD168,
        "title": "Silniční kolo — žena ~168 cm",
        "fit": "velikost XS / S (≈47–53 cm)",
        "travel": "karbon nebo 105+",
        "price": "€400–1600 (do ~40 tis. Kč)",
        "desc": "Silniční kola 2021+, ideálně karbonový rám nebo řazení Shimano 105 / SRAM Rival a výš, v dobrém stavu.",
    },
    {
        "src": REPORT_GRAVEL168_HTML,
        "out": "report-gravel168.html",
        "merged": MERGED_GRAVEL168,
        "title": "Gravel / Endurance — žena ~168 cm",
        "fit": "velikost XS / S (≈47–53 cm)",
        "travel": "gravel nebo endurance · karbon nebo 105+",
        "price": "€400–1600 (do ~40 tis. Kč)",
        "desc": "Gravel a endurance silniční kola 2021+, XS/S, ideálně karbon nebo řazení 105 / Rival+.",
    },
]


def _count(path: Path) -> int:
    if not path.exists():
        return 0
    d = json.load(open(path, encoding="utf-8"))
    return len(d.get("all", []))


def _card(r: dict) -> str:
    n = _count(r["merged"])
    return f"""    <a class="card" href="{r['out']}">
      <h2>{r['title']}</h2>
      <p class="tags"><span>{r['fit']}</span><span>{r['travel']}</span><span>{r['price']}</span></p>
      <p class="desc">{r['desc']}</p>
      <p class="count">{n} aktivních inzerátů →</p>
    </a>"""


def build_index() -> str:
    cards = "\n".join(_card(r) for r in REPORTS if r["src"].exists())
    generated = datetime.now().strftime("%Y-%m-%d %H:%M")
    return f"""<!DOCTYPE html>
<html lang="cs">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Bazar kol — přehledy</title>
  <style>
    :root {{ font-family: system-ui, "Segoe UI", sans-serif; line-height: 1.5; }}
    body {{ max-width: 760px; margin: 0 auto; padding: 2.5rem 1.25rem 4rem; background: #f6f7f9; color: #1a1a1a; }}
    h1 {{ margin-bottom: 0.25rem; font-size: 1.9rem; }}
    .sub {{ color: #555; margin-top: 0; }}
    .cards {{ display: grid; gap: 1rem; margin-top: 2rem; }}
    .card {{
      display: block; background: #fff; border: 1px solid #e0e0e0; border-radius: 12px;
      padding: 1.25rem 1.4rem; text-decoration: none; color: inherit;
      transition: box-shadow .15s, transform .15s, border-color .15s;
    }}
    .card:hover {{ box-shadow: 0 6px 22px #0000001a; transform: translateY(-2px); border-color: #2d6a4f; }}
    .card h2 {{ margin: 0 0 .5rem; font-size: 1.25rem; color: #1b4332; }}
    .tags {{ display: flex; flex-wrap: wrap; gap: .4rem; margin: .3rem 0 .6rem; }}
    .tags span {{ background: #e7f0ea; color: #1b4332; border-radius: 999px; padding: .15rem .7rem; font-size: .8rem; }}
    .desc {{ color: #444; margin: .4rem 0 .8rem; }}
    .count {{ margin: 0; font-weight: 600; color: #1565c0; }}
    footer {{ margin-top: 2.5rem; color: #888; font-size: .85rem; }}
  </style>
</head>
<body>
  <h1>Bazar kol — přehledy</h1>
  <p class="sub">Trail/enduro MTB, silniční a gravel/endurance z rakouských a českých bazarů. Odkazy jsou ověřené jako aktivní.</p>
  <div class="cards">
{cards}
  </div>
  <footer>Vygenerováno {generated} · data z willhaben.at, cyklobazar.cz, bazos.cz a dalších.</footer>
</body>
</html>"""


def main() -> None:
    DOCS.mkdir(exist_ok=True)
    copied = []
    for r in REPORTS:
        if r["src"].exists():
            shutil.copyfile(r["src"], DOCS / r["out"])
            copied.append(r["out"])
    (DOCS / "index.html").write_text(build_index(), encoding="utf-8")
    (DOCS / ".nojekyll").write_text("", encoding="utf-8")
    print("Built docs/:")
    print("  index.html")
    for c in copied:
        print(f"  {c}")


if __name__ == "__main__":
    main()
