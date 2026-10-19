"""Export merged_deals.json to readable HTML (and optional text)."""
from __future__ import annotations

import html
import json
import sys
from datetime import datetime
from pathlib import Path

from filters import eur_to_czk
from image_urls import load_index, lookup
from paths import MERGED_MTB183, REPORT_MTB183_HTML, REPORT_MTB183_TXT, ensure_layout

DEFAULT_IN = MERGED_MTB183
HTML_OUT = REPORT_MTB183_HTML
TXT_OUT = REPORT_MTB183_TXT


def _esc(s: str) -> str:
    return html.escape(s or "")


def _fmt_price(e: dict) -> str:
    """€1234 (30 850 Kč) — EUR primary, CZK in parentheses for every bike."""
    if e.get("price_eur") is None:
        return "?"
    eur = float(e["price_eur"])
    czk = e.get("price_czk")
    if czk is None:
        czk = eur_to_czk(eur)
    czk_i = int(round(float(czk)))
    czk_s = f"{czk_i:,}".replace(",", "\u00a0")
    return f"€{eur:.0f} ({czk_s} Kč)"


def _enrich(report: dict, index: dict[str, str]) -> None:
    for key in ("pinned", "top_at", "top_cz", "top_market", "top", "all"):
        for e in report.get(key, []):
            if not e.get("image_url"):
                e["image_url"] = lookup(index, e)


def _list_items(report: dict) -> tuple[list[dict], set[str]]:
    """All listings for display, including pinned items missing from `all`."""
    pinned_urls = {e.get("url") for e in report.get("pinned", []) if e.get("url")}
    seen: set[str] = set()
    items: list[dict] = []
    for e in report.get("all", []):
        url = e.get("url")
        if url and url not in seen:
            seen.add(url)
            items.append(e)
    for e in report.get("pinned", []):
        url = e.get("url")
        if url and url not in seen:
            seen.add(url)
            items.append(e)
    items.sort(
        key=lambda e: (
            0 if e.get("url") in pinned_urls else 1,
            -e.get("score", 0),
            e.get("price_eur") or 9999,
        )
    )
    return items, pinned_urls


def _card(e: dict, highlight: bool = False, shop: bool = False) -> str:
    price = _fmt_price(e)
    price_num = e.get("price_eur") if e.get("price_eur") is not None else 999999
    score = e.get("score", 0)
    year = f"MY{e['year']}" if e.get("year") else "rok?"
    notes = ", ".join(e.get("notes") or [])
    cls = "card pinned" if highlight else "card"
    if e.get("over_budget"):
        cls += " over-budget"
    img = e.get("image_url")
    img_html = ""
    if img:
        img_html = (
            f'<a class="thumb" href="{_esc(e.get("url", ""))}" target="_blank" rel="noopener">'
            f'<img src="{_esc(img)}" alt="" loading="lazy" referrerpolicy="no-referrer"></a>'
        )
    if shop:
        disc = ""
        if e.get("discount_pct"):
            disc = f" · −{int(e['discount_pct'])} %"
        was = ""
        if e.get("price_was_czk"):
            was_s = f"{int(e['price_was_czk']):,}".replace(",", "\u00a0")
            was = f' <span class="was">bylo {was_s} Kč</span>'
        color = e.get("color") or ""
        spec = e.get("spec") or e.get("travel") or ""
        meta = f"{year} · vel. {_esc(str(e.get('fit', '?')))}{disc}"
        if color:
            meta += f" · {_esc(color)}"
        return f"""<article class="{cls}" data-price="{price_num}" data-score="{score}">
  <div class="card-body">
    {img_html}
    <div class="card-text">
      <div class="row">
        <span class="price">{_esc(price)}{was}</span>
        <span class="meta">{meta}</span>
        <span class="src">{_esc(str(e.get('source', '')))}</span>
      </div>
      <h3><a href="{_esc(e.get('url', ''))}" target="_blank" rel="noopener">{_esc(e.get('title', ''))}</a></h3>
      <p class="loc">{_esc(e.get('location', ''))}</p>
      {f'<p class="notes">{_esc(spec)}</p>' if spec else ''}
      {f'<p class="notes">{_esc(notes)}</p>' if notes else ''}
    </div>
  </div>
</article>"""
    return f"""<article class="{cls}" data-price="{price_num}" data-score="{score}">
  <div class="card-body">
    {img_html}
    <div class="card-text">
      <div class="row">
        <span class="price">{_esc(price)}</span>
        <span class="meta">{_esc(year)} · {_esc(str(e.get('travel', '')))} · vel. {_esc(str(e.get('fit', '')))} · score {e.get('score', 0)}</span>
        <span class="src">{_esc(str(e.get('source', '')))}</span>
      </div>
      <h3><a href="{_esc(e.get('url', ''))}" target="_blank" rel="noopener">{_esc(e.get('title', ''))}</a></h3>
      <p class="loc">{_esc(e.get('location', ''))}</p>
      {f'<p class="notes">{_esc(notes)}</p>' if notes else ''}
    </div>
  </div>
</article>"""


def write_html(report: dict, path: Path = HTML_OUT) -> Path:
    index = load_index()
    _enrich(report, index)

    by_src = report.get("by_source", {})
    price_min = report.get("price_min_eur", 800)
    price_max = report.get("price_max_eur", 1900)
    fit_label = report.get("fit_label", "M/L")
    heading = report.get("heading", "MTB trail / AM deals")
    page_title = report.get("page_title", "MTB trail deals — report")
    generated = datetime.now().strftime("%Y-%m-%d %H:%M")
    with_img = sum(1 for e in report.get("all", []) if e.get("image_url"))
    subtitle = report.get(
        "subtitle",
        f"€{price_min:.0f}–€{price_max:.0f} · full-sus · {fit_label} · 2019+",
    )

    items, pinned_urls = _list_items(report)
    shop_new = list(report.get("shop_new") or [])
    cards = "\n".join(
        _card(e, highlight=e.get("url") in pinned_urls) for e in items
    )
    shop_cards = "\n".join(_card(e, shop=True) for e in shop_new)

    src_rows = "".join(
        f"<tr><td>{_esc(k)}</td><td>{v}</td></tr>" for k, v in sorted(by_src.items(), key=lambda x: -x[1])
    )

    if shop_new:
        body_list = f"""
  <div class="tabs" role="tablist">
    <button type="button" class="tab active" data-tab="bazar" role="tab" aria-selected="true">Bazar ({len(items)})</button>
    <button type="button" class="tab" data-tab="nova" role="tab" aria-selected="false">Nová / e-shop ({len(shop_new)})</button>
  </div>
  <section class="deal-section tab-panel active" id="panel-bazar" role="tabpanel">
    <p class="tab-hint">Bazárové inzeráty (AT/CZ) — ověřené odkazy, velikost dle značky pro ~168&nbsp;cm.</p>
    <table>
      <thead><tr><th>Zdroj</th><th>Počet</th></tr></thead>
      <tbody>{src_rows}</tbody>
    </table>
    <div class="card-list sortable">\n{cards}\n</div>
  </section>
  <section class="deal-section tab-panel" id="panel-nova" role="tabpanel" hidden>
    <p class="tab-hint">Nová / outlet z e-shopů (CZ + DE/AT) — slevy, sytější barvy. Ceny a velikosti se mění; před nákupem ověř na e-shopu. Položky „nad rozpočtem“ jsou jen tip.</p>
    <div class="card-list sortable">\n{shop_cards}\n</div>
  </section>"""
    else:
        body_list = (
            f'<section class="deal-section">'
            f'<h2>Inzeráty ({len(items)})</h2>\n'
            f'<table><thead><tr><th>Zdroj</th><th>Počet</th></tr></thead>'
            f'<tbody>{src_rows}</tbody></table>\n'
            f'<div class="card-list sortable">\n{cards}\n</div>\n</section>'
            if items
            else ""
        )

    tabs_js = ""
    if shop_new:
        tabs_js = """
  document.querySelectorAll(".tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((b) => {
        b.classList.toggle("active", b === btn);
        b.setAttribute("aria-selected", b === btn ? "true" : "false");
      });
      document.querySelectorAll(".tab-panel").forEach((p) => {
        const on = p.id === "panel-" + btn.dataset.tab;
        p.classList.toggle("active", on);
        p.hidden = !on;
      });
    });
  });
"""

    doc = f"""<!DOCTYPE html>
<html lang="cs">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_esc(page_title)}</title>
  <style>
    :root {{ font-family: system-ui, Segoe UI, sans-serif; line-height: 1.45; }}
    body {{ max-width: 960px; margin: 0 auto; padding: 1rem 1.25rem 3rem; background: #f6f7f9; color: #1a1a1a; }}
    h1 {{ margin-bottom: 0.25rem; }}
    .sub {{ color: #555; margin-top: 0; }}
    table {{ border-collapse: collapse; margin: 1rem 0; background: #fff; }}
    th, td {{ border: 1px solid #ddd; padding: 0.4rem 0.75rem; text-align: left; }}
    section {{ margin-top: 1.25rem; }}
    section h2 {{ border-bottom: 2px solid #2d6a4f; padding-bottom: 0.35rem; }}
    .tabs {{ display: flex; gap: 0.5rem; margin: 1rem 0 0.5rem; flex-wrap: wrap; }}
    .tab {{
      font: inherit; font-weight: 600; cursor: pointer; border: 1px solid #c5cdd4;
      background: #fff; color: #333; border-radius: 999px; padding: 0.45rem 1rem;
    }}
    .tab.active {{ background: #1b4332; color: #fff; border-color: #1b4332; }}
    .tab-hint {{ color: #555; font-size: 0.92rem; margin: 0.5rem 0 1rem; }}
    .card {{ background: #fff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 0.85rem 1rem; margin: 0.65rem 0; }}
    .card.pinned {{ border-color: #2d6a4f; box-shadow: 0 0 0 2px #2d6a4f22; }}
    .card.over-budget {{ opacity: 0.85; border-style: dashed; }}
    .card-body {{ display: flex; gap: 1rem; align-items: flex-start; }}
    .thumb {{ flex: 0 0 auto; display: block; }}
    .thumb img {{ width: 140px; height: 105px; object-fit: cover; border-radius: 6px; background: #eee; border: 1px solid #ddd; }}
    .card-text {{ flex: 1; min-width: 0; }}
    .row {{ display: flex; flex-wrap: wrap; gap: 0.5rem 1rem; align-items: baseline; font-size: 0.9rem; }}
    .price {{ font-weight: 700; font-size: 1.15rem; color: #1b4332; }}
    .was {{ font-weight: 400; font-size: 0.85rem; color: #888; text-decoration: line-through; margin-left: 0.35rem; }}
    .meta, .loc, .notes {{ color: #555; margin: 0.25rem 0; }}
    .src {{ margin-left: auto; font-size: 0.8rem; color: #888; }}
    h3 {{ margin: 0.35rem 0; font-size: 1.05rem; }}
    h3 a {{ color: #1565c0; text-decoration: none; }}
    h3 a:hover {{ text-decoration: underline; }}
    .toolbar {{
      display: flex; flex-wrap: wrap; gap: 0.75rem 1.5rem; align-items: center;
      background: #fff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 0.75rem 1rem; margin: 1rem 0;
    }}
    .toolbar label {{ display: flex; align-items: center; gap: 0.5rem; font-size: 0.95rem; }}
    .toolbar select {{ font: inherit; padding: 0.35rem 0.5rem; border-radius: 4px; border: 1px solid #ccc; }}
    @media (max-width: 520px) {{
      .card-body {{ flex-direction: column; }}
      .thumb img {{ width: 100%; height: auto; max-height: 200px; }}
    }}
  </style>
</head>
<body>
  <h1>{_esc(heading)}</h1>
  <p class="sub">{_esc(subtitle)} · vygenerováno {generated} · fotek {with_img}/{len(report.get('all', []))}</p>
  <div class="toolbar">
    <label for="sort-mode">Řazení
      <select id="sort-mode" aria-label="Řazení inzerátů">
        <option value="score-desc">Vyhodnost (nejlepší první)</option>
        <option value="price-asc">Cena (nejlevnější)</option>
        <option value="price-desc">Cena (nejvyšší)</option>
      </select>
    </label>
  </div>
  {body_list}
  <script>
(function () {{
  const KEY = "mtb-report-sort";
  const select = document.getElementById("sort-mode");
  if (!select) return;

  function cmp(a, b, mode) {{
    const pa = parseFloat(a.dataset.price) || 999999;
    const pb = parseFloat(b.dataset.price) || 999999;
    const sa = parseFloat(a.dataset.score) || 0;
    const sb = parseFloat(b.dataset.score) || 0;
    if (mode === "price-asc") return pa - pb || sb - sa;
    if (mode === "price-desc") return pb - pa || sb - sa;
    return sb - sa || pa - pb;
  }}

  function applySort(mode) {{
    document.querySelectorAll(".card-list.sortable").forEach((list) => {{
      const cards = Array.from(list.querySelectorAll(":scope > article.card"));
      cards.sort((a, b) => cmp(a, b, mode));
      cards.forEach((c) => list.appendChild(c));
    }});
  }}

  const saved = localStorage.getItem(KEY);
  if (saved && select.querySelector('option[value="' + saved + '"]')) {{
    select.value = saved;
  }}
  applySort(select.value);

  select.addEventListener("change", () => {{
    localStorage.setItem(KEY, select.value);
    applySort(select.value);
  }});
{tabs_js}
}})();
  </script>
</body>
</html>"""
    ensure_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(doc, encoding="utf-8")
    return path


def write_txt(report: dict, path: Path = TXT_OUT) -> Path:
    heading = report.get("heading", "MTB trail deals")
    lines = [f"{heading} — {datetime.now():%Y-%m-%d %H:%M}", ""]

    def block(title: str, items: list[dict]) -> None:
        if not items:
            return
        lines.append(f"=== {title} ===")
        lines.append("")
        for e in items:
            price = _fmt_price(e)
            yr = f"MY{e['year']}" if e.get("year") else "rok?"
            lines.append(
                f"{price} | {yr} | {e.get('travel', '')} | {e.get('fit', '')} | "
                f"score {e.get('score', 0)} | [{e.get('source')}]"
            )
            lines.append(f"  {e.get('title', '')}")
            if e.get("location"):
                lines.append(f"  {e['location']}")
            lines.append(f"  {e.get('url', '')}")
            lines.append("")

    all_items, _ = _list_items(report)
    block(f"INZERÁTY ({len(all_items)})", all_items)

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def export(
    report: dict | None = None,
    inp: Path = DEFAULT_IN,
    html_out: Path = HTML_OUT,
    txt_out: Path = TXT_OUT,
) -> tuple[Path, Path]:
    if report is None:
        report = json.load(open(inp, encoding="utf-8"))
    html_path = write_html(report, path=html_out)
    txt_path = write_txt(report, path=txt_out)
    return html_path, txt_path


def main() -> None:
    inp = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_IN
    html_path, txt_path = export(inp=inp)
    print(f"HTML: {html_path}")
    print(f"Text: {txt_path}")


if __name__ == "__main__":
    main()
