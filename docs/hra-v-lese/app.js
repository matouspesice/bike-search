(function () {
  "use strict";

  var banner = document.getElementById("banner");
  function showBanner(html) {
    if (!banner) return;
    banner.innerHTML = html;
    banner.classList.add("visible");
  }
  function hideBanner() {
    if (!banner) return;
    banner.classList.remove("visible");
    banner.innerHTML = "";
  }

  var data = window.HRA_TRACKS;
  if (!data || !data.players) {
    showBanner("Chyba mapy: data.js se nenačetl (HRA_TRACKS chybí).");
    return;
  }

  var cfg = Object.assign({ mapyApiKey: "", preferMapy: true }, window.HRA_V_LESE_CONFIG || {});
  var params = new URLSearchParams(window.location.search);
  var apiKey = (params.get("apikey") || params.get("apiKey") || cfg.mapyApiKey || "").trim();

  var cols = data.grid.columns;
  var nRows = data.grid.rows;
  var b = data.grid.bounds;
  var cellW = (b.east - b.west) / cols.length;
  var cellH = (b.north - b.south) / nRows;

  function parseCell(id) {
    var m = String(id).trim().toUpperCase().match(/^([A-U])(\d{1,2})$/);
    if (!m) return null;
    var ci = cols.indexOf(m[1]);
    var ri = parseInt(m[2], 10) - 1;
    if (ci < 0 || ri < 0 || ri >= nRows) return null;
    return { c: ci, r: ri, id: m[1] + String(ri + 1) };
  }

  // Plain [[south, west], [north, east]] — avoids LatLngBounds edge cases
  function cellCorners(c, r) {
    var west = b.west + c * cellW;
    var east = west + cellW;
    var north = b.north - r * cellH;
    var south = north - cellH;
    return [
      [south, west],
      [north, east]
    ];
  }

  function cellCenterLatLng(c, r) {
    return [b.north - (r + 0.5) * cellH, b.west + (c + 0.5) * cellW];
  }

  // Legend + pairs first so UI works even if map drawing fails later
  var visible = {};
  data.players.forEach(function (p) {
    visible[p.id] = true;
  });

  var legendEl = document.getElementById("legend");
  data.players.forEach(function (p) {
    var row = document.createElement("label");
    row.className = "legend-item";
    row.innerHTML =
      '<span class="swatch" style="background:' +
      p.color +
      '"></span><span><input type="checkbox" checked data-id="' +
      p.id +
      '"> <strong>' +
      p.name +
      '</strong><div class="muted">' +
      p.path[0][0] +
      " → " +
      p.path[p.path.length - 1][0] +
      " · " +
      p.path.length +
      " políček</div></span>";
    legendEl.appendChild(row);
  });

  var pairsEl = document.getElementById("pairs");
  data.pairs.forEach(function (pair) {
    var div = document.createElement("div");
    div.className = "pair";
    div.innerHTML = "<strong>" + pair.label + '</strong><span class="muted">' + pair.note + "</span>";
    pairsEl.appendChild(div);
  });

  document.getElementById("uncertain").innerHTML =
    "<strong>Nejistoty</strong><ul>" +
    data.uncertain
      .map(function (u) {
        return "<li>" + u + "</li>";
      })
      .join("") +
    "</ul>";

  if (typeof L === "undefined") {
    showBanner("Chyba mapy: Leaflet se nenačetl.");
    return;
  }

  var map = L.map("map", { zoomControl: true });
  var gridLayer = L.layerGroup().addTo(map);
  var trackLayer = L.layerGroup().addTo(map);

  var otm = L.tileLayer("https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png", {
    maxZoom: 17,
    attribution:
      '&copy; <a href="https://opentopomap.org">OpenTopoMap</a> (<a href="https://creativecommons.org/licenses/by-sa/3.0/">CC-BY-SA</a>) · &copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
  });

  function mapyUrl(key) {
    return "https://api.mapy.cz/v1/maptiles/outdoor/256/{z}/{x}/{y}?apikey=" + encodeURIComponent(key);
  }

  var usingMapy = false;
  if (apiKey && cfg.preferMapy !== false) {
    var mapyLayer = L.tileLayer(mapyUrl(apiKey), {
      maxZoom: 19,
      attribution:
        '<a href="https://api.mapy.cz" target="_blank"><img src="https://api.mapy.cz/img/api/logo.svg" alt="Mapy.com" style="height:1em;vertical-align:middle"></a> © Seznam.cz a další'
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
      "Chybí API klíč Mapy.cz — dočasný podklad OpenTopoMap. Přidej <code>config.js</code> nebo <code>?apikey=…</code> (viz README)."
    );
  }

  function drawGrid() {
    gridLayer.clearLayers();
    var c, r, id, rect;
    for (c = 0; c < cols.length; c++) {
      for (r = 0; r < nRows; r++) {
        id = cols.charAt(c) + String(r + 1);
        rect = L.rectangle(cellCorners(c, r), {
          color: "#2c3e2a",
          weight: 0.7,
          opacity: 0.5,
          fillOpacity: 0,
          interactive: true
        });
        rect.bindTooltip(id, { sticky: true, className: "cell-tooltip" });
        gridLayer.addLayer(rect);
      }
    }
    for (c = 0; c < cols.length; c++) {
      L.marker([b.north + cellH * 0.2, b.west + (c + 0.5) * cellW], {
        interactive: false,
        icon: L.divIcon({
          className: "grid-label",
          html:
            '<div style="font:600 11px IBM Plex Sans,sans-serif;color:#1a2418;text-align:center;width:20px;margin-left:-10px">' +
            cols.charAt(c) +
            "</div>"
        })
      }).addTo(gridLayer);
    }
    for (r = 0; r < nRows; r++) {
      L.marker([b.north - (r + 0.5) * cellH, b.west - cellW * 0.4], {
        interactive: false,
        icon: L.divIcon({
          className: "grid-label",
          html:
            '<div style="font:600 11px IBM Plex Sans,sans-serif;color:#1a2418;width:22px;text-align:right">' +
            String(r + 1) +
            "</div>"
        })
      }).addTo(gridLayer);
    }
  }

  function drawPlayers() {
    trackLayer.clearLayers();
    data.players.forEach(function (player) {
      if (!visible[player.id]) return;
      var pts = [];
      var seen = {};
      player.path.forEach(function (step, idx) {
        var cell = step[0];
        var time = step[1];
        var p = parseCell(cell);
        if (!p) return;
        var center = cellCenterLatLng(p.c, p.r);
        pts.push(center);
        if (!seen[p.id]) {
          seen[p.id] = true;
          var fill = L.rectangle(cellCorners(p.c, p.r), {
            color: player.color,
            weight: 1.4,
            fillColor: player.color,
            fillOpacity: 0.32,
            opacity: 0.95
          });
          fill.bindTooltip(player.name + "<br><strong>" + p.id + "</strong> · " + time, { sticky: true });
          trackLayer.addLayer(fill);
        }
        var order = L.circleMarker(center, {
          radius: idx === 0 || idx === player.path.length - 1 ? 6 : 4,
          color: "#ffffff",
          weight: 1.5,
          fillColor: player.color,
          fillOpacity: 1
        });
        order.bindTooltip(String(idx + 1) + ". " + p.id + " (" + time + ") — " + player.name);
        trackLayer.addLayer(order);
      });
      if (pts.length > 1) {
        trackLayer.addLayer(
          L.polyline(pts, {
            color: player.color,
            weight: 3,
            opacity: 0.9
          })
        );
      }
    });
  }

  function fitGameBounds() {
    map.invalidateSize();
    map.fitBounds(
      [
        [b.south, b.west],
        [b.north, b.east]
      ],
      { padding: [28, 28], maxZoom: 14 }
    );
  }

  try {
    map.setView([(b.north + b.south) / 2, (b.west + b.east) / 2], 13);
    drawGrid();
    drawPlayers();
    L.circleMarker([data.car.lat, data.car.lon], {
      radius: 8,
      color: "#222222",
      weight: 2,
      fillColor: "#f1c40f",
      fillOpacity: 1
    })
      .bindPopup(
        "<strong>" +
          data.car.label +
          "</strong><br>" +
          data.car.lat.toFixed(5) +
          ", " +
          data.car.lon.toFixed(5)
      )
      .addTo(map);

    fitGameBounds();
    map.whenReady(fitGameBounds);
    setTimeout(fitGameBounds, 150);
    setTimeout(fitGameBounds, 600);
    window.addEventListener("resize", fitGameBounds);
  } catch (err) {
    console.error(err);
    showBanner("Chyba mapy: " + (err && err.message ? err.message : String(err)));
  }

  legendEl.addEventListener("change", function (e) {
    var t = e.target;
    if (t && t.matches && t.matches("input[type=checkbox][data-id]")) {
      visible[t.getAttribute("data-id")] = t.checked;
      drawPlayers();
    }
  });

  document.getElementById("btn-all").onclick = function () {
    legendEl.querySelectorAll("input[type=checkbox]").forEach(function (cb) {
      cb.checked = true;
      visible[cb.getAttribute("data-id")] = true;
    });
    drawPlayers();
  };
  document.getElementById("btn-none").onclick = function () {
    legendEl.querySelectorAll("input[type=checkbox]").forEach(function (cb) {
      cb.checked = false;
      visible[cb.getAttribute("data-id")] = false;
    });
    drawPlayers();
  };
  document.getElementById("btn-fit").onclick = function () {
    map.fitBounds(
      [
        [b.south, b.west],
        [b.north, b.east]
      ],
      { padding: [28, 28], maxZoom: 14 }
    );
  };

  var playTimer = null;
  var playBtn = document.getElementById("btn-play");
  playBtn.onclick = function () {
    if (playTimer) {
      clearInterval(playTimer);
      playTimer = null;
      playBtn.textContent = "Přehrát pořadí";
      playBtn.classList.remove("active");
      drawPlayers();
      return;
    }
    playBtn.textContent = "Stop";
    playBtn.classList.add("active");
    var events = [];
    data.players.forEach(function (p) {
      if (!visible[p.id]) return;
      p.path.forEach(function (step, idx) {
        var parsed = parseCell(step[0]);
        if (!parsed) return;
        events.push({ t: step[1], idx: idx, player: p, cell: parsed });
      });
    });
    events.sort(function (a, b) {
      if (a.t === b.t) return a.idx - b.idx;
      return a.t < b.t ? -1 : 1;
    });
    trackLayer.clearLayers();
    var i = 0;
    var drawn = {};
    playTimer = setInterval(function () {
      if (i >= events.length) {
        clearInterval(playTimer);
        playTimer = null;
        playBtn.textContent = "Přehrát pořadí";
        playBtn.classList.remove("active");
        return;
      }
      var ev = events[i++];
      var key = ev.player.id + ":" + ev.cell.id;
      if (!drawn[key]) {
        drawn[key] = true;
        trackLayer.addLayer(
          L.rectangle(cellCorners(ev.cell.c, ev.cell.r), {
            color: ev.player.color,
            weight: 1.2,
            fillColor: ev.player.color,
            fillOpacity: 0.35
          }).bindTooltip(ev.player.name + "<br>" + ev.cell.id + " · " + ev.t)
        );
      }
      trackLayer.addLayer(
        L.circleMarker(cellCenterLatLng(ev.cell.c, ev.cell.r), {
          radius: 5,
          color: "#fff",
          weight: 1,
          fillColor: ev.player.color,
          fillOpacity: 1
        })
      );
    }, 280);
  };
})();
