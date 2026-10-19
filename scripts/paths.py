"""Central data-layout paths for the MTB / road / gravel pipelines.

Layout:
    data/
      reports/              # HTML + TXT reports (what you open)
      deals/                # merged_deals_*.json
      scrapes/
        mtb/                # MTB raw scrapes + per-source *_deals
        road/
        gravel/
      _legacy/              # old probes / wh_* leftovers
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

REPORTS = DATA / "reports"
DEALS = DATA / "deals"
SCRAPES = DATA / "scrapes"
SCRAPE_MTB = SCRAPES / "mtb"
SCRAPE_ROAD = SCRAPES / "road"
SCRAPE_GRAVEL = SCRAPES / "gravel"
LEGACY = DATA / "_legacy"


def ensure_layout() -> None:
    for p in (REPORTS, DEALS, SCRAPE_MTB, SCRAPE_ROAD, SCRAPE_GRAVEL, LEGACY):
        p.mkdir(parents=True, exist_ok=True)


# ── reports ─────────────────────────────────────────────────────────────────

REPORT_MTB183_HTML = REPORTS / "report.html"
REPORT_MTB183_TXT = REPORTS / "report.txt"
REPORT_W175_HTML = REPORTS / "report_women175.html"
REPORT_W175_TXT = REPORTS / "report_women175.txt"
REPORT_ROAD168_HTML = REPORTS / "report_road168.html"
REPORT_ROAD168_TXT = REPORTS / "report_road168.txt"
REPORT_GRAVEL168_HTML = REPORTS / "report_gravel168.html"
REPORT_GRAVEL168_TXT = REPORTS / "report_gravel168.txt"

# ── deals ───────────────────────────────────────────────────────────────────

MERGED_MTB183 = DEALS / "merged_deals.json"
MERGED_W175 = DEALS / "merged_deals_w175.json"
MERGED_ROAD168 = DEALS / "merged_deals_road168.json"
MERGED_GRAVEL168 = DEALS / "merged_deals_gravel168.json"
