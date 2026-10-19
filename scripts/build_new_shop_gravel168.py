"""Build curated new-shop gravel list with thumbnails and patch the HTML report.

Usage:
    python scripts/build_new_shop_gravel168.py
    python scripts/build_new_shop_gravel168.py --no-fetch   # skip HTTP image fetch
"""
from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from html import unescape
from pathlib import Path

from curated_new_shop_gravel168 import CATALOG, normalize_item
from export_report import _card
from paths import DEALS, ensure_layout

ROOT = Path(__file__).resolve().parent.parent
OUT_JSON = DEALS / "new_shop_gravel168.json"
DOCS_HTML = ROOT / "docs" / "report-gravel168.html"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def fetch_og_image(url: str, timeout: float = 12.0) -> str | None:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "cs,en;q=0.8",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read(400_000)
            ctype = (resp.headers.get("Content-Type") or "").lower()
    except (urllib.error.URLError, TimeoutError, ValueError):
        return None
    if "html" not in ctype and b"<html" not in raw[:200].lower():
        # still try decode
        pass
    try:
        html = raw.decode("utf-8", errors="replace")
    except Exception:
        return None
    patterns = [
        r'<meta[^>]+property=["\']og:image:secure_url["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image:secure_url["\']',
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
        r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<link[^>]+rel=["\']image_src["\'][^>]+href=["\']([^"\']+)["\']',
    ]
    for pat in patterns:
        m = re.search(pat, html, re.I)
        if m:
            img = unescape(m.group(1).strip())
            if img.startswith("//"):
                img = "https:" + img
            if img.startswith("http") and _usable_image(img):
                return img
    return None


def _usable_image(url: str) -> bool:
    """Drop generic shop share/logo/category images that aren't the bike."""
    bad = (
        "fbshare",
        "facebook/share",
        "og-default",
        "default-og",
        "/logo",
        "placeholder",
        "bike-discount.svg",
        "/categories/",
        "user/categories",
    )
    low = url.lower()
    if low.endswith(".svg"):
        return False
    return not any(b in low for b in bad)


def enrich_images(items: list[dict], fetch: bool = True) -> list[dict]:
    # Drop unusable curated images
    for item in items:
        img = item.get("image_url")
        if img and not _usable_image(img):
            item["image_url"] = None
    if not fetch:
        return items
    need = sorted({i["url"] for i in items if i.get("url") and not i.get("image_url")})
    print(f"Fetching og:image for {len(need)} URLs missing photos...")
    found: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(fetch_og_image, u): u for u in need}
        for fut in as_completed(futs):
            u = futs[fut]
            img = fut.result()
            if img:
                found[u] = img
                print(f"  OK  {u[:70]}…")
            else:
                print(f"  --  {u[:70]}…")
    for item in items:
        if not item.get("image_url") and item.get("url") in found:
            item["image_url"] = found[item["url"]]
    with_img = sum(1 for i in items if i.get("image_url"))
    print(f"Images: {with_img}/{len(items)}")
    return items


def patch_docs_html(items: list[dict]) -> None:
    if not DOCS_HTML.exists():
        print(f"Skip HTML patch — missing {DOCS_HTML}")
        return
    html = DOCS_HTML.read_text(encoding="utf-8")
    cards = "\n".join(_card(e, shop=True) for e in items)
    # Update tab count
    html = re.sub(
        r'(data-tab="nova"[^>]*>Nová / e-shop )\(\d+\)',
        rf"\1({len(items)})",
        html,
        count=1,
    )
    # Replace card list inside panel-nova
    new_panel = (
        '  <section class="deal-section tab-panel" id="panel-nova" role="tabpanel" hidden>\n'
        '    <p class="tab-hint">Nová / outlet z e-shopů (CZ + DE/AT) — slevy, sytější barvy. '
        "Ceny a velikosti se mění; před nákupem ověř na e-shopu. "
        "Položky „nad rozpočtem“ jsou jen tip.</p>\n"
        f'    <div class="card-list sortable">\n{cards}\n</div>\n'
        "  </section>"
    )
    pat = re.compile(
        r'  <section class="deal-section tab-panel" id="panel-nova".*?</section>',
        re.S,
    )
    if not pat.search(html):
        raise SystemExit("panel-nova not found in docs HTML")
    html = pat.sub(new_panel, html, count=1)
    # Bump photo count in subtitle if present (bazar photos stay; shop imgs are extra)
    DOCS_HTML.write_text(html, encoding="utf-8")
    print(f"Patched {DOCS_HTML} ({len(items)} shop items)")


def main() -> None:
    fetch = "--no-fetch" not in sys.argv
    ensure_layout()
    items = [normalize_item(x) for x in CATALOG]
    items = enrich_images(items, fetch=fetch)
    items.sort(key=lambda x: (bool(x.get("over_budget")), x.get("price_czk") or 999999))
    payload = {
        "profile": "gravel168_new_shop",
        "budget_czk_soft": 50000,
        "items": items,
    }
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"Wrote {OUT_JSON} ({len(items)} items)")
    patch_docs_html(items)


if __name__ == "__main__":
    main()
