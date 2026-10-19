"""Build a road-bike search profile for a woman ~168 cm.

Targets:
  - silniční / Rennrad (not MTB, gravel, e-bike)
  - frame size XS/S or ~47–53 cm
  - model year 2021+
  - budget €400–€1600 (≈ 10–40 tis. Kč)
  - prefer carbon frame and/or Shimano 105+ (or SRAM Rival/Force/Red)
  - good condition signals boost score

Re-analyzes data/scrapes/road/*_listings.json (from scrape_road.py). Output:

    data/deals/merged_deals_road168.json
    data/reports/report_road168.html
    data/reports/report_road168.txt

Run:
    python mtb/scripts/scrape_road.py
    python mtb/scripts/build_road_women168.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from analyze_trail import attr_map, full_text, listing_url
from analyze_trail import price_eur as wh_price_eur
from export_report import export as export_report
from filters import czk_to_eur, model_year
from image_urls import willhaben_image
from linkcheck import filter_live, verify_prices
from paths import (
    MERGED_ROAD168,
    REPORT_ROAD168_HTML,
    REPORT_ROAD168_TXT,
    SCRAPE_ROAD,
    ensure_layout,
)
from size_fit_168 import frame_fit_168

OUT_JSON = MERGED_ROAD168
OUT_HTML = REPORT_ROAD168_HTML
OUT_TXT = REPORT_ROAD168_TXT
DATA = SCRAPE_ROAD

MIN_YEAR = 2021
PRICE_EUR_MIN = 400
PRICE_EUR_MAX = 1600  # ≈ 40 000 Kč

AT_SOURCES = {"willhaben.at", "radbazar.at", "radlmarkt.at", "biklo.at"}
CZ_SOURCES = {"bazos.cz", "sbazar.cz", "cyklobazar.cz", "biklo.cz"}

GENERIC_SOURCES = {
    "bazos.cz": DATA / "bazos_listings.json",
    "sbazar.cz": DATA / "sbazar_listings.json",
    "cyklobazar.cz": DATA / "cyklobazar_listings.json",
    "radbazar.at": DATA / "radbazar_listings.json",
    "buycycle.com": DATA / "buycycle_listings.json",
}

# Groupsets at/above 105 (or SRAM Rival equivalent)
GROUP_GOOD = (
    r"(?:\b105\b|ultegra|dura[\s\-]?ace|di2|"
    r"\brival\b|\bforce\b|\bred\b\s*(?:axs|etap)?|"
    r"sram\s+rival|sram\s+force|sram\s+red|"
    r"campagnolo\s+(?:chorus|record|super))"
)
GROUP_LOW = r"(?:\btiagra\b|\bsora\b|\bclaris\b|\btourney\b|\bmicroshift\b|\bapex\b)"


def is_wrong_category(text: str) -> tuple[bool, str]:
    t = text.lower()
    bad = [
        "mountainbike", "mountain bike", " mtb ", "enduro", "trailbike",
        "celoodpruž", "celoodpruz", "fully", "full suspension", "hardtail",
        "e-bike", "e bike", "ebike", "elektro", "pedelec", "bosch motor",
        "gravel", "cyclocross", "cyclo-cross", "crossbike", "cross bike",
        "fatbike", "bmx", "downhill", "freeride",
        "kinder", "kinderrad", "dětsk", "detsk", "junior",
        "koloběž", "kolobez", "skládač", "skladacka", "folding",
        "trekking", "citybike", "city bike", "městské", "mestské",
        "hollandrad", "cruiser", "fixbike",
        "triathlon", "zeitfahr", "tt bike", "time trial",
        "rahmen only", "jen rám", "nur rahmen", "frameset only",
        "laufradsatz", "kola samotná", "wheelset",
    ]
    for kw in bad:
        if kw in t:
            return True, kw.strip()
    # MTB model names without road context
    mtb_models = [
        "stumpjumper", "fuel ex", "spectral", "capra", "slash", "process 1",
        "stereo 1", "jeffsy", "sight", "nomad", "bronson",
    ]
    if any(m in t for m in mtb_models):
        return True, "mtb model"
    return False, ""


def is_road_bike(text: str) -> bool:
    t = text.lower()
    signals = [
        "rennrad", "rennväg", "road bike", "roadbike", "silniční", "silnicni",
        "silničník", "silnicnik", "race bike", "racebike", "aero road",
        "endurance road", "roadrace",
    ]
    models = [
        "tarmac", "aethos", "rouleur", "allez", "domane", "emonda", "madone",
        "tcr ", "defy", "contend", "ultimate cf", "endurace", "aeroad",
        "speedmax", "slr 7", "slr 8", "orbea orca", "orca m", "scott addict",
        "scott foil", "ridley fenix", "ridley helminth", "bianchi infinito",
        "bianchi oltre", "cervelo", "cervélo", "factor oso", "factor one",
        "look 785", "pinarello", "wilier", "colnago", "canyon ultimate",
        "canyon endurace", "canyon aeroad", "cube attain", "cube agree",
        "cube litening", "merida reacto", "merida scultura", "focus izalco",
        "giant propel", "giant tcr", "canyon inflite",  # inflite is CX — filtered elsewhere
        "specialized tarmac", "specialized aethos", "trek emonda", "trek domane",
        "cannondale synapse", "cannondale system", "supersix", "caad",
    ]
    if any(s in t for s in signals) or any(m in t for m in models):
        return True
    # Shimano road groupset + carbon often implies road when in road category scrape
    if re.search(GROUP_GOOD, t) and ("carbon" in t or "karbon" in t or "karbonový" in t):
        return True
    return False


def has_carbon_frame(text: str) -> bool:
    """True only for carbon *frame* — ignore carbon fork / wheels / pedals alone."""
    t = text.lower()
    # Explicit alu frame → not carbon frame (even with carbon fork)
    if re.search(
        r"(?:alu(?:minium)?[\s\-]?rahmen|alu[\s\-]?frame|hlin[ií]kov(?:ý|y)\s*r[aá]m|"
        r"alloy\s*frame|rahmen\s*(?:ist\s*)?(?:aus\s*)?alu|rám\s*(?:je\s*)?hlin)",
        t,
    ):
        return False
    if re.search(
        r"(?:vollcarbon|full\s*carbon|carbonrahmen|carbon[\s\-]?frame|carbon[\s\-]?rahmen|"
        r"karbon(?:ov[ýy])?\s*r[aá]m|ud\s*carbon|cf[\s\-]?(?:slx?|r)\b|"
        r"c:?62|c:?68|tarmac\s*sl|aethos|emonda\s*slr|addict\s*rc|"
        r"carbonfahrrad|carbon[\s\-]?rennrad)",
        t,
    ):
        return True
    # "Carbon" next to Rahmen/frame, but not Gabel/Fork/Laufrad/Pedal
    if re.search(r"carbon.{0,20}(?:rahmen|frame|rám)|(?:rahmen|frame|rám).{0,20}carbon", t):
        if not re.search(r"carbon\s*(?:gabel|fork|laufrad|wheel|felge|pedal)", t):
            return True
    return False


def groupset_tier(text: str) -> str:
    t = text.lower()
    # Avoid bare "red" / "force" false positives — require brand or road context
    if re.search(
        r"(?:\bshimano\s*105\b|\b105\s*(?:di2|r7|r71|r70)|ultegra|dura[\s\-]?ace|"
        r"sram\s+rival|sram\s+force|sram\s+red|rival\s*axs|force\s*axs|red\s*axs|"
        r"campagnolo\s+(?:chorus|record|super))",
        t,
    ):
        return "105+"
    if re.search(GROUP_LOW, t):
        return "entry"
    return "unknown"


def road_year(text: str) -> int | None:
    """Prefer explicit model year; also catch Bj2009 / MY2021 glued forms."""
    y = model_year(text)
    if y:
        return y
    t = text.lower()
    glued = re.findall(
        r"(?:baujahr|bj|modelljahr|model\s*year|modelljahr|my|rok)\s*[:\s]?(20\d{2})",
        t,
    )
    if glued:
        return max(int(x) for x in glued)
    # standalone years in plausible model range
    years = [int(x) for x in re.findall(r"\b(20(?:1[5-9]|2[0-6]))\b", text)]
    if not years:
        return None
    # drop service-like max if multiple
    return max(years)


def condition_bonus(text: str) -> tuple[int, list[str]]:
    t = text.lower()
    score = 0
    notes: list[str] = []
    for kw, pts in [
        ("neuwertig", 3), ("wie neu", 3), ("kaum gefahren", 2), ("wenig gefahren", 2),
        ("málo najeto", 2), ("zachoval", 2), ("perfektní stav", 2), ("perfektni stav", 2),
        ("výborný stav", 2), ("vyborny stav", 2), ("top zustand", 2), ("top zustand", 2),
        ("sehr guter zustand", 2), ("rechnung", 2), ("faktura", 1), ("servisova", 1),
        ("servisová", 1), ("first owner", 1), ("erster besitzer", 1), ("od prvního", 1),
        ("garáž", 1), ("garage", 1), ("nehavarovan", 1),
    ]:
        if kw in t:
            score += pts
            notes.append(kw)
    # wear / damage penalties
    for kw, pts in [
        ("defekt", -2), ("gerissen", -2), ("praskl", -2), ("havar", -3),
        ("crash", -3), ("schaden", -2), ("poškozen", -2), ("poskozen", -2),
        ("ersatzteil", -3), ("na díly", -3), ("na dily", -3),
    ]:
        if kw in t:
            score += pts
            notes.append(kw)
    return score, notes


def score_road(
    text: str,
    price_eur: float | None,
    year: int | None,
    fit_class: str,
    carbon: bool,
    group: str,
) -> tuple[int, list[str]]:
    t = text.lower()
    score = 0
    notes: list[str] = []

    if year:
        if year >= 2024:
            score += 5
            notes.append(f"MY{year}")
        elif year >= 2022:
            score += 4
            notes.append(f"MY{year}")
        elif year >= MIN_YEAR:
            score += 2
            notes.append(f"MY{year}")
    else:
        score -= 1
        notes.append("year?")

    if carbon:
        score += 4
        notes.append("carbon frame")
    if group == "105+":
        score += 4
        notes.append("105+")
    elif group == "entry":
        score -= 2
        notes.append("entry group")

    if carbon or group == "105+":
        score += 2
        notes.append("ideal spec")
    else:
        score -= 3
        notes.append("spec?")

    for kw in ("damen", "frauen", "women", "wsd", "ladies", "dámské", "damske"):
        if kw in t:
            score += 2
            notes.append("women")
            break

    if "vb" in t or "dohodou" in t or "smlouvou" in t or "verhandlungsbasis" in t:
        score += 1
        notes.append("VB")

    if price_eur and price_eur <= 1200:
        score += 2
        notes.append("good price")
    if price_eur and price_eur <= 900:
        score += 2
        notes.append("steal?")

    c_score, c_notes = condition_bonus(text)
    score += c_score
    notes.extend(c_notes[:4])

    if fit_class == "likely_fit":
        score += 3
    elif fit_class == "unlikely":
        score -= 10

    return score, notes


def evaluate(text: str, price_eur: float | None, title: str = "") -> dict | None:
    bad, _ = is_wrong_category(text)
    if bad:
        return None

    # From dedicated road scrapes we still require a road signal OR (carbon+group)
    # so random junk doesn't slip through bazos "silniční" noise.
    if not is_road_bike(text):
        # category scrapes (willhaben/cyklobazar/radbazar) are already road-focused;
        # still require at least a bike-ish title with year or groupset
        if not (
            re.search(r"\b(20(?:2[1-5]))\b", text)
            or re.search(GROUP_GOOD, text.lower())
            or "carbon" in text.lower()
            or "karbon" in text.lower()
        ):
            return None

    if price_eur is not None and (price_eur < PRICE_EUR_MIN or price_eur > PRICE_EUR_MAX):
        return None

    year = road_year(text)
    # Hard requirement: model year 2021+ (user asked for bikes not older than 2021)
    if not year or year < MIN_YEAR:
        return None

    carbon = has_carbon_frame(text)
    group = groupset_tier(text)

    if group == "entry" and not carbon:
        return None
    if not (carbon or group == "105+"):
        return None

    fit_class, fit_label = frame_fit_168(text, title)
    if fit_class == "unlikely":
        return None

    score, notes = score_road(text, price_eur, year, fit_class, carbon, group)
    spec = "carbon" if carbon else ""
    if group == "105+":
        spec = f"{spec}+105+".strip("+") if spec else "105+"
    elif group == "entry":
        spec = f"{spec}+entry".strip("+") if spec else "entry"
    if not spec:
        spec = "spec?"

    return {
        "year": year,
        "travel": spec,  # reuse report field for groupset/material
        "fit": fit_label,
        "fit_class": fit_class,
        "score": score,
        "notes": notes,
        "carbon": carbon,
        "groupset": group,
    }


def from_generic(source: str, path: Path) -> list[dict]:
    if not path.exists():
        return []
    out: list[dict] = []
    for item in json.load(open(path, encoding="utf-8")):
        text = " ".join([
            item.get("title", ""),
            item.get("description", ""),
            item.get("body", ""),
        ])
        if item.get("year"):
            text += f" model {item['year']}"
        price = item.get("price_eur")
        if price is None and item.get("price_czk"):
            price = czk_to_eur(item["price_czk"])
        meta = evaluate(text, price, item.get("title", ""))
        if not meta:
            continue
        out.append({
            "source": item.get("source", source),
            "id": item.get("id"),
            "title": (item.get("title", "") or "")[:120],
            "price_eur": price,
            "price_czk": item.get("price_czk"),
            "location": item.get("location", ""),
            "url": item.get("url", ""),
            "image_url": item.get("image_url"),
            **meta,
        })
    return out


def from_willhaben() -> list[dict]:
    p = DATA / "at_listings.json"
    if not p.exists():
        return []
    out: list[dict] = []
    for item in json.load(open(p, encoding="utf-8")):
        text = full_text(item)
        price = wh_price_eur(item)
        a = attr_map(item.get("attributes", {}))
        title = a.get("HEADING", item.get("description", ""))
        meta = evaluate(text, price, title)
        if not meta:
            continue
        out.append({
            "source": "willhaben.at",
            "id": item.get("id"),
            "title": (title or "")[:120],
            "price_eur": price,
            "location": f"{a.get('POSTCODE', '')} {a.get('LOCATION', '')}, {a.get('STATE', '')}".strip(", "),
            "url": listing_url(item),
            "image_url": willhaben_image(item.get("attributes", {})),
            **meta,
        })
    return out


def source_key(name: str) -> str:
    return (name or "").split(" (")[0]


def main() -> None:
    merged: list[dict] = []
    merged.extend(from_willhaben())
    for src, path in GENERIC_SOURCES.items():
        merged.extend(from_generic(src, path))

    kept: list[dict] = []
    seen: set[str] = set()
    for m in merged:
        url = m.get("url") or ""
        if url and url in seen:
            continue
        fit_ok = m.get("fit_class") == "likely_fit"
        notes_l = " ".join(m.get("notes") or []).lower()
        title_l = (m.get("title") or "").lower()
        women_signal = (
            "women" in notes_l
            or any(
                k in title_l
                for k in (
                    "damen", "frauen", "women", "wsd", "ladies", "dámsk", "damsk",
                    "liv ", "aura", "avail",
                )
            )
        )
        unknown_ok = (
            m.get("fit_class") == "unknown"
            and women_signal
            and m.get("year")
            and m.get("year") >= MIN_YEAR
            and m.get("score", 0) >= 10
            and (m.get("carbon") or m.get("groupset") == "105+")
        )
        if fit_ok or unknown_ok:
            if url:
                seen.add(url)
            kept.append(m)

    if "--no-verify" not in sys.argv:
        print(f"Verifying {len(kept)} links (dropping sold/expired ads)...")
        kept, dropped = filter_live(kept)
        print(f"  dropped {dropped} dead links, {len(kept)} live remain")
        print(f"Verifying listed prices match the live page...")
        kept, price_dropped = verify_prices(kept)
        print(f"  dropped {price_dropped} price mismatches, {len(kept)} remain")

    kept.sort(key=lambda x: (-x.get("score", 0), x.get("price_eur") or 9999))

    by_src: dict[str, int] = {}
    for m in kept:
        sk = source_key(m.get("source", "?"))
        by_src[sk] = by_src.get(sk, 0) + 1

    at_deals = [m for m in kept if source_key(m.get("source", "")) in AT_SOURCES]
    cz_deals = [m for m in kept if source_key(m.get("source", "")) in CZ_SOURCES]

    report = {
        "page_title": "Silniční kolo — žena ~168 cm — report",
        "heading": "Silniční kolo — žena ~168 cm (XS/S, ≈47–53 cm)",
        "subtitle": (
            f"€{PRICE_EUR_MIN:.0f}–€{PRICE_EUR_MAX:.0f} (do ~40 tis. Kč) · "
            f"2021+ · karbon nebo 105+ · XS/S"
        ),
        "fit_label": "XS/S (≈47–53 cm)",
        "price_min_eur": PRICE_EUR_MIN,
        "price_max_eur": PRICE_EUR_MAX,
        "by_source": by_src,
        "pinned": [],
        "top_at": at_deals[:30],
        "top_cz": cz_deals[:20],
        "top_market": [],
        "top": kept[:50],
        "all": kept,
    }
    ensure_layout()
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    html_path, txt_path = export_report(report, html_out=OUT_HTML, txt_out=OUT_TXT)

    print(
        f"Road ~168 cm (XS/S), €{PRICE_EUR_MIN:.0f}-{PRICE_EUR_MAX:.0f}, "
        f"MY{MIN_YEAR}+, carbon|105+"
    )
    print("Counts by source:", by_src)
    print(f"Total kept: {len(kept)}  (AT {len(at_deals)} | CZ {len(cz_deals)})")
    print(f"Saved {OUT_JSON}")
    print(f"Report HTML: {html_path}")
    print(f"Report text: {txt_path}")


if __name__ == "__main__":
    main()
