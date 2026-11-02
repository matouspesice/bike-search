# Hra v lese

> Hostováno pod `bike-search` Pages (`docs/hra-v-lese/`), protože PAT neumí vytvořit/`push` do nového `hra-v-lese` / `AISk8`.

Digitální mapa rodinné mřížkové hry kolem **Heřmanice / Hřídelec / Pustá Proseč / Kumburský Újezd** (u Nové Paky). Trasy z WhatsApp skupiny *Chalupa*.

## Live

**GitHub Pages:** https://matouspesice.github.io/bike-search/hra-v-lese/

## Podklad mapy

- **Live:** turistická vrstva **Mapy.cz / Mapy.com** (`outdoor`) přes [Map Tiles REST API](https://developer.mapy.com/rest-api-mapy-cz/function/map-tiles/) — klíč v commitnutém `config.js` (veřejný Pages, rodinná mapa).
- **Fallback:** [OpenTopoMap](https://opentopomap.org), pokud Mapy dlaždice selžou.

### Klíč / lokální override

1. Klíč spravuj na [developer.mapy.com/account](https://developer.mapy.com/account).
2. Live Pages čte `config.js` (`preferMapy: true`). Pro jednorázový override: `?apikey=…`.
3. Šablona bez klíče: `config.example.js`. Při chybě dlaždic zůstane OpenTopoMap (UI banner jen při selhání dlaždic / Leaflet).

## Mřížka a data

- Sloupce **A–U**, řádky **1–17** (U kvůli Matoušovu **U13**; papír končil u T).
- Georeference podle obcí na papírové mapě (vizuální fit, ne sken).
- 8 hráčů, barvy, pořadí pohybu, legenda, dvojice.

### Dvojice

| Dvojice | Důkaz |
|--------|--------|
| Honza + Lucka | oba K7 @13:12 |
| Martin + Tereza | oba I8 @13:02 |
| Anežka + Matouš | oba L12 ~13:10 |
| Markéta + Míra | dvojice (cesty se nepotkaly) |

## Lokálně

Stačí otevřít `index.html` přes libovolný static server, např.:

```bash
python3 -m http.server 8080
```

## Licence podkladu

OpenTopoMap: CC-BY-SA · data OpenStreetMap. Při přepnutí na Mapy.com dodrž attribution dle dokumentace API.
