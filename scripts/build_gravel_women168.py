"""Build a gravel / endurance search profile for a woman ~168 cm.

Targets:
  - gravel OR endurance road (Domane, Endurace, Roubaix, Synapse, …)
  - frame size XS/S or ~47–53 cm
  - model year 2021+
  - budget €400–€1600 (≈ 10–40 tis. Kč)
  - prefer carbon frame and/or Shimano 105+/GRX / SRAM Rival+
  - exclude race-aero, MTB fully, e-bike, pure trekking city bikes

Output:
    data/deals/merged_deals_gravel168.json
    data/reports/report_gravel168.html
    data/reports/report_gravel168.txt

Run:
    python mtb/scripts/scrape_gravel.py
    python mtb/scripts/build_gravel_women168.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from analyze_trail import attr_map, full_text, listing_url
from analyze_trail import price_eur as wh_price_eur
from build_road_women168 import (
    condition_bonus,
    groupset_tier,
    has_carbon_frame,
    road_year,
)
from size_fit_168 import frame_fit_168
from export_report import export as export_report
from filters import czk_to_eur
from image_urls import willhaben_image
from linkcheck import filter_live, verify_prices
from paths import (
    DEALS,
    MERGED_GRAVEL168,
    REPORT_GRAVEL168_HTML,
    REPORT_GRAVEL168_TXT,
    SCRAPE_GRAVEL,
    ensure_layout,
)

SHOP_NEW_JSON = DEALS / "new_shop_gravel168.json"

OUT_JSON = MERGED_GRAVEL168
OUT_HTML = REPORT_GRAVEL168_HTML
OUT_TXT = REPORT_GRAVEL168_TXT
DATA = SCRAPE_GRAVEL

MIN_YEAR = 2019  # was 2021 — more stock; older still scored lower
PRICE_EUR_MIN = 400
PRICE_EUR_MAX = 1600
UNKNOWN_SCORE_MIN = 8  # was 10 — keep more size-unknown ads

AT_SOURCES = {"willhaben.at", "radbazar.at", "radlmarkt.at", "biklo.at"}
CZ_SOURCES = {"bazos.cz", "sbazar.cz", "cyklobazar.cz", "biklo.cz"}

GENERIC_SOURCES = {
    "bazos.cz": DATA / "bazos_listings.json",
    "sbazar.cz": DATA / "sbazar_listings.json",
    "cyklobazar.cz": DATA / "cyklobazar_listings.json",
    "radbazar.at": DATA / "radbazar_listings.json",
    "buycycle.com": DATA / "buycycle_listings.json",
}

# GRX is the gravel groupset equivalent of 105+
GROUP_GRAVEL_EXTRA = r"(?:\bgrx\b|shimano\s*grx|sram\s*apex\s*axs)"
GROUP_MID = r"(?:\btiagra\b|\bapex\b|\bsora\b|\bgrx\s*400\b|\bmicroshift\b)"


def carbon_ok(text: str) -> bool:
    """Carbon frame, or loose 'karbon/carbon' in ad (common on CZ bazars)."""
    if has_carbon_frame(text):
        return True
    t = text.lower()
    if re.search(r"\b(?:alu(?:minium)?|hlin[ií]k|alloy)\b", t) and not re.search(
        r"\b(?:karbon(?:ov[ýy])?\s*r[aá]m|carbon\s*frame|carbonrahmen)\b", t
    ):
        return False
    if re.search(r"\b(?:karbon|carbon)\b", t):
        if re.search(r"(?:karbon|carbon)\s*(?:kola|zaplet|wheel|laufrad|gabel|vidlic|fork)", t):
            return False
        return True
    return False


def is_wrong_category(text: str) -> tuple[bool, str]:
    t = text.lower()
    bad = [
        "mountainbike", "mountain bike", " mtb ", "enduro", "trailbike",
        "celoodpruž", "celoodpruz", "fully", "full suspension", "hardtail",
        "e-bike", "e bike", "ebike", "elektro", "pedelec", "bosch motor",
        "fatbike", "bmx", "downhill", "freeride",
        "kinder", "kinderrad", "dětsk", "detsk", "junior",
        "koloběž", "kolobez", "skládač", "skladacka", "folding",
        "citybike", "city bike", "městské", "mestské", "hollandrad", "cruiser",
        "triathlon", "zeitfahr", "tt bike", "time trial",
        "rahmen only", "jen rám", "nur rahmen", "frameset only", "frameset",
        "rámová sada", "ramova sada", "rámova sada", "rahmenset", "frame set",
        "laufradsatz", "wheelset",
        # fishing / non-bike noise from bazos
        "kaprář", "kaprař", "prut ", "pruty", "feeder", "rybář", "rybar",
        # aggressive race aero (not endurance)
        "aeroad", "madone", "propel", "foil ", "systemsix", "supersix evo",
        "tarmac", "aethos", "emonda slr", "allez sprint", "venge",
    ]
    for kw in bad:
        if kw in t:
            return True, kw.strip()
    mtb_models = [
        "stumpjumper", "fuel ex", "spectral", "capra", "slash", "process 1",
        "stereo 1", "jeffsy", "sight", "nomad", "bronson",
    ]
    if any(m in t for m in mtb_models):
        return True, "mtb model"
    return False, ""


def is_gravel_or_endurance(text: str) -> bool:
    t = text.lower()
    signals = [
        "gravel", "gravelbike", "gravel bike", "allroad", "all-road", "all road",
        "endurance", "ausdauer", "gran fondo", "sportive",
        "cyclocross", "cyclo-cross", "crossbike", "cx bike",
    ]
    models = [
        "diverge", "crux", "checkpoint", "domane", "Boone", "boone",
        "roubaix", "sequoia", "synapse", "topstone", "superx",
        "endurace", "grizl", "grial", "grail", "inflite", "allroad",
        "contend", "defy", "revolt", "devote",  # devote = Liv gravel
        "nuroad", "attain", "silex", "gestalt", "aspero", "áspero",
        "scultura endur", "reacto endur", "fairfax", "larkspur",
        "addict gravel", "speedster gravel", "crater lake",
        "mallet", "midnight", "surplus", "straggler", "cross check",
        "open up", "open u.p", "santa cruz stigmata", "ritchey outback",
        "canyon grail", "canyon grizl", "specialized diverge",
        "trek checkpoint", "trek domane", "cannondale topstone",
        "giant revolt", "liv devote", "cube nuroad", "focus atlas",
        "orbea terra", "bianchi infinito", "bianchi Impulso", "impulso",
        "felt breed", "ridley kanzo", "kanzo", "whyte tourus", "tourus",
        "triban", "rc 520", "gravel 2", "grinder",
    ]
    if any(s in t for s in signals):
        return True
    if any(m.lower() in t for m in models):
        return True
    if re.search(GROUP_GRAVEL_EXTRA, t):
        return True
    return False


def groupset_tier_gravel(text: str) -> str:
    t = text.lower()
    if re.search(GROUP_GRAVEL_EXTRA, t):
        return "105+"
    # Bare "105" is common in CZ/AT ads (groupset_tier is stricter).
    if re.search(r"\b105\b|\bultegra\b|\bdura[\s\-]?ace\b|\brival\b|\bforce\b", t):
        return "105+"
    base = groupset_tier(text)
    if base == "105+":
        return "105+"
    if re.search(GROUP_MID, t):
        return "mid"
    return base


def score_gravel(
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
        notes.append("105+/GRX")
    elif group == "mid":
        score += 1
        notes.append("mid group")
    elif group == "entry":
        score -= 2
        notes.append("entry group")

    if carbon or group == "105+":
        score += 2
        notes.append("ideal spec")
    elif group == "mid":
        notes.append("ok spec")
    else:
        score -= 2
        notes.append("spec?")

    if "gravel" in t or "grx" in t:
        score += 2
        notes.append("gravel")
    elif "endurance" in t or any(
        m in t for m in ("domane", "endurace", "roubaix", "synapse", "defy", "contend")
    ):
        score += 2
        notes.append("endurance")

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

    if not is_gravel_or_endurance(text):
        return None

    # Pure trekking without gravel/endurance signal already fails above;
    # also drop obvious touring bags-only city trekking
    t = text.lower()
    if "trekking" in t and "gravel" not in t and "endurance" not in t and "grx" not in t:
        if not any(m in t for m in ("domane", "endurace", "roubaix", "synapse", "checkpoint", "diverge")):
            return None

    if price_eur is not None and (price_eur < PRICE_EUR_MIN or price_eur > PRICE_EUR_MAX):
        return None

    year = road_year(text)
    # Soft year: keep ads without year (common on CZ bazars); reject only clearly old.
    if year is not None and year < MIN_YEAR:
        return None

    carbon = carbon_ok(text)
    group = groupset_tier_gravel(text)

    if group == "entry" and not carbon:
        return None
    # Accept: carbon, 105+/GRX, or mid (Tiagra/Apex/Sora) — not bare unknown alu.
    if not (carbon or group in ("105+", "mid")):
        return None

    fit_class, fit_label = frame_fit_168(text, title)
    if fit_class == "unlikely":
        return None

    score, notes = score_gravel(text, price_eur, year, fit_class, carbon, group)
    spec = "carbon" if carbon else ""
    if group == "105+":
        spec = f"{spec}+105+".strip("+") if spec else "105+"
    elif group == "mid":
        spec = f"{spec}+mid".strip("+") if spec else "mid"
    elif group == "entry":
        spec = f"{spec}+entry".strip("+") if spec else "entry"
    if not spec:
        spec = "spec?"

    kind = "gravel" if ("gravel" in t or "grx" in t) else "endurance"

    return {
        "year": year,
        "travel": f"{kind}|{spec}",
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
        year = m.get("year")
        # Unknown size only if clear women's / small-rider signal — most "unknown"
        # ads are actually M/L frames without a size in the title.
        notes_l = " ".join(m.get("notes") or []).lower()
        title_l = (m.get("title") or "").lower()
        women_signal = (
            "women" in notes_l
            or any(
                k in title_l
                for k in (
                    "damen", "frauen", "women", "wsd", "ladies", "dámsk", "damsk",
                    "liv ", "devote", "aura", "avail",
                )
            )
        )
        unknown_ok = (
            m.get("fit_class") == "unknown"
            and women_signal
            and (year is None or year >= MIN_YEAR)
            and m.get("score", 0) >= UNKNOWN_SCORE_MIN
            and (m.get("carbon") or m.get("groupset") in ("105+", "mid"))
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

    shop_new: list[dict] = []
    if SHOP_NEW_JSON.exists():
        raw = json.load(open(SHOP_NEW_JSON, encoding="utf-8"))
        shop_new = list(raw.get("items") or [])
        shop_new.sort(key=lambda x: (bool(x.get("over_budget")), x.get("price_czk") or 999999))

    report = {
        "page_title": "Gravel / Endurance — žena ~168 cm — report",
        "heading": "Gravel / Endurance — žena ~168 cm (XS/S, ≈47–53 cm)",
        "subtitle": (
            f"bazar €{PRICE_EUR_MIN:.0f}–€{PRICE_EUR_MAX:.0f} · nová do ~50 tis. Kč · "
            f"velikost dle značky · sytější barvy v záložce Nová"
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
        "shop_new": shop_new,
    }
    ensure_layout()
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    html_path, txt_path = export_report(report, html_out=OUT_HTML, txt_out=OUT_TXT)

    print(
        f"Gravel/endurance ~168 cm (XS/S), €{PRICE_EUR_MIN:.0f}-{PRICE_EUR_MAX:.0f}, "
        f"MY{MIN_YEAR}+ or year?, carbon|105+/GRX|mid"
    )
    print("Counts by source:", by_src)
    print(f"Total kept: {len(kept)}  (AT {len(at_deals)} | CZ {len(cz_deals)})")
    print(f"Saved {OUT_JSON}")
    print(f"Report HTML: {html_path}")
    print(f"Report text: {txt_path}")


if __name__ == "__main__":
    main()
