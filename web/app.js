import * as M from "./model.js";

const $ = (id) => document.getElementById(id);
// Sequential "heat" ramp (ColorBrewer YlOrRd): light = low, dark red = high.
const RAMP = [[0, [255, 255, 178]], [0.25, [254, 204, 92]], [0.5, [253, 141, 60]], [0.75, [240, 59, 32]], [1, [189, 0, 38]]];
const MODES = {
  indice: "Indice = habitat × conditions météo (100 : habitat idéal et journée parmi les meilleures de la saison).",
  habitat: "Habitat : arbres-hôtes, altitude et pH du sol (indépendant de la météo).",
  meteo: "Conditions : météo des semaines précédentes comparée aux jours habituels de la saison (là où l'habitat convient).",
};
const DAY_FMT = new Intl.DateTimeFormat("fr-FR", { weekday: "long", day: "numeric", month: "long" });
const SHORT_FMT = new Intl.DateTimeFormat("fr-FR", { weekday: "short", day: "numeric" });

const state = { mode: "indice", sp: 0, day: 0, opacity: 0.8 };
let D;                 // loaded data
let map, overlay, canvas, ctx, image, pixels, palette, marker;

const store = {
  get(k, def) { try { const v = localStorage.getItem("mushroomator." + k); return v === null ? def : JSON.parse(v); } catch { return def; } },
  set(k, v) { try { localStorage.setItem("mushroomator." + k, JSON.stringify(v)); } catch { /* private mode */ } },
};

async function loadJSON(url) {
  const r = await fetch(url, { cache: "no-cache" });
  if (!r.ok) throw new Error(`${url} : HTTP ${r.status}`);
  return r.json();
}

async function loadArray(url, Type) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${url} : HTTP ${r.status}`);
  let bytes = new Uint8Array(await r.arrayBuffer());
  if (bytes[0] === 0x1f && bytes[1] === 0x8b) {          // still gzipped (the server did not decode it)
    const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream("gzip"));
    bytes = new Uint8Array(await new Response(stream).arrayBuffer());
  }
  return new Type(bytes.buffer, bytes.byteOffset, bytes.byteLength / Type.BYTES_PER_ELEMENT);
}

function buildPalette() {
  const pal = new Uint32Array(256);
  for (let i = 0; i < 256; i++) {
    const v = i / 255;
    if (v < 0.04) { pal[i] = 0; continue; }
    let k = 0;
    while (k < RAMP.length - 2 && v > RAMP[k + 1][0]) k++;
    const [v0, c0] = RAMP[k], [v1, c1] = RAMP[k + 1];
    const f = (v - v0) / (v1 - v0);
    const [r, g, b] = c0.map((x, j) => Math.round(x + (c1[j] - x) * f));
    const a = Math.round(255 * Math.min(1, 0.35 + 0.75 * v));
    pal[i] = ((a << 24) | (b << 16) | (g << 8) | r) >>> 0;   // little-endian RGBA
  }
  return pal;
}

const CanvasOverlay = L.ImageOverlay.extend({
  _initImage() {
    this._image = this._url;
    L.DomUtil.addClass(this._image, "leaflet-image-layer");
    if (this._zoomAnimated) L.DomUtil.addClass(this._image, "leaflet-zoom-animated");
    this._image.onselectstart = L.Util.falseFn;
    this._image.onmousemove = L.Util.falseFn;
    if (this.options.zIndex != null) this._updateZIndex();
    if (this.options.className) L.DomUtil.addClass(this._image, this.options.className);
  },
});

function baseLayers() {
  const ign = (layer, fmt) => "https://data.geopf.fr/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0" +
    `&LAYER=${layer}&STYLE=normal&TILEMATRIXSET=PM&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}&FORMAT=${fmt}`;
  const ignAttr = '© <a href="https://www.ign.fr/">IGN</a>';
  return {
    "Plan IGN": L.tileLayer(ign("GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2", "image/png"), { maxZoom: 19, attribution: ignAttr, crossOrigin: true }),
    "Relief (OpenTopoMap)": L.tileLayer("https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png", {
      maxZoom: 17, subdomains: "abc", crossOrigin: true,
      attribution: 'Carte © <a href="https://opentopomap.org">OpenTopoMap</a> (CC-BY-SA), données © <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }),
    "Photos aériennes IGN": L.tileLayer(ign("ORTHOIMAGERY.ORTHOPHOTOS", "image/jpeg"), { maxZoom: 19, attribution: ignAttr, crossOrigin: true }),
    "OpenStreetMap": L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19, crossOrigin: true, attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }),
  };
}

function initMap() {
  const [w, s, e, n] = D.grid.bounds;
  map = L.map("map", { zoomControl: false, maxBounds: [[s - 1, w - 1], [n + 1, e + 1]], minZoom: 7 });
  map.fitBounds([[s, w], [n, e]]);
  const bases = baseLayers();
  const chosen = store.get("base", "Plan IGN");
  (bases[chosen] || bases["Plan IGN"]).addTo(map);
  L.control.zoom({ position: "topright" }).addTo(map);
  L.control.layers(bases, null, { position: "topright" }).addTo(map);
  map.on("baselayerchange", (ev) => store.set("base", ev.name));
  map.attributionControl.addAttribution('Météo <a href="https://open-meteo.com/">Open-Meteo</a> · Forêts IGN BD Forêt');
  const Locate = L.Control.extend({
    options: { position: "topright" },
    onAdd() {
      const b = L.DomUtil.create("button", "locate-btn leaflet-bar");
      b.type = "button"; b.title = "Ma position"; b.setAttribute("aria-label", "Ma position"); b.textContent = "◎";
      L.DomEvent.on(b, "click", (ev) => { L.DomEvent.stop(ev); map.locate({ setView: true, maxZoom: 14 }); });
      return b;
    },
  });
  new Locate().addTo(map);
  map.on("locationfound", (ev) => {
    if (marker) marker.remove();
    marker = L.circleMarker(ev.latlng, { radius: 7, color: "#fff", weight: 2, fillColor: "#2a78d6", fillOpacity: 1 }).addTo(map);
  });
  map.on("locationerror", () => alert("Position indisponible."));

  canvas = document.createElement("canvas");
  canvas.width = D.grid.nx; canvas.height = D.grid.ny;
  ctx = canvas.getContext("2d");
  image = ctx.createImageData(D.grid.nx, D.grid.ny);
  pixels = new Uint32Array(image.data.buffer);
  overlay = new CanvasOverlay(canvas, [[s, w], [n, e]], { opacity: state.opacity, interactive: false, className: "heat" });
  overlay.addTo(map);
  map.on("click", (ev) => showDetails(ev.latlng));
}

function render() {
  const sp = D.species[state.sp];
  const fields = state.mode === "habitat" || !D.weather ? null : M.coarseFields(sp, D.weather, state.day);
  const mode = fields ? state.mode : "habitat";
  const values = M.computeGrid(sp, D.layers, fields, D.wts, mode);
  for (let p = 0; p < values.length; p++) {
    const v = values[p];
    pixels[p] = v === v ? palette[Math.max(0, Math.min(255, Math.round(v * 255)))] : 0;
  }
  ctx.putImageData(image, 0, 0);
  $("legend-text").textContent = MODES[mode] + (D.weather ? "" : " Météo indisponible : seul l'habitat est affiché.");
}

function dayLabel(iso) {
  const today = D.weather.today;
  const diff = Math.round((new Date(iso) - new Date(today)) / 86400000);
  const names = { "-1": "Hier", 0: "Aujourd'hui", 1: "Demain" };
  return names[diff] ?? DAY_FMT.format(new Date(iso + "T12:00:00"));
}

function updateDayUI() {
  if (!D.weather) { $("day-label").textContent = "Habitat"; $("day-note").textContent = ""; return; }
  const iso = D.weather.dates[state.day];
  const diff = Math.round((new Date(iso) - new Date(D.weather.today)) / 86400000);
  const label = dayLabel(iso), full = DAY_FMT.format(new Date(iso + "T12:00:00"));
  $("day-label").textContent = label === full ? full.charAt(0).toUpperCase() + full.slice(1) : `${label} · ${full}`;
  const replay = D.weather.source.startsWith("Rejeu");
  $("day-note").textContent = replay ? "rejeu d'une date passée (météo observée)"
    : diff > 0 ? "prévision" : diff < 0 ? "météo observée" : "en partie prévu";
  document.querySelectorAll("#day-strip .bar").forEach((b, k) => b.classList.toggle("selected", k === state.day));
}

function buildDayStrip() {
  const strip = $("day-strip");
  strip.innerHTML = "";
  if (!D.weather) return;
  const sp = D.species[state.sp];
  const summary = M.dailySummary(sp, D.layers, D.weather, D.wts);
  D.weather.dates.forEach((iso, k) => {
    const v = summary[k];
    const bar = document.createElement("button");
    bar.type = "button";
    bar.className = "bar";
    const pct = Number.isFinite(v) ? Math.round(v * 100) : null;
    const date = new Date(iso + "T12:00:00");
    bar.style.setProperty("--h", String(Math.max(4, pct ?? 0)));
    bar.title = `${DAY_FMT.format(date)} : conditions ${pct ?? "—"}/100 en habitat favorable`;
    bar.setAttribute("aria-label", bar.title);
    if (iso === D.weather.today) bar.classList.add("today");
    bar.innerHTML = `<span class="fill"></span><span class="lbl">${date.getDate()}</span>`;
    bar.addEventListener("click", () => { state.day = k; $("day").value = k; updateDayUI(); render(); });
    strip.appendChild(bar);
  });
}

const fmt = (v, d = 0) => Number.isFinite(v) ? v.toLocaleString("fr-FR", { maximumFractionDigits: d, minimumFractionDigits: d }) : "—";

function factorText(effect) {
  const x = Math.exp(effect);
  const cls = effect > 0.15 ? "up" : effect < -0.15 ? "down" : "flat";
  const word = cls === "up" ? "favorable" : cls === "down" ? "défavorable" : "neutre";
  return `<span class="eff ${cls}">×${fmt(x, x < 10 ? 1 : 0)} <small>${word}</small></span>`;
}

function chartSvg(series, key, todayIso, selectedIso, kind) {
  const vals = series[key][D.pointIndex];
  const dates = series.dates, n = dates.length, W = 300, H = 64, pad = 2;
  const max = kind === "bars" ? Math.max(10, ...vals.filter(Number.isFinite)) : Math.max(...vals.filter(Number.isFinite));
  const min = kind === "bars" ? 0 : Math.min(...vals.filter(Number.isFinite));
  const x = (i) => pad + (i + 0.5) * (W - 2 * pad) / n;
  const y = (v) => H - 14 - (v - min) / (max - min || 1) * (H - 22);
  const ti = dates.indexOf(todayIso), si = dates.indexOf(selectedIso);
  let s = `<svg viewBox="0 0 ${W} ${H}" class="chart" role="img" aria-label="${kind === "bars" ? "Pluie quotidienne" : "Température moyenne"}">`;
  if (ti >= 0) s += `<rect x="${x(ti) - 1}" y="0" width="${W - x(ti)}" height="${H - 12}" class="future"/>`;
  if (kind === "bars") {
    const bw = Math.max(1, (W - 2 * pad) / n - 1.5);
    vals.forEach((v, i) => { if (v > 0) s += `<rect x="${x(i) - bw / 2}" y="${y(v)}" width="${bw}" height="${H - 14 - y(v)}" rx="1" class="bar"/>`; });
  } else {
    s += `<polyline class="line" points="${vals.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ")}"/>`;
  }
  if (si >= 0) s += `<line x1="${x(si)}" x2="${x(si)}" y1="0" y2="${H - 12}" class="sel"/>`;
  s += `<line x1="0" x2="${W}" y1="${H - 13.5}" y2="${H - 13.5}" class="axis"/>`;
  s += `<text x="2" y="${H - 2}" class="tick">${SHORT_FMT.format(new Date(dates[0] + "T12:00:00"))}</text>`;
  s += `<text x="${W - 2}" y="${H - 2}" text-anchor="end" class="tick">${SHORT_FMT.format(new Date(dates[n - 1] + "T12:00:00"))}</text>`;
  s += `<text x="${W - 2}" y="10" text-anchor="end" class="tick">${kind === "bars" ? `max ${fmt(max)} mm` : `${fmt(min)} à ${fmt(max)} °C`}</text>`;
  return s + "</svg>";
}

function showDetails(latlng) {
  const rc = M.pixelOf(D.grid, latlng.lat, latlng.lng);
  if (!rc) return;
  const [r, c] = rc;
  const sp = D.species[state.sp];
  const p = r * D.grid.nx + c;
  const groupName = D.groupNames[D.layers.host[p]];
  let html = `<h2>${sp.nom}</h2><p class="muted small">${latlng.lat.toFixed(4)}° N, ${latlng.lng.toFixed(4)}° E</p>`;
  const hab = M.pixelHabitat(sp, D.layers, p);
  if (!D.layers.host[p]) {
    html += `<p>Pas de formation forestière cartographiée ici (BD Forêt) : l'indice n'est pas calculé.</p>`;
  } else if (D.weather) {
    const fields = M.coarseFields(sp, D.weather, state.day);
    const ex = M.explain(sp, D.layers, fields, D.wts, r, c);
    html += `<div class="score"><span class="big">${Math.round(ex.index * 100)}</span><span>/100<br><small>indice du ${DAY_FMT.format(new Date(D.weather.dates[state.day] + "T12:00:00"))}</small></span></div>`;
    html += `<h3>Habitat : ${fmt(hab.H * 100)}/100</h3><ul class="facts">
      <li><span>${groupName}</span>${factorBar(hab.host)}</li>
      <li><span>Altitude ${fmt(hab.elev)} m</span>${factorBar(hab.elevF)}</li>
      <li><span>pH du sol ${fmt(hab.ph, 1)}</span>${factorBar(hab.phF)}</li></ul>`;
    html += `<h3>Conditions : ${fmt(ex.q * 100)}/100</h3>
      <p class="small muted">Meilleures que ${fmt(ex.q * 100)} % des jours habituels de la saison (${seasonText(sp)}).</p><ul class="facts">`;
    const seasonMean = seasonAverage(sp);
    for (const t of ex.terms) {
      if (t.name === "doy") t.effect -= seasonMean;
      const unit = D.units[t.name] || "";
      const value = t.name === "doy" ? DAY_FMT.format(new Date(D.weather.dates[state.day] + "T12:00:00"))
        : t.name === "SWB" ? `${fmt(t.value * 100)} %` : `${fmt(t.value, unit === "°C" ? 1 : 0)} ${unit}`;
      html += `<li><span>${D.labels[t.name]}<br><small class="muted">${value}</small></span>${factorText(t.effect)}</li>`;
    }
    html += `</ul><p class="small muted">Effets relatifs à une valeur typique (pour la saison : à un jour moyen de la saison) : ×2 double les chances, ×0,5 les divise par deux.</p>`;
    const pt = nearestPoint(latlng);
    D.pointIndex = pt;
    const s = D.weather.series;
    html += `<h3>Météo du secteur</h3><p class="small muted">Point météo à ${fmt(D.weather.elev.flat()[pt])} m ; zone grisée : prévisions.</p>`;
    html += `<p class="chart-title small">Pluie quotidienne</p>${chartSvg(s, "rr", D.weather.today, D.weather.dates[state.day], "bars")}`;
    html += `<p class="chart-title small">Température moyenne</p>${chartSvg(s, "tg", D.weather.today, D.weather.dates[state.day], "line")}`;
  } else {
    html += `<h3>Habitat : ${fmt(hab.H * 100)}/100</h3><p>${groupName}, ${fmt(hab.elev)} m, pH ${fmt(hab.ph, 1)}.</p>`;
  }
  html += `<p class="warning small"><strong>Confusions dangereuses :</strong> ${sp.confusions}</p>`;
  html += `<p class="small"><a href="https://www.geoportail.gouv.fr/carte?c=${latlng.lng},${latlng.lat}&z=15&l0=GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2::GEOPORTAIL:OGC:WMTS(1)&permalink=yes" target="_blank" rel="noopener">Ouvrir dans Géoportail</a></p>`;
  $("details-body").innerHTML = html;
  $("details").hidden = false;
}

function factorBar(v) {
  const pct = Math.round(Math.max(0, Math.min(1, v)) * 100);
  return `<span class="meter" title="${pct} %"><span style="width:${pct}%"></span></span>`;
}

function seasonAverage(sp) {
  const [a, b] = sp.modele.season, ys = sp.modele.tables.doy.y;
  let sum = 0;
  for (let d = a; d <= b; d++) sum += ys[d - 1];
  return sum / (b - a + 1);
}

function seasonText(sp) {
  const [a, b] = sp.modele.season;
  const f = new Intl.DateTimeFormat("fr-FR", { day: "numeric", month: "long" });
  const date = (doy) => f.format(new Date(Date.UTC(2023, 0, doy)));
  return `du ${date(a)} au ${date(b)}`;
}

function nearestPoint(latlng) {
  const { lons, lats } = D.weather;
  const j = Math.max(0, Math.min(lons.length - 1, Math.round((latlng.lng - lons[0]) / (lons[1] - lons[0]))));
  const i = Math.max(0, Math.min(lats.length - 1, Math.round((latlng.lat - lats[0]) / (lats[1] - lats[0]))));
  return i * lons.length + j;
}

function fillAbout() {
  const hind = D.validation?.hindcast?.species ?? {};
  const rows = D.species.map((s) => {
    const m = s.modele.metrics, h = hind[s.key];
    return `<tr><td>${s.nom}<br><small class="muted">${m.observations} obs.</small></td>
      <td>${fmt(m.auc_saison_modele_saison_seule, 2)} → <strong>${fmt(m.auc_saison, 2)}</strong></td>
      <td>${h ? fmt(h.auc_meme_lieu_autres_jours, 2) : "—"}</td><td>${h ? fmt(h.auc_indice_vs_autres_champignons, 2) : "—"}</td></tr>`;
  }).join("");
  const period = D.validation?.hindcast?.period;
  $("about-metrics").innerHTML = `<div class="table-wrap"><table><thead><tr><th>Espèce</th><th>Conditions en saison<br><small>saison seule → avec météo</small></th><th>Rejeu : jour trouvé vs autres jours</th><th>Rejeu : vs autres champignons</th></tr></thead><tbody>${rows}</tbody></table></div>
    <p class="small muted">AUC : 0,5 = hasard, 1 = parfait. <strong>Conditions</strong> : capacité à distinguer les jours d'observation des autres jours de la saison, sur des années non vues à l'entraînement (France et Suisse). <strong>Rejeu</strong>${period ? ` (${period[0].slice(0, 4)}–${period[1].slice(0, 4)}, Rhône-Alpes)` : ""} : indice calculé par l'application aux lieux et dates d'observations réelles, comparé au même lieu d'autres jours de l'année, puis aux observations d'autres champignons forestiers. « — » : trop peu d'observations précises dans la région.</p>`;
  $("about-sources").innerHTML = `${D.layersMeta.attribution}. Météo : ${D.weather ? D.weather.source : "—"}. Modèles entraînés sur les observations GBIF (France, Suisse) et la météo E-OBS (Copernicus/ECA&D, usage non commercial).`;
  $("about-version").textContent = `Version ${D.version}${D.weather ? ` · météo du ${D.weather.today}, générée le ${new Date(D.weather.generated).toLocaleString("fr-FR")}` : ""}`;
}

async function init() {
  const index = await loadJSON("data/index.json");
  const key = index.default, base = `data/${key}/`;
  const [meta, sp, weather] = await Promise.all([
    loadJSON(base + "layers.json"), loadJSON(base + "species.json"), loadJSON(base + "weather.json").catch(() => null)]);
  const files = meta.files;
  const types = { uint8: Uint8Array, uint16: Uint16Array };
  const [host, elev, ph10] = await Promise.all(["host", "elev", "ph10"].map(
    (k) => loadArray(base + files[k].file, types[files[k].dtype])));
  const grid = meta.grid;
  const axes = M.gridAxes(grid);
  D = {
    version: sp.version, grid, layersMeta: meta, layers: { grid, host, elev, ph10 }, species: sp.especes,
    groupNames: sp.groupes, labels: sp.variables, units: sp.unites, validation: sp.validation, weather,
    wts: weather ? { lon: M.axisWeights(weather.lons, axes.lon), lat: M.axisWeights(weather.lats, axes.lat) } : null,
  };
  $("region-name").textContent = meta.name;
  const select = $("species");
  D.species.forEach((s, k) => select.add(new Option(s.nom, k)));
  const savedKey = store.get("species", null);
  state.sp = Math.max(0, D.species.findIndex((s) => s.key === savedKey));
  select.value = state.sp;
  state.mode = store.get("mode", "indice");
  if (weather) {
    $("day").max = weather.dates.length - 1;
    state.day = Math.max(0, weather.dates.indexOf(weather.today));
    $("day").value = state.day;
  } else {
    $("day").hidden = true;
    state.mode = "habitat";
  }
  palette = buildPalette();
  $("ramp").style.background = `linear-gradient(to right, ${RAMP.map(([v, c]) => `rgb(${c.join(",")}) ${v * 100}%`).join(", ")})`;
  initMap();
  wireUI();
  setMode(state.mode);
  buildDayStrip();
  updateDayUI();
  fillAbout();
  $("loading").hidden = true;
  if (!store.get("safety-ok", false)) $("safety").hidden = false;
}

function setMode(mode) {
  state.mode = mode;
  document.querySelectorAll(".segmented button").forEach((b) => b.setAttribute("aria-checked", String(b.dataset.mode === mode)));
  store.set("mode", mode);
  render();
}

function wireUI() {
  $("species").addEventListener("change", (ev) => {
    state.sp = Number(ev.target.value);
    store.set("species", D.species[state.sp].key);
    render(); buildDayStrip(); updateDayUI();
    if (!$("details").hidden) $("details").hidden = true;
  });
  document.querySelectorAll(".segmented button").forEach((b) => b.addEventListener("click", () => setMode(b.dataset.mode)));
  let pending = 0;
  $("day").addEventListener("input", (ev) => {
    state.day = Number(ev.target.value);
    updateDayUI();
    cancelAnimationFrame(pending);
    pending = requestAnimationFrame(render);
  });
  $("opacity").value = state.opacity;
  $("opacity").addEventListener("input", (ev) => { state.opacity = Number(ev.target.value); overlay.setOpacity(state.opacity); });
  document.querySelectorAll("[data-close]").forEach((b) => b.addEventListener("click", () => { $(b.dataset.close).hidden = true; }));
  $("about-btn").addEventListener("click", () => { $("about").hidden = false; });
  $("safety-ok").addEventListener("click", () => { $("safety").hidden = true; store.set("safety-ok", true); });
}

init().catch((err) => {
  console.error(err);
  $("loading").textContent = "Impossible de charger les données : " + err.message;
});

if ("serviceWorker" in navigator && (location.protocol === "https:" || location.hostname === "localhost" || location.hostname === "127.0.0.1")) {
  navigator.serviceWorker.register("sw.js").catch(() => { /* optional */ });
}
