"""Verify that listing URLs still point to a live ad and drop dead ones.

Marketplaces (esp. willhaben) return HTTP 200 for expired ads but redirect to a
generic category page, so we inspect the final URL + page title, not just status.
"""
from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from urllib.request import Request, urlopen

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

# Titles served when a willhaben ad is gone (redirect to the category page).
CATEGORY_TITLES = (
    "mountainbikes - fahrräder",
    "rennräder - fahrräder",
    "trekkingfahrräder / crossbikes - fahrräder",
    "fahrräder & zubehör",
)
DEAD_MARKERS = (
    "nicht mehr verf", "wurde nicht gefunden", "objekt wurde nicht",
    "anzeige wurde deaktiviert", "existiert nicht", "wurde beendet",
    "inzerát nebyl nalezen", "nabídka byla smazána", "inzerát byl smazán",
    "stránka nenalezena", "404", "prodáno", "prodano", "rezervováno", "rezervovano",
)


# willhaben marks the status deep in the embedded __NEXT_DATA__ JSON, well past
# the first 60 kB, so we read enough of the page to reach it.
READ_BYTES = 400_000

# Sold / reserved signals from willhaben's embedded ad JSON + rendered header.
WH_SOLD_MARKERS = (
    '"availability":"soldout"',
    '"advertstatus":{"id":"sold"',
    '"id":"sold","description":"verkauft"',
    '"deletereason":"sold',
    "adstatus=120",
    "(verkauft)",
    '"advertstatus":{"id":"reserved"',
    "(reserviert)",
)


def _fetch(url: str) -> tuple[int, str, str]:
    req = Request(url, headers={"User-Agent": UA, "Accept": "text/html"})
    try:
        with urlopen(req, timeout=15) as r:
            body = r.read(READ_BYTES).decode("utf-8", "ignore").lower()
            return r.status, r.geturl(), body
    except Exception as e:  # noqa: BLE001
        return int(getattr(e, "code", 0) or -1), url, ""


def _title(body: str) -> str:
    m = re.search(r"<title[^>]*>(.*?)</title>", body, re.S)
    return m.group(1).strip() if m else ""


def is_live(url: str) -> bool:
    if not url:
        return False
    code, final, body = _fetch(url)
    if code in (404, 410) or code < 0:
        return False
    title = _title(body)

    if "willhaben.at" in url:
        # Gone ads serve the category page (title "Mountainbikes - Fahrräder ...")
        # at the same URL, so the title is the reliable signal.
        if any(k in title for k in CATEGORY_TITLES):
            return False
        # Sold/reserved ads keep their own page; status lives in the embedded JSON.
        if any(s in body for s in WH_SOLD_MARKERS):
            return False
        m = re.search(r"-(\d{6,})/?$", url) or re.search(r"/(\d{6,})/?$", url)
        ad_id = m.group(1) if m else None
        if ad_id and ad_id not in final:
            return False
        return True

    if any(k in title for k in DEAD_MARKERS):
        return False
    return True


def filter_live(entries: list[dict], workers: int = 16) -> tuple[list[dict], int]:
    urls = [e.get("url") or "" for e in entries]
    with ThreadPoolExecutor(max_workers=workers) as ex:
        flags = list(ex.map(is_live, urls))
    live = [e for e, ok in zip(entries, flags) if ok]
    return live, len(entries) - len(live)


def _parse_displayed_eur(raw: str) -> float | None:
    """AT/DE display prices: '9.979', '1.490 €', '1.234,50'."""
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


def extract_page_price_eur(url: str, body: str) -> float | None:
    """Best-effort price from a live listing page (radbazar / willhaben / bazos)."""
    # JSON / microdata first — prefer explicit quoted European prices ("1.850,00")
    # before truncated meta amounts ("1.85").
    for pat in (
        r'"price"\s*:\s*"([\d.,]+)"',
        r'itemprop="price"\s+content="([\d.,]+)"',
        r'"PRICE/AMOUNT"\s*:\s*\[\s*"([\d.,]+)"',
        r'property="product:price:amount"\s+content="([^"]+)"',
        r'"amount"\s*:\s*"?([\d.,]+)"?',
    ):
        m = re.search(pat, body, re.I)
        if m:
            raw = m.group(1)
            val = _parse_displayed_eur(raw)
            # Radbazar meta sometimes truncates 1850 → "1.85"
            if val is not None and val < 50 and re.fullmatch(r"\d{1,2}\.\d{2}", raw.strip()):
                val = val * 1000
            if val and val >= 50:
                return val

    if "radbazar.at" in url:
        # JSON price is reliable ("1.850,00"); meta amount is often truncated ("1.85").
        m = re.search(r'"price"\s*:\s*"([\d.,]+)"', body)
        if m:
            val = _parse_displayed_eur(m.group(1))
            if val and val >= 50:
                return val
        m = re.search(
            r'<meta property="product:price:amount" content="([^"]+)"',
            body,
            re.I,
        )
        if m:
            raw = m.group(1)
            val = _parse_displayed_eur(raw)
            if val is not None and val < 50 and re.fullmatch(r"\d{1,2}\.\d{2}", raw):
                val = val * 1000
            if val and val >= 50:
                return val
        m = re.search(
            r'(?:class="[^"]*font-bold[^"]*"[^>]*>)\s*([\d.,]+)\s*€',
            body,
            re.I,
        )
        if m:
            val = _parse_displayed_eur(m.group(1))
            if val and val >= 50:
                return val

    if "willhaben.at" in url:
        m = re.search(r'"PRICE/AMOUNT"[^]]*?"([\d.]+)"', body)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                pass

    if "bazos.cz" in url or "sbazar.cz" in url or "cyklobazar.cz" in url:
        m = re.search(r"([\d\s]{3,})\s*(?:&nbsp;)?\s*K[cč]", body, re.I)
        if m:
            digits = re.sub(r"[^\d]", "", m.group(1))
            if digits:
                return int(digits) / 25.0  # rough CZK→EUR
    return None


def price_matches(entry: dict, tolerance: float = 0.25) -> bool:
    """True if scraped price is within ±tolerance of the live page price.

    Skips check when the page price can't be read (don't drop on parse failure).
    """
    url = entry.get("url") or ""
    listed = entry.get("price_eur")
    if not url or listed is None:
        return True
    code, _final, body = _fetch(url)
    if code < 0 or not body:
        return True
    page = extract_page_price_eur(url, body)
    if page is None:
        return True
    # European JSON sometimes stores 9.979 meaning 9979 — already handled in parser,
    # but guard tiny misreads of expensive bikes as < €50.
    if page < 50:
        return True
    lo = listed * (1 - tolerance)
    hi = listed * (1 + tolerance)
    # Also allow absolute €80 slack for rounding / VB
    if abs(page - listed) <= 80:
        return True
    return lo <= page <= hi


def verify_prices(entries: list[dict], workers: int = 8) -> tuple[list[dict], int]:
    """Drop ads where the live page price is wildly different from the scrape."""
    with ThreadPoolExecutor(max_workers=workers) as ex:
        flags = list(ex.map(price_matches, entries))
    ok = [e for e, good in zip(entries, flags) if good]
    return ok, len(entries) - len(ok)
