"""Scrape radbazar.at — Austrian bike marketplace."""
from __future__ import annotations

from paths import SCRAPE_MTB, ensure_layout

import json
import re
import time
import urllib.parse
import urllib.request
from html import unescape
from pathlib import Path

from filters import PRICE_EUR_MAX, PRICE_EUR_MIN

ROOT = Path(__file__).resolve().parent.parent
OUT = SCRAPE_MTB / "radbazar_listings.json"
BASE = "https://www.radbazar.at"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"}

LIST_URLS = [
    f"{BASE}/categories/fahrrader/mountainbikes/fully",
    f"{BASE}/categories/fahrrader/mountainbikes",
]
MAX_PAGES = 8
FETCH_DETAILS = False


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=45) as r:
        return unescape(r.read().decode("utf-8", errors="replace"))


def parse_eur_price(raw: str) -> float | None:
    """Parse AT/DE prices: '1.490', '9.979', '1.234,50', '650 €'."""
    raw = raw.replace("\xa0", " ").replace("€", "").strip()
    raw = re.sub(r"[^\d.,]", "", raw)
    if not raw:
        return None
    if re.fullmatch(r"\d{1,3}(\.\d{3})+(,\d{1,2})?", raw):
        raw = raw.replace(".", "").replace(",", ".")
    elif "," in raw:
        raw = raw.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d+\.\d{3}", raw):
        raw = raw.replace(".", "")
    try:
        return float(raw)
    except ValueError:
        return None


def parse_list_page(html: str) -> list[dict]:
    items: list[dict] = []
    seen: set[str] = set()
    for m in re.finditer(
        r'<a href="(https://www\.radbazar\.at/listing/([a-f0-9-]+))"[^>]*class="font-medium[^"]*"[^>]*>\s*([^<]+?)\s*</a>',
        html,
        re.DOTALL,
    ):
        url, lid, title = m.groups()
        if lid in seen:
            continue
        # Image BEFORE title; price AFTER — separate windows so cards don't mix.
        before = html[max(0, m.start() - 1200) : m.start()]
        after = html[m.end() : m.end() + 500]
        price_m = re.search(r'<p class="font-bold mt-1">\s*([^<]+?)\s*</p>', after)
        imgs = re.findall(r'<img src="(https://www\.radbazar\.at/storage/[^"]+)"', before)
        image_url = imgs[-1] if imgs else None
        price = parse_eur_price(price_m.group(1)) if price_m else None
        if price is None or price < PRICE_EUR_MIN or price > PRICE_EUR_MAX:
            continue
        seen.add(lid)
        items.append({
            "id": lid,
            "source": "radbazar.at",
            "title": re.sub(r"\s+", " ", title).strip(),
            "description": "",
            "price_eur": price,
            "location": "Österreich",
            "url": url,
            "image_url": image_url,
        })
    return items


def main() -> None:
    all_items: dict[str, dict] = {}
    for base_url in LIST_URLS:
        for page in range(1, MAX_PAGES + 1):
            params = urllib.parse.urlencode({
                "price_min": int(PRICE_EUR_MIN),
                "price_max": int(PRICE_EUR_MAX),
                "page": page,
            })
            url = f"{base_url}?{params}"
            print(f"fetch {url}")
            try:
                html = fetch(url)
            except Exception as e:
                print(f"  fail: {e}")
                break
            batch = parse_list_page(html)
            print(f"  page {page}: {len(batch)} in budget")
            if not batch:
                break
            for it in batch:
                all_items[it["id"]] = it
            time.sleep(0.4)

    items = list(all_items.values())
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(items)} -> {OUT}")


if __name__ == "__main__":
    main()
