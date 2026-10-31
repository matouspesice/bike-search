# Hra v lese

> Hostováno pod `bike-search` Pages (`docs/hra-v-lese/`), protože PAT neumí vytvořit/`push` do nového `hra-v-lese` / `AISk8`.

Digitální mapa rodinné mřížkové hry kolem **Heřmanice / Hřídelec / Pustá Proseč / Kumburský Újezd** (u Nové Paky). Trasy z WhatsApp skupiny *Chalupa*.

## Live

**GitHub Pages:** https://matouspesice.github.io/bike-search/hra-v-lese/

## Podklad mapy

- **Teď:** [OpenTopoMap](https://opentopomap.org) (outdoor/topo) — uživatel nemá Mapy.cz API klíč.
- **Preferováno:** turistická vrstva **Mapy.cz / Mapy.com** (`outdoor`) přes [Map Tiles REST API](https://developer.mapy.com/rest-api-mapy-cz/function/map-tiles/).

### Jak zapnout Mapy.cz později

1. Založ projekt a klíč na [developer.mapy.com/account](https://developer.mapy.com/account) (Basic tarif má volné kredity).
2. Buď:
   - zkopíruj `config.example.js` → `config.js` a doplň `mapyApiKey`, **nebo**
   - otevři stránku s `?apikey=TVUJ_KLIC`.
3. Při platném klíči se načte Mapy outdoor; při chybě dlaždic zůstane OpenTopoMap a banner.

`config.js` je v `.gitignore` — klíč necommitovat.

## Mřížka a data

- Sloupce **A–U**, řádky **1–17** (U kvůli Matoušovu **U13**; papír končil u T).
- Georeference podle obcí na papírové mapě (vizuální fit, ne sken).
- 8 hráčů, barvy, pořadí pohybu, legenda, dvojice.

### Dvojice

| Dvojice | Důkaz |
|--------|--------|
| Honza + Lucka | oba K7 @13:12 |
| Martin Kolda + Tereza Vrabcová | oba I8 @13:02 |
| Anežka Pešicová + Matouš Pešice | oba L12 ~13:10 |
| Markéta Vrabcová + Míra Kubíček | zbývající pár (cesty se nepotkaly) |

## Lokálně

Stačí otevřít `index.html` přes libovolný static server, např.:

```bash
python3 -m http.server 8080
```

## Licence podkladu

OpenTopoMap: CC-BY-SA · data OpenStreetMap. Při přepnutí na Mapy.com dodrž attribution dle dokumentace API.
