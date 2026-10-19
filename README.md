# Bazar kol — deal finder

Skriptový nástroj na hledání bazárových kol (MTB trail/enduro, silniční, gravel/endurance)
z rakouských a českých zdrojů. Výstup jsou HTML reporty s ověřenými odkazy a fotkami.

## Požadavky

- Python 3.10+
- Jen standardní knihovna (žádné `pip install`)
- Spouštěj skripty z `mtb/scripts/` nebo s plnou cestou

## Struktura `data/`

```
data/
  reports/     # HTML + TXT reporty (to otevíráš)
  deals/       # merged_deals_*.json
  scrapes/
    mtb/       # surové MTB scrapy + *_deals
    road/      # silniční scrapy
    gravel/    # gravel / endurance scrapy
  _legacy/     # staré probe / wh_* zbytky
```

## Rychlý start (MTB 183 cm)

```powershell
python mtb/scripts/merge_all.py
start mtb/data/reports/report.html
```

## Kompletní obnovení MTB dat

```powershell
python mtb/scripts/scrape_at.py
python mtb/scripts/analyze_trail.py

python mtb/scripts/scrape_bazos.py
python mtb/scripts/scrape_sbazar.py
python mtb/scripts/scrape_cyklobazar.py
python mtb/scripts/scrape_radbazar.py
python mtb/scripts/scrape_radlmarkt.py
python mtb/scripts/scrape_biklo.py
python mtb/scripts/scrape_buycycle.py
python mtb/scripts/scrape_bikefair.py

python mtb/scripts/analyze_generic.py mtb/data/scrapes/mtb/bazos_listings.json
python mtb/scripts/analyze_generic.py mtb/data/scrapes/mtb/sbazar_listings.json
python mtb/scripts/analyze_generic.py mtb/data/scrapes/mtb/cyklobazar_listings.json
python mtb/scripts/analyze_generic.py mtb/data/scrapes/mtb/radbazar_listings.json
python mtb/scripts/analyze_generic.py mtb/data/scrapes/mtb/radlmarkt_listings.json
python mtb/scripts/analyze_generic.py mtb/data/scrapes/mtb/biklo_listings.json
python mtb/scripts/analyze_generic.py mtb/data/scrapes/mtb/buycycle_listings.json
python mtb/scripts/analyze_generic.py mtb/data/scrapes/mtb/bikefair_listings.json

python mtb/scripts/merge_all.py
```

## Profil: silniční kolo — žena ~168 cm (XS/S)

Rozpočet **do ~40 tis. Kč** (€400–1600), model **2021+**, velikost **XS/S**,
ideálně **karbon** nebo **Shimano 105+** / SRAM Rival+.

```powershell
python mtb/scripts/scrape_road.py
python mtb/scripts/build_road_women168.py
start mtb/data/reports/report_road168.html
```

## Profil: gravel / endurance — žena ~168 cm (XS/S)

Stejné limity jako silniční profil. Typ: **gravel** nebo **endurance**
(Domane, Endurace, Roubaix, Synapse, Checkpoint, Diverge, …), řazení 105+/GRX/Rival+.

```powershell
python mtb/scripts/scrape_gravel.py
python mtb/scripts/build_gravel_women168.py
start mtb/data/reports/report_gravel168.html
```

## Profil: enduro/AM — ~175 cm (S/M)

Používá **stejná MTB data**, jiný filtr velikosti (**S/M**) a zdvih 140–180 mm.

```powershell
python mtb/scripts/build_women175.py
start mtb/data/reports/report_women175.html
```

**Kontrola odkazů:** po analýze se ověří aktivní inzeráty (mrtvé/prodané se smažou).
Přeskočení: `--no-verify`. Logika: `scripts/linkcheck.py` (včetně kontroly ceny u živé stránky).

## Publikace (GitHub Pages)

Veřejný web: **https://matouspesice.github.io/bike-search/**

```powershell
python mtb/scripts/publish_site.py
git add docs && git commit -m "update reports" && git push
```

Pages: větev `main`, složka `/docs`. Raw `data/` je v `.gitignore`.

### Starý odkaz `/mtb-deals/` (redirect)

Po přejmenování repa GitHub **nepřesměruje** project Pages URL
(`…/mtb-deals/` → 404). Repo URL na github.com redirect má, Pages ne.

Obnovení starého odkazu: user site `matouspesice.github.io` se složkou
`mtb-deals/` (meta-refresh + JS). **Nevytvářej** znovu repo `mtb-deals` —
zrušilo by to github.com redirect na `bike-search`.

Cloud Agent GitHub App umí jen `bike-search`, ne `createRepository`. Do
Cloud Environment secrets přidej `GH_TOKEN` (PAT s právem vytvořit repo),
pak v cloudu:

```bash
bash scripts/setup_legacy_pages_redirect.sh
```

Stuby jsou v `redirects/legacy-mtb-deals/`.

## Výstupy

| Soubor | Popis |
|--------|--------|
| `data/reports/report.html` | MTB trail/AM ~183 cm |
| `data/reports/report_women175.html` | MTB enduro/AM ~175 cm |
| `data/reports/report_road168.html` | Silniční ~168 cm |
| `data/reports/report_gravel168.html` | Gravel/endurance ~168 cm |
| `data/deals/merged_deals*.json` | Data pro reporty |
| `data/scrapes/{mtb,road,gravel}/` | Surové scrapy |

Jen přegenerovat report z JSON:

```powershell
python mtb/scripts/export_report.py
```

Cesty jsou centralizované v `scripts/paths.py`.

## Filtry (MTB trail)

- Celoodpružené trail/AM (~150 mm)
- Rok 2019+, velikost M/L
- Bez hardtailů, e-bike, gravel, dětských

## Poznámky

- Inzeráty nekupuj na dálku bez prohlídky.
- API willhaben (`webapi/bff`) vrací 401 — scrape z HTML.
- Starší `wh_*.py` / `_legacy/` jsou z první verze.
