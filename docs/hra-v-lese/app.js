(function () {
  "use strict";

  var banner = document.getElementById("banner");
  function showBanner(html) {
    if (!banner) return;
    banner.innerHTML = html;
    banner.classList.add("visible");
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

  if (typeof L === "undefined") {
    showBanner("Chyba mapy: Leaflet se nenačetl.");
    return;
  }

  function isMobileLayout() {
    return window.matchMedia("(max-width: 820px)").matches;
  }

  /** Force document scroll on mobile — kill any leftover viewport lock. */
  function unlockDocumentScroll() {
    if (!isMobileLayout()) return;
    document.documentElement.style.height = "auto";
    document.documentElement.style.overflowY = "scroll";
    document.documentElement.style.overflowX = "hidden";
    document.body.style.height = "auto";
    document.body.style.minHeight = "0";
    document.body.style.overflow = "visible";
    document.body.style.display = "block";
    var panelBody = document.querySelector(".panel-body");
    if (panelBody) {
      panelBody.style.overflow = "visible";
      panelBody.style.height = "auto";
      panelBody.style.maxHeight = "none";
    }
    var panel = document.querySelector("aside.panel");
    if (panel) {
      panel.style.overflow = "visible";
      panel.style.height = "auto";
    }
    var main = document.querySelector("main");
    if (main) {
      main.style.height = "auto";
      main.style.overflow = "visible";
    }
  }
  unlockDocumentScroll();

  // Mobile: no one-finger map drag — vertical page scroll must win.
  // Pan/zoom via +/- buttons (and pinch zoom). Desktop keeps normal drag.
  var map = L.map("map", {
    zoomControl: true,
    dragging: !isMobileLayout(),
    doubleClickZoom: true,
    boxZoom: !isMobileLayout(),
    keyboard: !isMobileLayout(),
    scrollWheelZoom: !isMobileLayout(),
    touchZoom: true,
    tapHold: false
  });
  var gridLayer = L.layerGroup().addTo(map);
  var trackLayer = L.layerGroup().addTo(map);

  function applyMobileMapGestures() {
    var mobile = isMobileLayout();
    var el = map.getContainer();
    unlockDocumentScroll();
    if (mobile) {
      map.dragging.disable();
      if (map.boxZoom) map.boxZoom.disable();
      if (map.keyboard) map.keyboard.disable();
      el.style.touchAction = "pan-y";
      el.classList.add("map-page-scroll");
    } else {
      map.dragging.enable();
      if (map.boxZoom) map.boxZoom.enable();
      if (map.keyboard) map.keyboard.enable();
      el.style.touchAction = "";
      el.classList.remove("map-page-scroll");
    }
    map.invalidateSize();
  }
  applyMobileMapGestures();
  window.matchMedia("(max-width: 820px)").addEventListener("change", applyMobileMapGestures);

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

  function buildEvents() {
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
      if (a.t === b.t) {
        if (a.player.name === b.player.name) return a.idx - b.idx;
        return a.player.name < b.player.name ? -1 : 1;
      }
      return a.t < b.t ? -1 : 1;
    });
    return events;
  }

  /** Draw cumulative state through events[0..throughIndex] inclusive. throughIndex -1 = empty. */
  function renderThrough(throughIndex) {
    trackLayer.clearLayers();
    var events = timelineEvents;
    if (!events.length || throughIndex < 0) return;

    var end = Math.min(throughIndex, events.length - 1);
    var seen = {};
    var lastByPlayer = {};
    var polylines = {};

    var i, ev, key, center, playerId;
    for (i = 0; i <= end; i++) {
      ev = events[i];
      playerId = ev.player.id;
      key = playerId + ":" + ev.cell.id;
      center = cellCenterLatLng(ev.cell.c, ev.cell.r);

      if (!polylines[playerId]) polylines[playerId] = [];
      polylines[playerId].push(center);
      lastByPlayer[playerId] = ev;

      if (!seen[key]) {
        seen[key] = true;
        trackLayer.addLayer(
          L.rectangle(cellCorners(ev.cell.c, ev.cell.r), {
            color: ev.player.color,
            weight: 1.4,
            fillColor: ev.player.color,
            fillOpacity: 0.32,
            opacity: 0.95
          }).bindTooltip(ev.player.name + "<br><strong>" + ev.cell.id + "</strong> · " + ev.t, { sticky: true })
        );
      }
    }

    Object.keys(polylines).forEach(function (pid) {
      var pts = polylines[pid];
      if (pts.length > 1) {
        trackLayer.addLayer(
          L.polyline(pts, {
            color: events.find(function (e) {
              return e.player.id === pid;
            }).player.color,
            weight: 3,
            opacity: 0.9
          })
        );
      }
    });

    // All visited step markers; emphasize current tip per player
    for (i = 0; i <= end; i++) {
      ev = events[i];
      center = cellCenterLatLng(ev.cell.c, ev.cell.r);
      var isTip = lastByPlayer[ev.player.id] === ev;
      trackLayer.addLayer(
        L.circleMarker(center, {
          radius: isTip ? 7 : 4,
          color: "#ffffff",
          weight: 1.5,
          fillColor: ev.player.color,
          fillOpacity: 1
        }).bindTooltip(
          (isTip ? "● " : "") + String(ev.idx + 1) + ". " + ev.cell.id + " (" + ev.t + ") — " + ev.player.name
        )
      );
    }
  }

  var scrubber = document.getElementById("scrubber");
  var scrubberMeta = document.getElementById("scrubber-meta");
  var timelineEvents = [];
  var playTimer = null;
  var playBtn = document.getElementById("btn-play");
  var syncingScrubber = false;

  function updateScrubberMeta(index) {
    var n = timelineEvents.length;
    if (!n) {
      scrubberMeta.textContent = "Žádné body (zapni hráče v legendě).";
      scrubber.setAttribute("aria-valuetext", "prázdné");
      return;
    }
    var ev = timelineEvents[index];
    var label =
      ev.t +
      " · " +
      ev.player.name +
      " · " +
      ev.cell.id +
      "  (" +
      String(index + 1) +
      "/" +
      String(n) +
      ")";
    scrubberMeta.textContent = label;
    scrubber.setAttribute("aria-valuetext", label);
  }

  function syncTimelineUI() {
    timelineEvents = buildEvents();
    var n = timelineEvents.length;
    scrubber.min = "0";
    scrubber.max = String(Math.max(0, n - 1));
    scrubber.disabled = n === 0;
    var idx = n ? n - 1 : 0;
    syncingScrubber = true;
    scrubber.value = String(idx);
    syncingScrubber = false;
    updateScrubberMeta(idx);
    renderThrough(n ? idx : -1);
  }

  function stopPlay() {
    if (playTimer) {
      clearInterval(playTimer);
      playTimer = null;
    }
    playBtn.textContent = "Přehrát";
    playBtn.classList.remove("active");
  }

  scrubber.addEventListener("input", function () {
    if (syncingScrubber) return;
    stopPlay();
    var idx = parseInt(scrubber.value, 10) || 0;
    updateScrubberMeta(idx);
    renderThrough(idx);
  });

  // Improve mobile dragging of range without scrolling the panel
  scrubber.addEventListener(
    "touchstart",
    function (e) {
      e.stopPropagation();
    },
    { passive: true }
  );

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

    syncTimelineUI();
    fitGameBounds();
    map.whenReady(fitGameBounds);
    setTimeout(fitGameBounds, 150);
    setTimeout(fitGameBounds, 600);
    window.addEventListener("resize", fitGameBounds);
  } catch (err) {
    console.error(err);
    showBanner("Chyba mapy: " + (err && err.message ? err.message : String(err)));
  }

  function refreshAfterVisibilityChange() {
    stopPlay();
    syncTimelineUI();
  }

  legendEl.addEventListener("change", function (e) {
    var t = e.target;
    if (t && t.matches && t.matches("input[type=checkbox][data-id]")) {
      visible[t.getAttribute("data-id")] = t.checked;
      refreshAfterVisibilityChange();
    }
  });

  document.getElementById("btn-all").onclick = function () {
    legendEl.querySelectorAll("input[type=checkbox]").forEach(function (cb) {
      cb.checked = true;
      visible[cb.getAttribute("data-id")] = true;
    });
    refreshAfterVisibilityChange();
  };
  document.getElementById("btn-none").onclick = function () {
    legendEl.querySelectorAll("input[type=checkbox]").forEach(function (cb) {
      cb.checked = false;
      visible[cb.getAttribute("data-id")] = false;
    });
    refreshAfterVisibilityChange();
  };
  document.getElementById("btn-fit").onclick = fitGameBounds;

  playBtn.onclick = function () {
    if (playTimer) {
      stopPlay();
      return;
    }
    timelineEvents = buildEvents();
    if (!timelineEvents.length) return;

    // Restart from beginning when already at the end
    if ((parseInt(scrubber.value, 10) || 0) >= timelineEvents.length - 1) {
      syncingScrubber = true;
      scrubber.value = "0";
      syncingScrubber = false;
      updateScrubberMeta(0);
      renderThrough(0);
    }

    playBtn.textContent = "Stop";
    playBtn.classList.add("active");

    playTimer = setInterval(function () {
      var next = (parseInt(scrubber.value, 10) || 0) + 1;
      if (next >= timelineEvents.length) {
        stopPlay();
        return;
      }
      syncingScrubber = true;
      scrubber.value = String(next);
      syncingScrubber = false;
      updateScrubberMeta(next);
      renderThrough(next);
    }, 320);
  };
})();
