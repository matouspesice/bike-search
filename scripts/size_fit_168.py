"""Frame-size fit for a rider ~168 cm (woman, road/gravel/endurance).

Uses brand-published height bands where known. Prefer the *smaller* size at
a boundary (sportier / safer for ~168 cm).

Returns: (fit_class, fit_label)
  fit_class: likely_fit | unlikely | unknown
  fit_label: short display string (XS / S / 52 / …)
"""
from __future__ import annotations

import re

# Target rider height (cm). Bands below are inclusive.
TARGET_CM = 168

# Generic road/gravel cm seat-tube → letter (fallback when brand unknown).
# For 168 cm we treat ≥54 as too big (Specialized/Trek 54 starts ~170).
def _generic_letter_from_cm(cm: int) -> str | None:
    if cm < 44 or cm > 62:
        return None
    if cm <= 46:
        return "xs"
    if cm <= 53:
        return "s"
    if cm <= 55:
        return "m"
    if cm <= 58:
        return "l"
    return "xl"


# Brand → which letter sizes fit ~168 cm (from brand charts / common geometry).
# "borderline" letters score as likely_fit but labeled with a note.
BRAND_LETTERS_OK: dict[str, set[str]] = {
    # Canyon Endurace/Grail/Grizl: XS ≈166–172, S ≈172–178 → at 168 prefer XS, S ok
    "canyon": {"2xs", "xs", "s"},
    # Specialized uses numbers primarily; letters rare
    "specialized": {"xs", "s"},
    "trek": {"xs", "s"},
    "cannondale": {"xs", "s"},
    "giant": {"xs", "s"},
    "liv": {"xs", "s"},  # women-specific Giant
    "cube": {"xs", "s"},
    "merida": {"xs", "s"},
    "scott": {"xs", "s"},
    "orbea": {"xs", "s"},
    "focus": {"xs", "s"},
    "bianchi": {"xs", "s"},
    "bmc": {"xs", "s"},
    "ktm": {"xs", "s"},
    "ridley": {"xs", "s"},
    "felt": {"xs", "s"},
    "bulls": {"xs", "s"},
    "bergamont": {"xs", "s"},
    "ctm": {"xs", "s"},
    "author": {"xs", "s"},
    "superior": {"xs", "s"},
    "triban": {"xs", "s"},  # Decathlon
    "van rysel": {"xs", "s"},
    "decathlon": {"xs", "s"},
    "simplon": {"xs", "s"},
    "guerciotti": {"xs", "s"},
    "colnago": {"xs", "s"},
    "fuji": {"xs", "s"},
    "kelly": {"xs", "s"},
    "kellys": {"xs", "s"},
    "rose": {"xs", "s"},
    "radon": {"xs", "s"},
    "stevens": {"xs", "s"},
    "whyte": {"xs", "s"},
    "marin": {"xs", "s"},
}

# Brand → cm sizes that fit ~168 cm (inclusive). Anything larger → reject.
BRAND_CM_OK: dict[str, tuple[int, int]] = {
    # (min_cm, max_cm) suitable for ~168 cm
    "canyon": (44, 53),  # Canyon mostly letter-sized; cm rare
    "specialized": (49, 52),  # 52 = 163–170; 54 = 170–178 → reject
    "trek": (47, 52),  # Domane/Checkpoint: 52 or 54 at 168 → prefer ≤52
    "cannondale": (48, 51),  # Synapse/Topstone 51 ≈ S
    "giant": (44, 53),
    "liv": (44, 53),
    "cube": (47, 53),  # 53 OK borderline; 56+ too big
    "merida": (47, 52),
    "scott": (47, 52),
    "orbea": (47, 53),
    "focus": (47, 53),
    "bianchi": (47, 53),
    "bmc": (47, 51),
    "ktm": (46, 53),
    "ridley": (47, 53),
    "felt": (47, 53),
    "bulls": (47, 53),
    "bergamont": (47, 53),
    "default": (47, 53),
}

BRAND_ALIASES: list[tuple[str, str]] = [
    (r"\bcanyon\b", "canyon"),
    (r"\bspecialized\b|\bs-works\b|\ballez\b|\bdiverge\b|\broubaix\b|\btarmac\b|\bcrux\b", "specialized"),
    (r"\btrek\b|\bdomane\b|\bcheckpoint\b|\bemonda\b", "trek"),
    (r"\bcannondale\b|\bsynapse\b|\btopstone\b|\bsuperx\b", "cannondale"),
    (r"\bliv\b|\bdevote\b", "liv"),
    (r"\bgiant\b|\brevolt\b|\bcontend\b|\bdefy\b|\btcx\b", "giant"),
    (r"\bcube\b|\bnuroad\b|\battain\b|\bcross\s*race\b", "cube"),
    (r"\bmerida\b|\bsilex\b|\bscultura\b", "merida"),
    (r"\bscott\b|\baddict\b|\bspeedster\b", "scott"),
    (r"\borbea\b|\bterra\b|\bavant\b", "orbea"),
    (r"\bfocus\b|\batlas\b", "focus"),
    (r"\bbianchi\b|\binfinito\b|\bimpulso\b", "bianchi"),
    (r"\bbmc\b|\burs\b|\bkaius\b", "bmc"),
    (r"\bktm\b|\bx[\s\-]?strada\b|\bgravelator\b", "ktm"),
    (r"\bridley\b|\bkanzo\b", "ridley"),
    (r"\bfelt\b", "felt"),
    (r"\bbulls\b|\bgrinder\b", "bulls"),
    (r"\bbergamont\b|\bgrandurance\b", "bergamont"),
    (r"\bctm\b|\bkoyuk\b", "ctm"),
    (r"\bauthor\b", "author"),
    (r"\bsuperior\b", "superior"),
    (r"\btriban\b", "triban"),
    (r"\bvan\s*rysel\b|\brcx\b", "van rysel"),
    (r"\bdecathlon\b", "decathlon"),
    (r"\bsimplon\b", "simplon"),
    (r"\bguerciotti\b", "guerciotti"),
    (r"\bcolnago\b", "colnago"),
    (r"\bfuji\b|\broubaix\b", "fuji"),
    (r"\bkellys?\b", "kellys"),
    (r"\brose\b", "rose"),
    (r"\bradon\b", "radon"),
    (r"\bstevens\b", "stevens"),
    (r"\bwhyte\b|\btourus\b", "whyte"),
    (r"\bmarin\b", "marin"),
]

_SIZE_LABEL = (
    r"(?:rahmengr[öo]ße|rahmengroesse|rahmenh[öo]he|gr[öo]ße|groesse|gr\.|"
    r"\bsize\b|\bvelikost\b|\bvel\.|\brh\b|\brám\b|\brahmen\b|"
    r"\bframe\s*size\b|\bframesize\b|veľkosť|velkost)"
)


def detect_brand(text: str) -> str | None:
    t = text.lower()
    for pat, brand in BRAND_ALIASES:
        if re.search(pat, t):
            return brand
    return None


def _extract_cm(text: str) -> list[int]:
    t = text.lower()
    # Strip shoe / clothing size noise
    t = re.sub(
        r"(?:rad(?:fahr)?schuh|schuh|shoe|boty|tretry|helmet|helm|trikot|jersey)"
        r".{0,25}?(?:gr\.?|größe|size|vel\.?)?\s*\d{2}",
        " ",
        t,
    )
    cms: list[int] = []
    for m in re.finditer(_SIZE_LABEL + r"\s*[:=\-]?\s*(\d{2})\s*(?:cm)?\b", t):
        cms.append(int(m.group(1)))
    for m in re.finditer(r"\b(4[4-9]|5[0-9]|6[0-2])\s*cm\b", t):
        cms.append(int(m.group(1)))
    for m in re.finditer(r"\brh\s*[:=]?\s*(\d{2})\b", t):
        cms.append(int(m.group(1)))
    for m in re.finditer(r"\b(4[7-9]|5[0-3])er\b", t):
        cms.append(int(m.group(1)))
    for m in re.finditer(r"(?:velikost|veľkosť|velkost|vel\.)\s*[:=]?\s*(\d{2})\b", t):
        cms.append(int(m.group(1)))
    return [c for c in cms if 44 <= c <= 62]


def _extract_letters(text: str, title_only: bool = False) -> set[str]:
    s = text.lower()
    out: set[str] = set()
    for m in re.finditer(
        _SIZE_LABEL + r"\s*[:=\-]?\s*(xxl|xl|xs|s|m|l)\s*[/–\-]\s*(xxl|xl|xs|s|m|l)\b",
        s,
    ):
        out.add(m.group(1))
        out.add(m.group(2))
    for m in re.finditer(_SIZE_LABEL + r"\s*[:=\-]?\s*(xxl|xl|xs|2xs|xxs|s|m|l)\b", s):
        g = m.group(1)
        out.add("xs" if g in ("2xs", "xxs") else g)
    for m in re.finditer(r"[-_/]gr[-_]?(xs|s|m|l|xl|2xs)\b", s):
        g = m.group(1)
        out.add("xs" if g == "2xs" else g)
    if re.search(r"\b(?:extra[\s\-]?small|x[\s\-]?small|xxs|2xs)\b", s):
        out.add("xs")
    elif re.search(r"\bsmall\b", s):
        out.add("s")
    if re.search(r"\bmedium\b", s):
        out.add("m")
    if re.search(r"\b(?:extra[\s\-]?large|x[\s\-]?large)\b", s):
        out.add("xl")
    elif re.search(r"\blarge\b", s):
        out.add("l")

    # Title-only: letter sizes at token boundaries (avoid "silex" → xs)
    tl = s if title_only else ""
    if title_only:
        tl = s.strip()
        mt = re.search(r"(?:^|[\s\-/(])(xxl|xl|xs|2xs|xxs|[sml])\)?\s*$", tl)
        if mt:
            g = mt.group(1)
            out.add("xs" if g in ("2xs", "xxs") else ("xl" if g == "xxl" else g))
        for m in re.finditer(
            r"(?:^|[\s|/,;(\-])(xxl|xl|xs|2xs|xxs|[sml])(?=[\s|/,;)\-]|$)", tl
        ):
            g = m.group(1)
            out.add("xs" if g in ("2xs", "xxs") else ("xl" if g == "xxl" else g))
        # "M-2024" / "Gr. S" / "(Black) M"
        for m in re.finditer(r"(?:^|[\s(\-])([sml]|xs|xl)(?=[\s)\-/,]|$)", tl):
            out.add(m.group(1))
        mt4 = re.search(r"\b(4[4-9]|5[0-9]|6[0-2])\s*$", tl)
        if mt4:
            letter = _generic_letter_from_cm(int(mt4.group(1)))
            if letter:
                out.add(letter)
        # Rider-height ranges that are clearly too tall
        if re.search(r"(?:1[7-9]\d|18[0-9])\s*(?:–|-|až|bis)?\s*1[89]\d\s*cm", tl):
            out.add("xl")
        # Explicit height bands in title: "165-175 cm" → ok if overlaps 168
        for m in re.finditer(
            r"(\d{3})\s*(?:–|-|až|bis|/)\s*(\d{3})\s*cm", tl
        ):
            lo, hi = int(m.group(1)), int(m.group(2))
            if hi < 165 or lo > 172:
                if lo >= 175:
                    out.add("xl")
                elif lo >= 170:
                    out.add("m")

    return {"xl" if x == "xxl" else x for x in out}


def _cm_fits_brand(brand: str | None, cm: int) -> bool:
    lo, hi = BRAND_CM_OK.get(brand or "", BRAND_CM_OK["default"])
    return lo <= cm <= hi


def _letter_fits_brand(brand: str | None, letter: str) -> bool:
    ok = BRAND_LETTERS_OK.get(brand or "", {"xs", "s"})
    return letter in ok


def frame_fit_168(text: str, title: str = "") -> tuple[str, str]:
    """Fit for ~168 cm → brand-aware XS/S / ~47–53 cm only."""
    brand = detect_brand(f"{title} {text}")
    title_letters = _extract_letters(title, title_only=True)
    body_letters = _extract_letters(text, title_only=False)
    title_cms = _extract_cm(title)
    body_cms = _extract_cm(text)

    # Title wins on conflicts (ads often say "M" in title + junk in body).
    letters = set(title_letters) if title_letters else set(body_letters)
    if title_letters and body_letters:
        if title_letters & {"m", "l", "xl"}:
            letters = set(title_letters)
        else:
            letters = set(title_letters) | (body_letters & {"xs", "s"})

    cms = title_cms or body_cms
    if title_cms and body_cms:
        cms = title_cms

    # Explicit M/L/XL in the *title* always wins — don't let body "RH 53" rescue it.
    title_big = title_letters & {"l", "xl"}
    title_mid = title_letters & {"m"}
    if title_big:
        return "unlikely", "XL" if "xl" in title_big else "L (moc velké)"
    if title_mid and not (title_letters & {"xs", "s", "2xs"}):
        return "unlikely", "M (spíš velké pro 168 cm)"

    # Height hints in full text (e.g. "pro postavu 180 cm")
    full = f"{title} {text}".lower()
    if re.search(
        r"(?:pro\s+)?(?:postavu|výšku|vysku|fahrer|rider|körpergröße|koerpergrosse)"
        r".{0,20}?(?:1[7-9]\d|18\d)\s*cm",
        full,
    ):
        m = re.search(r"(1[7-9]\d|18\d)\s*cm", full)
        if m and int(m.group(1)) >= 175:
            return "unlikely", f"{m.group(1)} cm (moc vysoké)"

    # Numeric cm decision (brand-aware)
    if cms:
        cm = max(cms)
        if not _cm_fits_brand(brand, cm):
            return "unlikely", f"{cm} cm (moc velké pro 168 cm)"
        return "likely_fit", str(cm)

    # Letter decision (body + title)
    big = letters & {"l", "xl"}
    mid = letters & {"m"}
    good = letters & {"xs", "s", "2xs"}
    if "2xs" in letters:
        good.add("xs")

    if big:
        return "unlikely", "XL" if "xl" in big else "L (moc velké)"
    if mid and not good:
        return "unlikely", "M (spíš velké pro 168 cm)"
    if good:
        primary = "S" if "s" in good else "XS"
        letter_key = "s" if primary == "S" else "xs"
        if brand and not _letter_fits_brand(brand, letter_key):
            return "unlikely", f"{primary} ({brand}: spíš velké)"
        return "likely_fit", primary

    return "unknown", "?"
