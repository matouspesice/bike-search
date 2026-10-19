"""Scrape gravel / endurance listings into data/scrapes/gravel/.

Does not overwrite MTB or road scrapes. Price band ~€400–€1600
(≈ 10–40 tis. Kč).

Run:
    python mtb/scripts/scrape_gravel.py
"""
from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
from html import unescape
from pathlib import Path

from paths import SCRAPE_GRAVEL, ensure_layout

DATA = SCRAPE_GRAVEL

# ~10–40 tis. Kč
CZK_PER_EUR = 25.0
PRICE_EUR_MIN = 400
PRICE_EUR_MAX = 1600
CENA_OD = int(PRICE_EUR_MIN * CZK_PER_EUR)
CENA_DO = int(PRICE_EUR_MAX * CZK_PER_EUR)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "cs,de-AT;q=0.9,en;q=0.8",
}

BUYCYCLE_HEADERS = {
    **HEADERS,
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Referer": "https://www.buycycle.com/",
}


def fetch(url: str, headers: dict | None = None) -> str:
    req = urllib.request.Request(url, headers=headers or HEADERS)
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read().decode("utf-8", errors="replace")


def save(name: str, items: list[dict]) -> None:
    ensure_layout()
    path = DATA / name
    with open(path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    print(f"  Saved {len(items)} -> {path}")


# ── willhaben.at: Cross/Trekking + Rennräder (endurance filtered later) ─────

def scrape_willhaben() -> None:
    print("\n=== willhaben.at gravel/cross + rennrad ===")
    categories = [
        (
            "cross/trekking",
            "https://www.willhaben.at/iad/kaufen-und-verkaufen/marktplatz/"
            "fahrraeder/trekkingfahrraeder-crossbikes-4562",
        ),
        (
            "rennrad",
            "https://www.willhaben.at/iad/kaufen-und-verkaufen/marktplatz/"
            "fahrraeder/rennraeder-4560",
        ),
    ]
    params = {
        "rows": "90",
        "isNavigation": "true",
        "PRICE_FROM": str(PRICE_EUR_MIN),
        "PRICE_TO": str(PRICE_EUR_MAX),
    }

    def extract_next(html: str) -> dict | None:
        m = re.search(
            r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
            html,
            re.DOTALL,
        )
        return json.loads(m.group(1)) if m else None

    def find_ads(data: dict) -> list[dict]:
        found: list[dict] = []

        def walk(obj):
            if isinstance(obj, dict):
                keys = set(obj.keys())
                if {"id", "description", "attributes"}.issubset(keys) or (
                    "id" in keys and "description" in keys and "advertImageList" in keys
                ):
                    found.append(obj)
                elif "id" in keys and "description" in keys and any(
                    k in keys for k in ("heading", "teaser", "advertiserInfo")
                ):
                    found.append(obj)
                for v in obj.values():
                    walk(v)
            elif isinstance(obj, list):
                for v in obj:
                    walk(v)

        walk(data)
        seen: set[str] = set()
        out: list[dict] = []
        for item in found:
            aid = item.get("id")
            if aid and aid not in seen:
                seen.add(aid)
                out.append(item)
        return out

    all_items: list[dict] = []
    for cat_name, base in categories:
        print(f"  category {cat_name}")
        max_pages = 25 if cat_name == "rennrad" else 20
        for page in range(1, max_pages + 1):
            qs = urllib.parse.urlencode({**params, "page": str(page)})
            url = f"{base}?{qs}"
            print(f"    page {page}...", end=" ", flush=True)
            try:
                html = fetch(url)
                nd = extract_next(html)
                if not nd:
                    print("no data")
                    break
                ads = find_ads(nd)
                print(f"{len(ads)} ads")
                if not ads:
                    break
                for raw in ads:
                    all_items.append({
                        "id": raw.get("id"),
                        "description": raw.get("description") or raw.get("teaser") or "",
                        "attributes": raw.get("attributes") or {},
                    })
                if len(ads) < 30:
                    break
                time.sleep(0.35)
            except Exception as e:
                print(f"error: {e}")
                break

    seen: set[str] = set()
    uniq: list[dict] = []
    for it in all_items:
        aid = str(it.get("id"))
        if aid in seen:
            continue
        seen.add(aid)
        uniq.append(it)
    save("at_listings.json", uniq)


# ── bazos.cz ────────────────────────────────────────────────────────────────

def scrape_bazos() -> None:
    print("\n=== bazos.cz gravel/endurance ===")
    base = "https://sport.bazos.cz"
    queries = [
        "gravel", "gravel kolo", "endurance", "allroad", "grx",
        "diverge", "checkpoint", "topstone", "grizl", "grail",
        "nuroad", "silex", "kanzo", "revolt", "devote", "domane",
        "endurace", "orbea terra", "ridley",
    ]

    def parse_list(html: str) -> list[dict]:
        items: list[dict] = []
        for block in re.split(r'<div class="inzeraty inzeratyflex">', html)[1:]:
            m_url = re.search(r'<h2 class=nadpis><a href="([^"]+)">([^<]+)</a>', block)
            if not m_url:
                continue
            path, title = m_url.groups()
            m_price = re.search(r"inzeratycena.*?<b>.*?([\d\s]+)\s*Kč", block, re.DOTALL)
            m_loc = re.search(r'inzeratylok">([^<]+)<br>([^<]*)<', block)
            m_popis = re.search(r'<div class=popis>(.*?)</div>', block, re.DOTALL)
            popis = re.sub(r"<[^>]+>", "", m_popis.group(1)) if m_popis else ""
            popis = re.sub(r"\s+", " ", popis).strip()
            raw_price = re.sub(r"[^\d]", "", m_price.group(1)) if m_price else ""
            price = float(raw_price) if raw_price else None
            loc = (
                f"{m_loc.group(1).strip()} {m_loc.group(2).strip()}".strip()
                if m_loc
                else ""
            )
            full_url = path if path.startswith("http") else base + path
            ad_id = re.search(r"/inzerat/(\d+)/", path)
            aid = ad_id.group(1) if ad_id else path
            img_m = re.search(r'<img[^>]+src="([^"]+)"[^>]*class="obrazek"', block)
            image_url = img_m.group(1) if img_m else None
            if not image_url and str(aid).isdigit():
                image_url = f"https://www.bazos.cz/img/1t/{str(aid)[-3:]}/{aid}.jpg"
            items.append({
                "id": aid,
                "source": "bazos.cz",
                "title": title.strip(),
                "description": popis,
                "price_czk": price,
                "price_eur": round(price / CZK_PER_EUR, 0) if price else None,
                "location": loc,
                "url": full_url,
                "image_url": image_url,
            })
        return items

    def fetch_detail(item: dict) -> str:
        try:
            html = fetch(item["url"])
            m = re.search(r'<div class=["\']popisdetail["\']>(.*?)</div>', html, re.DOTALL)
            if not m:
                m = re.search(r'<div class=["\']popis["\']>(.*?)</div>', html, re.DOTALL)
            if m:
                text = re.sub(r"<[^>]+>", " ", m.group(1))
                return re.sub(r"\s+", " ", text).strip()
        except Exception as e:
            print(f"    detail fail {item['id']}: {e}")
        return ""

    all_items: dict[str, dict] = {}
    for query in queries:
        print(f"  query {query!r}")
        for page in range(20):
            offset = page * 20
            params = urllib.parse.urlencode({
                "hledat": query,
                "hlokalita": "",
                "humkreis": "",
                "cenaod": str(CENA_OD),
                "cenado": str(CENA_DO),
                "order": "",
            })
            prefix = f"/{offset}/" if offset else "/"
            url = f"{base}{prefix}?{params}"
            try:
                batch = parse_list(fetch(url))
            except Exception as e:
                print(f"    page {page+1} error: {e}")
                break
            if not batch:
                break
            new = 0
            for it in batch:
                if it["id"] not in all_items:
                    all_items[it["id"]] = it
                    new += 1
            print(f"    page {page+1}: +{new} (total {len(all_items)})")
            if new == 0:
                break
            time.sleep(0.3)

    def wants_detail(it: dict) -> bool:
        t = f"{it['title']} {it['description']}".lower()
        if any(x in t for x in ("e-bike", "elektro", "dětsk", "detsk", "koloběž")):
            return False
        return any(
            x in t
            for x in (
                "gravel", "endurance", "allroad", "all-road", "grx", "checkpoint",
                "diverge", "topstone", "grizl", "grial", "surplus", "rouleur",
                "domane", "endurace", "roubaix", "synapse", "contend", "defy",
                "karbon", "carbon", "105", "ultegra", "rival",
            )
        )

    items = list(all_items.values())
    targets = [it for it in items if wants_detail(it)]
    print(f"  details {len(targets)}/{len(items)}")
    for i, it in enumerate(targets, 1):
        extra = fetch_detail(it)
        if extra:
            it["description"] = f"{it['description']} {extra}".strip()
        if i % 25 == 0:
            print(f"    {i}/{len(targets)}")
        time.sleep(0.2)
    save("bazos_listings.json", items)


# ── sbazar.cz ───────────────────────────────────────────────────────────────

def scrape_sbazar() -> None:
    print("\n=== sbazar.cz gravel/endurance ===")
    try:
        from image_urls import sbazar_image_from_chunk
    except ImportError:
        def sbazar_image_from_chunk(_chunk: str) -> str | None:
            return None

    base = "https://www.sbazar.cz"
    queries = [
        "gravel", "endurance", "gravel kolo", "allroad", "grx",
        "diverge", "checkpoint", "topstone", "nuroad", "silex",
        "revolt", "devote", "domane", "endurace",
    ]

    def parse_offers(html: str) -> list[dict]:
        text = unescape(html)
        seen: set[str] = set()
        items: list[dict] = []
        for m in re.finditer(r'"id":\[0,(\d+)\]', text):
            chunk = text[m.start() : m.start() + 5000]
            seo_m = re.search(r'"seoName":\[0,"([^"]+)"\]', chunk)
            name_m = re.search(r'"name":\[0,"([^"]+)"\]', chunk)
            price_m = re.search(r'"price":\[0,(\d+)\]', chunk)
            if not (seo_m and name_m and price_m):
                continue
            seo = seo_m.group(1)
            if not re.match(r"\d+-", seo):
                continue
            oid = seo.split("-", 1)[0]
            if oid in seen or not oid.isdigit() or int(oid) < 10_000_000:
                continue
            title = name_m.group(1).strip()
            if len(title) < 8:
                continue
            price = int(price_m.group(1))
            if price < CENA_OD or price > CENA_DO:
                continue
            seen.add(oid)
            city_m = re.search(r'"city":\[0,"([^"]*)"\]', chunk)
            region_m = re.search(r'"region":\[0,"([^"]*)"\]', chunk)
            loc = " ".join(
                x
                for x in [
                    city_m.group(1) if city_m else "",
                    region_m.group(1) if region_m else "",
                ]
                if x
            )
            items.append({
                "id": oid,
                "source": "sbazar.cz",
                "title": title,
                "description": "",
                "price_czk": float(price),
                "price_eur": round(price / CZK_PER_EUR, 0),
                "location": loc,
                "url": f"{base}/inzerat/{seo}",
                "image_url": sbazar_image_from_chunk(chunk),
            })
        return items

    def fetch_detail(item: dict) -> str:
        try:
            html = fetch(item["url"])
            text = unescape(html)
            for m in re.finditer(r'"id":\[0,' + re.escape(item["id"]) + r"\]", text):
                chunk = text[m.start() : m.start() + 12000]
                img = sbazar_image_from_chunk(chunk)
                if img and not item.get("image_url"):
                    item["image_url"] = img
                desc_m = re.search(r'"description":\[0,"((?:\\.|[^"\\])*)"\]', chunk)
                if desc_m:
                    return desc_m.group(1).replace("\\n", " ").replace('\\"', '"')[:2000]
            m = re.search(r'<meta name="description" content="([^"]+)"', html)
            return m.group(1) if m else ""
        except Exception as e:
            print(f"    detail fail {item['id']}: {e}")
        return ""

    all_items: dict[str, dict] = {}
    for q in queries:
        slug = urllib.parse.quote(q)
        for page in range(1, 9):
            params = urllib.parse.urlencode({
                "cena_od": CENA_OD,
                "cena_do": CENA_DO,
                "strana": page,
            })
            url = f"{base}/hledej/{slug}?{params}"
            print(f"  {url}")
            try:
                batch = parse_offers(fetch(url))
            except Exception as e:
                print(f"    fail: {e}")
                break
            print(f"    page {page}: {len(batch)}")
            if not batch:
                break
            for it in batch:
                all_items[it["id"]] = it
            time.sleep(0.4)

    items = list(all_items.values())
    for i, it in enumerate(items, 1):
        print(f"  detail {i}/{len(items)}")
        it["description"] = fetch_detail(it)
        time.sleep(0.25)
    save("sbazar_listings.json", items)


# ── cyklobazar.cz ───────────────────────────────────────────────────────────

def scrape_cyklobazar() -> None:
    print("\n=== cyklobazar.cz gravel ===")
    base = "https://www.cyklobazar.cz"
    categories = ["gravel-bike", "silnicni-kola"]

    def parse_price(block: str) -> float | None:
        m = re.search(r"cb-offer__price[^>]*>\s*([\d\s&nbsp;]+)", block)
        if not m:
            m = re.search(r"([\d\s]{2,})\s*(?:&nbsp;)?\s*(?:<small>)?Kč", block)
        if not m:
            return None
        raw = re.sub(r"[^\d]", "", m.group(1).replace("&nbsp;", " "))
        return float(raw) if raw else None

    def parse_list(html: str) -> list[dict]:
        items: list[dict] = []
        seen: set[str] = set()
        for m in re.finditer(r'<a href="(/inzerat/[^"]+)"[^>]*class="[^"]*cb-offer', html):
            path = m.group(1)
            if path in seen:
                continue
            block = html[m.start() : m.start() + 3500]
            if "cb-offer--compact" in block[:200]:
                continue
            seen.add(path)
            title_m = re.search(r"<h4>\s*([^<]+?)\s*</h4>", block)
            loc_m = re.search(r"cb-offer__location[^>]*>\s*([^<]+)", block)
            img_m = re.search(r'<img src="(/uploads/[^"]+)"', block)
            price = parse_price(block)
            if price is None or price < CENA_OD or price > CENA_DO:
                continue
            slug = path.rsplit("/", 1)[-1]
            oid = path.split("/")[2] if path.count("/") >= 2 else slug
            items.append({
                "id": oid,
                "source": "cyklobazar.cz",
                "title": (title_m.group(1) if title_m else slug).strip(),
                "description": "",
                "price_czk": price,
                "price_eur": round(price / CZK_PER_EUR, 0),
                "location": loc_m.group(1).strip() if loc_m else "",
                "url": base + path,
                "image_url": base + img_m.group(1) if img_m else None,
            })
        return items

    def fetch_detail(item: dict) -> str:
        try:
            html = fetch(item["url"])
            m = re.search(r'<div class="[^"]*popis[^"]*"[^>]*>(.*?)</div>', html, re.DOTALL | re.I)
            if not m:
                m = re.search(r'<meta name="description" content="([^"]+)"', html)
                return re.sub(r"\s+", " ", m.group(1)).strip()[:2000] if m else ""
            text = re.sub(r"<[^>]+>", " ", m.group(1))
            return re.sub(r"\s+", " ", text).strip()[:2000]
        except Exception as e:
            print(f"    detail fail {item['id']}: {e}")
        return ""

    all_items: dict[str, dict] = {}
    for cat in categories:
        for page in range(1, 16):
            params = urllib.parse.urlencode({
                "cena_od": CENA_OD,
                "cena_do": CENA_DO,
                "strana": page,
            })
            url = f"{base}/{cat}?{params}"
            print(f"  {url}")
            try:
                batch = parse_list(fetch(url))
            except Exception as e:
                print(f"    fail: {e}")
                break
            print(f"    page {page}: {len(batch)}")
            if not batch:
                break
            for it in batch:
                all_items[it["id"]] = it
            time.sleep(0.35)

    items = list(all_items.values())
    print(f"  details {len(items)}")
    for i, it in enumerate(items, 1):
        it["description"] = fetch_detail(it)
        if i % 25 == 0:
            print(f"    {i}/{len(items)}")
        time.sleep(0.2)
    save("cyklobazar_listings.json", items)


# ── radbazar.at ─────────────────────────────────────────────────────────────

def scrape_radbazar() -> None:
    print("\n=== radbazar.at Gravelbikes ===")
    base = "https://www.radbazar.at"
    list_urls = [
        f"{base}/categories/fahrrader/gravelbikes",
        f"{base}/categories/fahrrader/crossbikes",
    ]

    def parse_eur(raw: str) -> float | None:
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
            # '9.979' = 9979 (thousands), not 9.979
            raw = raw.replace(".", "")
        try:
            return float(raw)
        except ValueError:
            return None

    def parse_list(html: str) -> list[dict]:
        html = unescape(html)
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
            # Card layout: <img> … title <a> … <p class="font-bold">price</p>
            # Image is BEFORE title; price is AFTER. Mixing the window shifts both.
            before = html[max(0, m.start() - 1200) : m.start()]
            after = html[m.end() : m.end() + 500]
            price_m = re.search(r'<p class="font-bold mt-1">\s*([^<]+?)\s*</p>', after)
            imgs = re.findall(
                r'<img src="(https://www\.radbazar\.at/storage/[^"]+)"', before
            )
            image_url = imgs[-1] if imgs else None
            price = parse_eur(price_m.group(1)) if price_m else None
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

    all_items: dict[str, dict] = {}
    for base_url in list_urls:
        for page in range(1, 10):
            params = urllib.parse.urlencode({
                "price_min": PRICE_EUR_MIN,
                "price_max": PRICE_EUR_MAX,
                "page": page,
            })
            url = f"{base_url}?{params}"
            print(f"  {url}")
            try:
                batch = parse_list(fetch(url))
            except Exception as e:
                print(f"    fail: {e}")
                break
            print(f"    page {page}: {len(batch)}")
            if not batch:
                break
            for it in batch:
                all_items[it["id"]] = it
            time.sleep(0.4)

    def fetch_detail(item: dict) -> str:
        try:
            html = fetch(item["url"])
            # Authoritative photo + price from the listing page.
            # Prefer JSON "price":"1.850,00" — meta product:price:amount is often
            # truncated ("1.85" instead of 1850).
            og = re.search(r'<meta property="og:image" content="([^"]+)"', html)
            if og:
                item["image_url"] = og.group(1)
            for pat in (
                r'"price"\s*:\s*"([\d.,]+)"',
                r'<meta property="product:price:amount" content="([^"]+)"',
                r'<meta property="og:price:amount" content="([^"]+)"',
            ):
                pm = re.search(pat, html)
                if not pm:
                    continue
                live = parse_eur(pm.group(1))
                # Truncated meta like "1.85" for €1850 — only trust if >= 50
                # or European thousands form (1.850 / 1.850,00).
                raw = pm.group(1)
                if live is not None and live < 50 and re.fullmatch(r"\d{1,2}\.\d{2}", raw):
                    live = live * 1000  # "1.85" → 1850
                if live and live >= 50:
                    item["price_eur"] = live
                    break
            # Prefer meta description / JSON-ish blobs for year + groupset
            bits: list[str] = []
            for pat in (
                r'<meta name="description" content="([^"]+)"',
                r'<meta property="og:description" content="([^"]+)"',
                r'"description"\s*:\s*"((?:\\.|[^"\\])*)"',
            ):
                m = re.search(pat, html)
                if m:
                    bits.append(unescape(m.group(1).replace("\\n", " ")))
            text = re.sub(r"<[^>]+>", " ", html)
            # Pull size / year / groupset keywords from nearby body
            for kw in ("Baujahr", "Modelljahr", "Größe", "Groesse", "GRX", "105", "Tiagra", "Carbon", "Jahr"):
                idx = text.find(kw)
                if idx >= 0:
                    bits.append(text[max(0, idx - 40) : idx + 80])
            return re.sub(r"\s+", " ", " ".join(bits)).strip()[:2500]
        except Exception as e:
            print(f"    detail fail {item['id']}: {e}")
        return ""

    items = list(all_items.values())
    print(f"  details {len(items)}")
    for i, it in enumerate(items, 1):
        extra = fetch_detail(it)
        if extra:
            it["description"] = extra
        if i % 10 == 0:
            print(f"    {i}/{len(items)}")
        time.sleep(0.25)
    # Drop out-of-budget after live price correction
    items = [
        it
        for it in items
        if it.get("price_eur") is not None
        and PRICE_EUR_MIN <= it["price_eur"] <= PRICE_EUR_MAX
    ]
    save("radbazar_listings.json", items)


# ── buycycle.com gravel ─────────────────────────────────────────────────────

def scrape_buycycle() -> None:
    print("\n=== buycycle.com gravel ===")
    try:
        from image_urls import buycycle_image_from_blob
    except ImportError:
        def buycycle_image_from_blob(_blob: str, _slug: str) -> str | None:
            return None

    locales = ["en-at", "en-cz", "en-de", "de-at", "de-de"]
    base = "https://www.buycycle.com"

    def human_title(slug: str) -> str:
        slug = re.sub(r"-\d{4,}$", "", slug)
        slug = re.sub(r"-20\d{2}-.*$", "", slug)
        slug = re.sub(r"-gr-[a-z0-9]+-.*$", "", slug, flags=re.I)
        parts = [p for p in slug.split("-") if p and not p.isdigit()]
        return " ".join(parts).title()

    def rsc_blob(html: str) -> str:
        parts = re.findall(r'self\.__next_f\.push\(\[1,"((?:\\.|[^"])*)"\]\)', html)
        blob = ""
        for part in parts:
            try:
                blob += bytes(part, "utf-8").decode("unicode_escape")
            except Exception:
                blob += part
        return blob

    def parse_blob(blob: str, locale: str) -> list[dict]:
        items: list[dict] = []
        for m in re.finditer(r'"slug":"([^"]+)".{0,400}?"price":(\d+)', blob, re.DOTALL):
            slug, price = m.groups()
            price_eur = float(price)
            if not (PRICE_EUR_MIN <= price_eur <= PRICE_EUR_MAX):
                continue
            year_m = re.search(r"(20\d{2})", slug)
            size_hint = ""
            if msize := re.search(r"-gr-([mlxs\d]+)-", slug):
                size_hint = f" size {msize.group(1).upper()}"
            items.append({
                "id": slug,
                "source": f"buycycle.com ({locale})",
                "title": human_title(slug),
                "description": slug + size_hint,
                "price_eur": price_eur,
                "year": int(year_m.group(1)) if year_m else None,
                "location": locale.split("-")[-1].upper(),
                "url": f"{base}/{locale}/product/{slug}",
                "image_url": buycycle_image_from_blob(blob, slug),
            })
        return items

    all_items: dict[str, dict] = {}
    params = urllib.parse.urlencode({"max_price": str(PRICE_EUR_MAX)})
    for locale in locales:
        for bike_type in ("gravel", "race"):
            url = f"{base}/{locale}/shop/main-types/bikes/types/{bike_type}?{params}"
            print(f"  {locale}/{bike_type}...")
            try:
                blob = rsc_blob(fetch(url, headers=BUYCYCLE_HEADERS))
                batch = parse_blob(blob, locale)
                print(f"    {len(batch)}")
                for it in batch:
                    all_items[it["id"]] = it
                time.sleep(0.45)
            except Exception as e:
                print(f"    fail: {e}")
    save("buycycle_listings.json", list(all_items.values()))
    if not all_items:
        print("  (buycycle blocked / empty — skipping; Cloudflare 403 is common)")


def main() -> None:
    import sys

    only = [a for a in sys.argv[1:] if not a.startswith("-")]
    steps = {
        "willhaben": scrape_willhaben,
        "bazos": scrape_bazos,
        "sbazar": scrape_sbazar,
        "cyklobazar": scrape_cyklobazar,
        "radbazar": scrape_radbazar,
        "buycycle": scrape_buycycle,
    }
    if only:
        for name in only:
            if name not in steps:
                print(f"Unknown source {name!r}; choose from {list(steps)}")
                raise SystemExit(2)
            steps[name]()
    else:
        for fn in steps.values():
            fn()
    print("\nDone. Next: python mtb/scripts/build_gravel_women168.py")


if __name__ == "__main__":
    main()
