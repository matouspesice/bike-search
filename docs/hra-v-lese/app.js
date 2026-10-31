(function () {
  const data = window.HRA_TRACKS;
  const cfg = Object.assign({ mapyApiKey: "", preferMapy: true }, window.HRA_V_LESE_CONFIG || {});
  const params = new URLSearchParams(location.search);
  const apiKey = (params.get("apikey") || params.get("apiKey") || cfg.mapyApiKey || "").trim();

  const cols = data.grid.columns;
  const nRows = data.grid.rows;
  const b = data.grid.bounds;
  const cellW = (b.east - b.west) / cols.length;
  const cellH = (b.north - b.south) / nRows;

  function parseCell(id) {
    const m = String(id).trim().toUpperCase().match(/^([A-U])(\d{1,2})$/);
    if (!m) return null;
    const ci = cols.indexOf(m[1]);
    const ri = parseInt(m[2], 10) - 1;
    if (ci < 0 || ri < 0 || ri >= nRows) return null;
    return { c: ci, r: ri, id: m[1] + (ri + 1) };
  }
  function cellBounds(c, r) {
    const west = b.west + c * cellW;
    const east = west + cellW;
    const north = b.north - r * cellH;
    const south = north - cellH;
    return [[south, west], [north, east]];
  }
  function cellCenter(c, r) {
    return [b.north - (r + 0.5) * cellH, b.west + (c + 0.5) * cellW];
  }

  const banner = document.getElementById("banner");
  const map = L.map("map", { zoomControl: true, preferCanvas: true });

  const otm = L.tileLayer("https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png", {
    maxZoom: 17,
    attribution: '&copy; <a href="https://opentopomap.org">OpenTopoMap</a> (<a href="https://creativecommons.org/licenses/by-sa/3.0/">CC-BY-SA</a>) · &copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
  });

  // Mapy.cz / Mapy.com outdoor — aktivní až s klíčem
  let mapyLayer = null;
  function mapyUrl(key) {
    return "https://api.mapy.cz/v1/maptiles/outdoor/256/{z}/{x}/{y}?apikey=" + encodeURIComponent(key);
  }

  let usingMapy = false;
  if (apiKey && cfg.preferMapy !== false) {
    mapyLayer = L.tileLayer(mapyUrl(apiKey), {
      maxZoom: 19,
      attribution: '<a href="https://api.mapy.cz" target="_blank"><img src="https://api.mapy.cz/img/api/logo.svg" alt="Mapy.com" style="height:1em;vertical-align:middle"></a> © Seznam.cz a další'
    });
    mapyLayer.on("tileerror", function () {
      if (usingMapy) {
        usingMapy = false;
        map.removeLayer(mapyLayer);
        otm.addTo(map);
        showBanner("Mapy.cz dlaždice selhaly — přepnuto na OpenTopoMap. Zkontroluj API klíč.");
      }
    });
    mapyLayer.addTo(map);
    usingMapy = true;
  } else {
    otm.addTo(map);
    showBanner(
      apiKey
        ? "Mapy klíč je nastavený, ale preferMapy=false — běží OpenTopoMap."
        : "Chybí API klíč Mapy.cz — dočasný podklad OpenTopoMap. Přidej <code>config.js</code> nebo <code>?apikey=…</code> (viz README)."
    );
  }

  function showBanner(html) {
    banner.innerHTML = html;
    banner.classList.add("visible");
  }

  const gridLayer = L.layerGroup().addTo(map);
  const trackLayer = L.layerGroup().addTo(map);
  const visible = Object.fromEntries(data.players.map((p) => [p.id, true]));

  // Draw full grid
  for (let c = 0; c < cols.length; c++) {
    for (let r = 0; r < nRows; r++) {
      const id = cols[c] + (r + 1);
      const rect = L.rectangle(cellBounds(c, r), {
        color: "#2c3e2a",
        weight: 0.6,
        opacity: 0.45,
        fill: false,
        interactive: true
      });
      rect.bindTooltip(id, { sticky: true, className: "cell-tooltip", direction: "center" });
      gridLayer.addLayer(rect);
    }
  }
  // Column / row labels on edges
  for (let c = 0; c < cols.length; c++) {
    const [lat] = cellCenter(c, 0);
    L.marker([b.north + cellH * 0.15, b.west + (c + 0.5) * cellW], {
      interactive: false,
      icon: L.divIcon({ className: "", html: `<div style="font:600 11px IBM Plex Sans,sans-serif;color:#1a2418;text-align:center;width:20px;margin-left:-10px">${cols[c]}</div>` })
    }).addTo(gridLayer);
  }
  for (let r = 0; r < nRows; r++) {
    const [, lon] = cellCenter(0, r);
    L.marker([b.north - (r + 0.5) * cellH, b.west - cellW * 0.35], {
      interactive: false,
      icon: L.divIcon({ className: "", html: `<div style="font:600 11px IBM Plex Sans,sans-serif;color:#1a2418;width:22px;text-align:right">${r + 1}</div>` })
    }).addTo(gridLayer);
  }

  const playerLayers = {};

  function drawPlayers() {
    trackLayer.clearLayers();
    data.players.forEach((player) => {
      if (!visible[player.id]) return;
      const pts = [];
      const seen = new Set();
      player.path.forEach(([cell, time], idx) => {
        const p = parseCell(cell);
        if (!p) return;
        const center = cellCenter(p.c, p.r);
        pts.push(center);
        if (!seen.has(p.id)) {
          seen.add(p.id);
          const fill = L.rectangle(cellBounds(p.c, p.r), {
            color: player.color,
            weight: 1.2,
            fillColor: player.color,
            fillOpacity: 0.28,
            opacity: 0.9
          });
          fill.bindTooltip(`${player.name}<br><strong>${p.id}</strong> · ${time}`, { sticky: true });
          trackLayer.addLayer(fill);
        }
        const order = L.circleMarker(center, {
          radius: idx === 0 || idx === player.path.length - 1 ? 6 : 4,
          color: "#fff",
          weight: 1.5,
          fillColor: player.color,
          fillOpacity: 1
        });
        order.bindTooltip(`${idx + 1}. ${p.id} (${time}) — ${player.name}`);
        trackLayer.addLayer(order);
      });
      if (pts.length > 1) {
        trackLayer.addLayer(L.polyline(pts, { color: player.color, weight: 3, opacity: 0.85 }));
      }
    });
  }

  L.circleMarker([data.car.lat, data.car.lon], {
    radius: 8, color: "#222", weight: 2, fillColor: "#f1c40f", fillOpacity: 1
  }).bindPopup(`<strong>${data.car.label}</strong><br>${data.car.lat.toFixed(5)}, ${data.car.lon.toFixed(5)}`).addTo(map);

  drawPlayers();
  map.fitBounds([[b.south, b.west], [b.north, b.east]], { padding: [24, 24] });

  // Legend UI
  const legendEl = document.getElementById("legend");
  data.players.forEach((p) => {
    const row = document.createElement("label");
    row.className = "legend-item";
    row.innerHTML = `<span class="swatch" style="background:${p.color}"></span>
      <span><input type="checkbox" checked data-id="${p.id}"> <strong>${p.name}</strong>
      <div class="muted">${p.path[0][0]} → ${p.path[p.path.length - 1][0]} · ${p.path.length} políček</div></span>`;
    legendEl.appendChild(row);
  });
  legendEl.addEventListener("change", (e) => {
    const t = e.target;
    if (t.matches("input[type=checkbox][data-id]")) {
      visible[t.getAttribute("data-id")] = t.checked;
      drawPlayers();
    }
  });

  const pairsEl = document.getElementById("pairs");
  data.pairs.forEach((pair) => {
    const div = document.createElement("div");
    div.className = "pair";
    div.innerHTML = `<strong>${pair.label}</strong><span class="muted">${pair.note}</span>`;
    pairsEl.appendChild(div);
  });

  const unc = document.getElementById("uncertain");
  unc.innerHTML = "<strong>Nejistoty</strong><ul>" + data.uncertain.map((u) => `<li>${u}</li>`).join("") + "</ul>";

  document.getElementById("btn-all").onclick = () => {
    legendEl.querySelectorAll("input[type=checkbox]").forEach((cb) => { cb.checked = true; visible[cb.dataset.id] = true; });
    drawPlayers();
  };
  document.getElementById("btn-none").onclick = () => {
    legendEl.querySelectorAll("input[type=checkbox]").forEach((cb) => { cb.checked = false; visible[cb.dataset.id] = false; });
    drawPlayers();
  };
  document.getElementById("btn-fit").onclick = () => {
    map.fitBounds([[b.south, b.west], [b.north, b.east]], { padding: [24, 24] });
  };

  // Simple playback by time order across all visible points
  let playTimer = null;
  const playBtn = document.getElementById("btn-play");
  playBtn.onclick = () => {
    if (playTimer) { clearInterval(playTimer); playTimer = null; playBtn.textContent = "Přehrát pořadí"; playBtn.classList.remove("active"); drawPlayers(); return; }
    playBtn.textContent = "Stop"; playBtn.classList.add("active");
    const events = [];
    data.players.forEach((p) => {
      if (!visible[p.id]) return;
      p.path.forEach(([cell, time], idx) => {
        const parsed = parseCell(cell);
        if (!parsed) return;
        events.push({ t: time, idx, player: p, cell: parsed });
      });
    });
    events.sort((a, b) => (a.t === b.t ? a.idx - b.idx : a.t < b.t ? -1 : 1));
    trackLayer.clearLayers();
    let i = 0;
    const drawn = {};
    playTimer = setInterval(() => {
      if (i >= events.length) { clearInterval(playTimer); playTimer = null; playBtn.textContent = "Přehrát pořadí"; playBtn.classList.remove("active"); return; }
      const ev = events[i++];
      const key = ev.player.id + ":" + ev.cell.id;
      if (!drawn[key]) {
        drawn[key] = true;
        trackLayer.addLayer(L.rectangle(cellBounds(ev.cell.c, ev.cell.r), {
          color: ev.player.color, weight: 1.2, fillColor: ev.player.color, fillOpacity: 0.35
        }).bindTooltip(`${ev.player.name}<br>${ev.cell.id} · ${ev.t}`));
      }
      trackLayer.addLayer(L.circleMarker(cellCenter(ev.cell.c, ev.cell.r), {
        radius: 5, color: "#fff", weight: 1, fillColor: ev.player.color, fillOpacity: 1
      }));
    }, 280);
  };
})();
