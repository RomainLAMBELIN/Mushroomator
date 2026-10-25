import * as M from "./model.js";

const $ = (id) => document.getElementById(id);
// Sequential "heat" ramp (ColorBrewer YlOrRd): light = low, dark red = high.
const RAMP = [[0, [255, 255, 178]], [0.25, [254, 204, 92]], [0.5, [253, 141, 60]], [0.75, [240, 59, 32]], [1, [189, 0, 38]]];
const MODES = {
  indice: "Indice = habitat × conditions météo (100 : habitat idéal et journée parmi les meilleures de la saison).",
  habitat: "Habitat : arbres-hôtes, altitude et pH du sol (indépendant de la météo).",
  meteo: "Conditions : météo des semaines précédentes comparée aux jours habituels de la saison (là où l'habitat convient).",
  semblables: "Semblables : endroits qui ressemblent à vos coins productifs (même peuplement, altitude et sol proches, 25 km autour) × conditions du jour.",
};
const DAY_FMT = new Intl.DateTimeFormat("fr-FR", { weekday: "long", day: "numeric", month: "long" });
const SHORT_FMT = new Intl.DateTimeFormat("fr-FR", { weekday: "short", day: "numeric" });
const UPDATE_FMT = new Intl.DateTimeFormat("fr-FR", { day: "numeric", month: "short" });
const LIST_FMT = new Intl.DateTimeFormat("fr-FR", { day: "numeric", month: "short", year: "numeric" });

const state = { mode: "indice", sp: 0, day: 0, opacity: 0.8 };
let D;                 // loaded data
let map, overlay, canvas, ctx, image, pixels, palette, marker;

const store = {
  get(k, def) { try { const v = localStorage.getItem("mushroomator." + k); return v === null ? def : JSON.parse(v); } catch { return def; } },
  set(k, v) { try { localStorage.setItem("mushroomator." + k, JSON.stringify(v)); } catch { /* private mode */ } },
};

// Date of the phone (YYYY-MM-DD): the stored map may be opened offline, days after its last update.
function localToday() {
  const d = new Date();
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
}
const isReplay = () => D.weather.source.startsWith("Rejeu");
const refDay = () => (isReplay() ? D.weather.today : localToday());     // the day called "aujourd'hui"

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
  const view = store.get("view", null);
  if (view && [view.lat, view.lng, view.zoom].every(Number.isFinite)) map.setView([view.lat, view.lng], view.zoom);
  else map.fitBounds([[s, w], [n, e]]);
  map.on("moveend", () => {
    const c = map.getCenter();
    store.set("view", { lat: +c.lat.toFixed(5), lng: +c.lng.toFixed(5), zoom: map.getZoom() });
  });
  const bases = baseLayers();
  Object.values(bases).forEach((layer) => layer.on("tileload", (ev) => keepTile(ev.tile.src)));
  const chosen = store.get("base", "Plan IGN");
  (bases[chosen] || bases["Plan IGN"]).addTo(map);
  L.control.zoom({ position: "topright" }).addTo(map);
  notebook.layer = L.layerGroup().addTo(map);
  L.control.layers(bases, { "Mes sorties": notebook.layer }, { position: "topright" }).addTo(map);
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
  const Notebook = L.Control.extend({
    options: { position: "topright" },
    onAdd() {
      const b = L.DomUtil.create("button", "carnet-btn leaflet-bar");
      b.type = "button"; b.title = "Carnet de sorties"; b.setAttribute("aria-label", "Carnet de sorties"); b.textContent = "📓";
      L.DomEvent.on(b, "click", (ev) => { L.DomEvent.stop(ev); openNotebook(); });
      return b;
    },
  });
  new Notebook().addTo(map);
  map.on("locationfound", (ev) => {
    lastFix = ev.latlng;
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
  map.on("click", (ev) => {
    if (Date.now() - search.closedAt <= 500) return;
    if (!$("carnet").hidden) setEntryPlace(ev.latlng); else showDetails(ev.latlng);
  });
}

// ------------------------------------------------------------------ place search ----
// IGN Géoplateforme autocompletion (free, no key, Licence Ouverte): communes, hamlets, summits, passes, woods, addresses.
const GEOCODER = "https://data.geopf.fr/geocodage/completion/";
const KIND_LABELS = { administratif: "commune", municipality: "commune", street: "voie", housenumber: "adresse", locality: "lieu-dit" };
const search = { places: [], shownFor: "", active: -1, timer: 0, controller: null, submitted: false, closedAt: 0 };
let placeMarker;

// "45.325, 5.764", "45.325 5.764" or "45,325 5,764": GPS coordinates, which also work offline.
function parseCoordinates(text) {
  const m = text.match(/^(-?\d{1,2}(?:\.\d+)?)\s*[,;\s]\s*(-?\d{1,3}(?:\.\d+)?)$/)
    || text.match(/^(-?\d{1,2}(?:,\d+)?)\s*[;\s]\s*(-?\d{1,3}(?:,\d+)?)$/);
  if (!m) return null;
  let [lat, lon] = [m[1], m[2]].map((v) => Number(v.replace(",", ".")));
  if (lat < lon) [lat, lon] = [lon, lat];         // longitude first: in this region latitudes are the larger numbers
  return { name: `${lat.toFixed(5)}, ${lon.toFixed(5)}`, detail: "coordonnées GPS", lat, lon, zoom: 15, rank: 0 };
}

// Words without accents; "st"/"ste" as commonly typed for "saint"/"sainte"; short words (de, la, du…) ignored.
const fold = (t) => t.normalize("NFD").replace(/\p{M}/gu, "").toLowerCase();
const words = (t) => fold(t).split(/[^a-z0-9]+/).filter(Boolean);
const queryWords = (t) => words(t).map((w) => ({ st: "saint", ste: "sainte" })[w] ?? w)
  .filter((w) => w.length > 2 || /^\d+$/.test(w));

function placeFromResult(r, address, query) {
  const name = r.fulltext.split(",")[0].trim();
  const tokens = words(`${name} ${r.city ?? ""}`);
  // 0: every typed word is a word of the name or commune, 1: the start of one (word being typed), 2: otherwise
  const match = query.every((w) => tokens.includes(w)) ? 0 : query.every((w) => tokens.some((t) => t.startsWith(w))) ? 1 : 2;
  const types = r.poiType || [];
  const commune = r.kind === "administratif" || r.kind === "municipality";
  const natural = types.includes("élément topographique ou forestier") || types.includes("hydrographie");
  const inhabited = types.includes("zone d'habitation") || r.kind === "locality";
  const street = r.kind === "street" || r.kind === "housenumber";
  // communes, then summits, passes, woods and lakes, then hamlets, then streets (first when a number is typed), then the rest
  const rank = commune ? 0 : natural ? 1 : inhabited ? 2 : street ? (address ? 0 : 3) : 4;
  const zoom = commune ? 13 : natural ? 14 : r.kind === "housenumber" ? 17 : street ? 16 : 15;
  const detail = (KIND_LABELS[r.kind] ?? r.kind ?? "lieu") + (r.city && r.city !== name ? ` · ${r.city}` : "")
    + (r.zipcode ? ` (${r.zipcode.slice(0, 2)})` : "");
  return { name, detail, lat: r.y, lon: r.x, zoom, rank, match, key: `${name.toLowerCase()}|${r.zipcode ?? ""}` };
}

async function findPlaces(text, signal) {
  const [w, s, e, n] = D.grid.bounds;
  const inRegion = (p) => p.lon >= w && p.lon <= e && p.lat >= s && p.lat <= n;
  const coords = parseCoordinates(text);
  if (coords) return [coords].filter(inRegion);
  const params = new URLSearchParams({ text, type: "PositionOfInterest,StreetAddress", maximumResponses: "15" });
  if (D.layersMeta.departements?.length) params.set("terr", D.layersMeta.departements.join(","));
  const r = await fetch(`${GEOCODER}?${params}`, { signal });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  const address = /^\d/.test(text), query = queryWords(text), seen = new Set();
  return ((await r.json()).results || []).filter((x) => x.fulltext && Number.isFinite(x.x) && Number.isFinite(x.y))
    .map((x) => placeFromResult(x, address, query)).filter(inRegion)
    // best match of the typed words first, then by kind; stable: keeps the geocoder's order within a group
    .sort((a, b) => a.match - b.match || a.rank - b.rank)
    .filter((p) => !seen.has(p.key) && seen.add(p.key)).slice(0, 8);
}

function showPlaces(places, note = "") {
  const list = $("search-results"), input = $("search");
  search.places = places;
  search.active = -1;
  list.replaceChildren(...places.map((p, k) => {
    const li = document.createElement("li");
    li.id = `place-${k}`;
    li.setAttribute("role", "option");
    li.setAttribute("aria-selected", "false");
    li.append(Object.assign(document.createElement("strong"), { textContent: p.name }),
      Object.assign(document.createElement("small"), { textContent: p.detail }));
    li.addEventListener("click", () => goToPlace(p));
    return li;
  }));
  if (note) list.append(Object.assign(document.createElement("li"), { className: "note", textContent: note }));
  const open = places.length > 0 || note !== "";
  list.hidden = !open;
  $("top").classList.toggle("searching", open);
  input.setAttribute("aria-expanded", String(open));
  input.removeAttribute("aria-activedescendant");
}

function closePlaces() {
  if ($("search-results").hidden) return false;
  showPlaces([]);
  return true;
}

function setActivePlace(k) {
  const items = [...$("search-results").querySelectorAll("li[role=option]")];
  if (!items.length) return;
  search.active = (k + items.length) % items.length;
  items.forEach((li, j) => li.setAttribute("aria-selected", String(j === search.active)));
  $("search").setAttribute("aria-activedescendant", items[search.active].id);
  items[search.active].scrollIntoView({ block: "nearest" });
}

async function runSearch() {
  const text = $("search").value.trim();
  search.controller?.abort();
  if (text.length < 3 && !parseCoordinates(text)) { search.submitted = false; showPlaces([]); return; }
  const controller = search.controller = new AbortController();
  try {
    const places = await findPlaces(text, controller.signal);
    if (controller !== search.controller) return;              // a newer search has started
    search.shownFor = text;
    showPlaces(places, places.length ? "" : "Rien trouvé dans la zone couverte.");
    if (search.submitted && places.length) goToPlace(places[0]);
  } catch (err) {
    if (err.name === "AbortError") return;
    showPlaces([], "Recherche impossible sans réseau. Les coordonnées GPS (par exemple 45.325, 5.764) fonctionnent hors ligne.");
  } finally {
    if (controller === search.controller) search.submitted = false;
  }
}

function goToPlace(p) {
  closePlaces();
  $("search").value = p.name;
  $("search").blur();                                           // closes the phone keyboard
  $("details").hidden = true;
  if (placeMarker) placeMarker.remove();
  // not interactive: touching the pin shows the details of the place, as anywhere on the map
  placeMarker = L.marker([p.lat, p.lon], { interactive: false }).addTo(map)
    .bindTooltip(p.name, { permanent: true, direction: "right", className: "place-label" });
  map.setView([p.lat, p.lon], p.zoom);
}

function initSearch() {
  const input = $("search");
  input.addEventListener("input", () => {
    if (!input.value && placeMarker) placeMarker.remove();
    search.controller?.abort();                    // an answer for the previous text must not show up any more
    clearTimeout(search.timer);
    search.timer = setTimeout(runSearch, 250);
  });
  input.addEventListener("focus", () => { if (input.value.trim()) runSearch(); });
  input.addEventListener("keydown", (ev) => {
    if (ev.key === "ArrowDown") { ev.preventDefault(); setActivePlace(search.active + 1); }
    else if (ev.key === "ArrowUp") { ev.preventDefault(); setActivePlace(search.active < 0 ? -1 : search.active - 1); }
    else if (ev.key === "Escape") closePlaces();
  });
  $("search-form").addEventListener("submit", (ev) => {
    ev.preventDefault();
    const text = input.value.trim();
    if (search.places.length && search.shownFor === text) goToPlace(search.places[Math.max(0, search.active)]);
    else { clearTimeout(search.timer); search.submitted = true; runSearch(); }
  });
  // touching the map closes the list (without also opening the details of that point)
  document.addEventListener("pointerdown", (ev) => {
    if (!$("top").contains(ev.target) && closePlaces()) search.closedAt = Date.now();
  });
}

// --------------------------------------------------------------------- notebook ----
// Outings noted on this phone only (local storage), exportable as a file; nothing is sent anywhere. The "rien trouvé"
// outings are the absences that public data lack: they will tell how reliable the map is for its user.
const notebook = { entries: store.get("carnet", []), layer: null, markers: new Map(), place: null, pin: null, res: "trouve" };
const RES_TEXT = { trouve: "Trouvé", rien: "Rien trouvé" };
const QTE_TEXT = { quelques: "quelques-uns", panier: "un panier", beaucoup: "beaucoup" };
const NO_SPOT = "Notez dans le carnet (📓) au moins un endroit en forêt où vous avez trouvé cette espèce.";
let lastFix = null, simCache = { key: "", grid: null, spots: 0 }, toastTimer = 0;

function toast(text) {
  const t = $("toast");
  t.textContent = text;
  t.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { t.hidden = true; }, 3500);
}

const speciesByKey = (key) => D.species.find((s) => s.key === key);
const newId = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 6);

// Resemblance to the places where the species was found, recomputed only when those places change.
function similarity(sp) {
  const spots = notebook.entries.filter((e) => e.sp === sp.key && e.res === "trouve");
  const key = sp.key + "|" + spots.map((e) => e.id).join(",");
  if (simCache.key !== key) {
    const grid = M.similarityGrid(D.layers, spots);
    simCache = { key, grid, spots: grid.some((v) => v > 0) ? spots.length : 0 };
  }
  return simCache;
}

// Index, habitat and conditions at that place on that day, when the weather of that day is loaded.
function entryIndex(sp, lat, lon, date) {
  const k = D.weather ? D.weather.dates.indexOf(date) : -1;
  const rc = M.pixelOf(D.grid, lat, lon);
  if (k < 0 || !rc || !D.layers.host[rc[0] * D.grid.nx + rc[1]]) return { indice: null, habitat: null, conditions: null };
  const ex = M.explain(sp, D.layers, M.coarseFields(sp, D.weather, k), D.wts, rc[0], rc[1]);
  return { indice: +ex.index.toFixed(3), habitat: +ex.habitat.H.toFixed(3), conditions: +ex.q.toFixed(3) };
}

function saveNotebook() {
  store.set("carnet", notebook.entries);
  drawNotebook();
  if (state.mode === "semblables") render();
}

function drawNotebook() {
  notebook.layer.clearLayers();
  notebook.markers.clear();
  for (const e of notebook.entries) {
    const found = e.res === "trouve";
    const m = L.circleMarker([e.lat, e.lon], { radius: 7, weight: 2, color: found ? "#ffffff" : "#5f5f5f",
                                                fillColor: found ? "#2e7d32" : "#ffffff", fillOpacity: 1 });
    m.bindPopup(() => entryPopup(e)).addTo(notebook.layer);
    notebook.markers.set(e.id, m);
  }
  fillNotebookPanel();
}

function entryPopup(e) {
  const div = document.createElement("div");
  const sp = speciesByKey(e.sp);
  const lines = [`${sp ? sp.nom : e.sp} · ${DAY_FMT.format(new Date(e.date + "T12:00:00"))}`,
    RES_TEXT[e.res] + (e.res === "trouve" && e.qte ? ` (${QTE_TEXT[e.qte] ?? e.qte})` : ""),
    e.indice != null ? `Indice ce jour-là : ${Math.round(e.indice * 100)}/100` : "", e.note || ""].filter(Boolean);
  lines.forEach((t, i) => div.append(Object.assign(document.createElement(i ? "div" : "strong"), { textContent: t })));
  const del = Object.assign(document.createElement("button"), { type: "button", className: "chip", textContent: "Supprimer" });
  del.style.marginTop = "8px";
  del.addEventListener("click", () => {
    if (!confirm("Supprimer cette sortie du carnet ?")) return;
    notebook.entries = notebook.entries.filter((x) => x.id !== e.id);
    map.closePopup();
    saveNotebook();
  });
  div.append(del);
  return div;
}

function notebookStats() {
  const E = notebook.entries;
  if (!E.length) return ["Notez aussi les sorties où vous ne trouvez rien : ce sont elles qui permettront de mesurer la fiabilité de la carte pour vous."];
  const found = E.filter((e) => e.res === "trouve").length;
  const lines = [`${E.length} sortie${E.length > 1 ? "s" : ""}, dont ${found} fructueuse${found > 1 ? "s" : ""}.`];
  const bySp = {};
  for (const e of E) {
    const t = (bySp[e.sp] ??= [0, 0]);
    t[0]++;
    if (e.res === "trouve") t[1]++;
  }
  lines.push(Object.entries(bySp).map(([k, [n, f]]) => `${speciesByKey(k)?.nom ?? k} : ${f} sur ${n}`).join(" · "));
  const scored = E.filter((e) => e.indice != null);
  if (scored.length >= 10) {
    lines.push("Réussite selon l'indice du jour : " + [[0, 0.3, "moins de 30"], [0.3, 0.6, "30 à 60"], [0.6, 2, "60 et plus"]].map(([a, b, label]) => {
      const g = scored.filter((e) => e.indice >= a && e.indice < b);
      return `${label} : ${g.filter((e) => e.res === "trouve").length} sur ${g.length}`;
    }).join(" · "));
  } else {
    const n = 10 - scored.length;
    lines.push(`Encore ${n} sortie${n > 1 ? "s" : ""} notée${n > 1 ? "s" : ""} le jour même pour voir la réussite selon l'indice.`);
  }
  return lines;
}

function fillNotebookPanel() {
  $("carnet-stats").replaceChildren(...notebookStats().map((t) => Object.assign(document.createElement("p"), { textContent: t })));
  const sorted = [...notebook.entries].sort((a, b) => (b.date + b.cree).localeCompare(a.date + a.cree));
  const items = sorted.slice(0, 100).map((e) => {
    const li = document.createElement("li");
    const found = e.res === "trouve";
    li.append(Object.assign(document.createElement("span"), { className: found ? "ok" : "ko", textContent: found ? "✓ " : "✗ " }),
      `${LIST_FMT.format(new Date(e.date + "T12:00:00"))} · ${speciesByKey(e.sp)?.nom ?? e.sp}${e.note ? ` · ${e.note}` : ""}`);
    li.addEventListener("click", () => {
      map.setView([e.lat, e.lon], Math.max(map.getZoom(), 15));
      notebook.markers.get(e.id)?.openPopup();
    });
    return li;
  });
  $("carnet-list").replaceChildren(...(items.length ? items : [Object.assign(document.createElement("li"), { textContent: "Aucune sortie notée pour l'instant." })]));
}

function openNotebook() {
  $("details").hidden = true;
  $("about").hidden = true;
  $("carnet").hidden = false;
  const select = $("carnet-sp");
  if (!select.options.length) D.species.forEach((s) => select.add(new Option(s.nom, s.key)));
  select.value = D.species[state.sp].key;
  $("carnet-date").value = localToday();
  if (!notebook.place && lastFix) setEntryPlace(lastFix);
  fillNotebookPanel();
}

function setEntryPlace(latlng) {
  notebook.place = L.latLng(latlng);
  $("carnet-lieu").textContent = `${notebook.place.lat.toFixed(5)}, ${notebook.place.lng.toFixed(5)}`;
  if (notebook.pin) notebook.pin.setLatLng(notebook.place);
  else notebook.pin = L.marker(notebook.place, { interactive: false, opacity: 0.85 }).addTo(map);
}

function setResult(res) {
  notebook.res = res;
  document.querySelectorAll("#carnet-res button").forEach((b) => b.setAttribute("aria-checked", String(b.dataset.res === res)));
  $("carnet-qte-field").hidden = res !== "trouve";
}

function saveEntry(ev) {
  ev.preventDefault();
  if (!notebook.place) { toast("Touchez la carte ou utilisez votre position pour placer la sortie."); return; }
  const sp = speciesByKey($("carnet-sp").value);
  const date = $("carnet-date").value || localToday();
  const { lat, lng } = notebook.place;
  notebook.entries.push({ id: newId(), date, cree: new Date().toISOString(), lat: +lat.toFixed(6), lon: +lng.toFixed(6), sp: sp.key,
                          res: notebook.res, qte: notebook.res === "trouve" ? $("carnet-qte").value : null,
                          note: $("carnet-note").value.trim().slice(0, 200), ...entryIndex(sp, lat, lng, date) });
  saveNotebook();
  $("carnet-note").value = "";
  toast(notebook.res === "trouve" ? "Sortie enregistrée : bravo !" : "Sortie enregistrée.");
}

function exportNotebook() {
  const data = { application: "Mushroomator", version: 1, exporte: new Date().toISOString(), sorties: notebook.entries };
  const a = Object.assign(document.createElement("a"), {
    href: URL.createObjectURL(new Blob([JSON.stringify(data, null, 1)], { type: "application/json" })),
    download: `carnet-mushroomator-${localToday()}.json` });
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 2000);
}

async function importNotebook(ev) {
  const file = ev.target.files[0];
  ev.target.value = "";
  if (!file) return;
  try {
    const data = JSON.parse(await file.text());
    const known = new Set(notebook.entries.map((e) => e.id));
    const num = (v) => (Number.isFinite(v) ? v : null);
    const rows = (Array.isArray(data) ? data : data.sorties || []).filter((e) => e && Number.isFinite(e.lat) && Number.isFinite(e.lon)
      && (e.res === "trouve" || e.res === "rien") && typeof e.sp === "string" && /^\d{4}-\d{2}-\d{2}$/.test(e.date || "")
      && !known.has(String(e.id)));
    notebook.entries.push(...rows.map((e) => ({ id: String(e.id ?? newId()), date: e.date, cree: String(e.cree ?? new Date().toISOString()),
      lat: e.lat, lon: e.lon, sp: e.sp, res: e.res, qte: QTE_TEXT[e.qte] ? e.qte : null, note: String(e.note ?? "").slice(0, 200),
      indice: num(e.indice), habitat: num(e.habitat), conditions: num(e.conditions) })));
    saveNotebook();
    toast(`${rows.length} sortie${rows.length > 1 ? "s" : ""} importée${rows.length > 1 ? "s" : ""}.`);
  } catch {
    toast("Fichier illisible.");
  }
}

function wireNotebook() {
  $("carnet-form").addEventListener("submit", saveEntry);
  document.querySelectorAll("#carnet-res button").forEach((b) => b.addEventListener("click", () => setResult(b.dataset.res)));
  $("carnet-gps").addEventListener("click", () => {
    if (!navigator.geolocation) { toast("Position indisponible."); return; }
    toast("Recherche de votre position…");
    navigator.geolocation.getCurrentPosition((pos) => {
      lastFix = L.latLng(pos.coords.latitude, pos.coords.longitude);
      setEntryPlace(lastFix);
      map.setView(lastFix, Math.max(map.getZoom(), 15));
    }, () => toast("Position indisponible."), { enableHighAccuracy: true, timeout: 15000, maximumAge: 60000 });
  });
  document.querySelector('[data-close="carnet"]').addEventListener("click", () => {
    notebook.pin?.remove();
    notebook.pin = notebook.place = null;
    $("carnet-lieu").textContent = "aucun lieu choisi";
  });
  $("carnet-export").addEventListener("click", exportNotebook);
  $("carnet-import").addEventListener("change", importNotebook);
}

function render() {
  const sp = D.species[state.sp];
  const fields = state.mode === "habitat" || !D.weather ? null : M.coarseFields(sp, D.weather, state.day);
  const mode = state.mode === "semblables" ? "semblables" : fields ? state.mode : "habitat";
  let values, note = D.weather ? "" : " Météo indisponible : seul l'habitat est affiché.";
  if (mode === "semblables") {
    const sim = similarity(sp);
    const q = fields ? M.computeGrid(sp, D.layers, fields, D.wts, "meteo", 0) : null;
    values = q ? sim.grid.map((v, p) => v * q[p]) : sim.grid;
    if (!sim.spots) note = " " + NO_SPOT;
  } else {
    values = M.computeGrid(sp, D.layers, fields, D.wts, mode);
  }
  for (let p = 0; p < values.length; p++) {
    const v = values[p];
    pixels[p] = v === v ? palette[Math.max(0, Math.min(255, Math.round(v * 255)))] : 0;
  }
  ctx.putImageData(image, 0, 0);
  $("legend-text").textContent = MODES[mode] + note;
}

function dayLabel(iso) {
  const diff = Math.round((new Date(iso) - new Date(refDay())) / 86400000);
  const names = { "-1": "Hier", 0: "Aujourd'hui", 1: "Demain" };
  return names[diff] ?? DAY_FMT.format(new Date(iso + "T12:00:00"));
}

function updateDayUI() {
  if (!D.weather) { $("day-label").textContent = "Habitat"; $("day-note").textContent = ""; return; }
  const iso = D.weather.dates[state.day];
  const diff = Math.round((new Date(iso) - new Date(D.weather.today)) / 86400000);
  const label = dayLabel(iso), full = DAY_FMT.format(new Date(iso + "T12:00:00"));
  $("day-label").textContent = label === full ? full.charAt(0).toUpperCase() + full.slice(1) : `${label} · ${full}`;
  const replay = isReplay();
  const note = replay ? "rejeu d'une date passée (météo observée)"
    : diff > 0 ? "prévision" : diff < 0 ? "météo observée" : "en partie prévu";
  const stale = !replay && D.weather.today < localToday();
  $("day-note").innerHTML = note + (stale
    ? ` · <span class="stale">mise à jour du ${UPDATE_FMT.format(new Date(D.weather.today + "T12:00:00"))}</span>` : "");
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
    if (iso === refDay()) bar.classList.add("today");
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
  if (state.mode === "semblables") {
    const v = similarity(sp).grid[p];
    html += `<p class="small"><strong>Ressemblance à vos coins :</strong> ${Number.isFinite(v) ? `${Math.round(v * 100)}/100` : "hors de portée de vos coins"}</p>`;
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
    const k = weather.dates.indexOf(refDay());
    state.day = k >= 0 ? k : Math.max(0, weather.dates.indexOf(weather.today));
    $("day").value = state.day;
  } else {
    $("day").hidden = true;
    state.mode = "habitat";
  }
  palette = buildPalette();
  $("ramp").style.background = `linear-gradient(to right, ${RAMP.map(([v, c]) => `rgb(${c.join(",")}) ${v * 100}%`).join(", ")})`;
  initMap();
  drawNotebook();
  initSearch();
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
  document.querySelectorAll("#top .segmented button").forEach((b) => b.setAttribute("aria-checked", String(b.dataset.mode === mode)));
  store.set("mode", mode);
  render();
  if (mode === "semblables" && !similarity(D.species[state.sp]).spots) toast(NO_SPOT);
}

function wireUI() {
  $("species").addEventListener("change", (ev) => {
    state.sp = Number(ev.target.value);
    store.set("species", D.species[state.sp].key);
    render(); buildDayStrip(); updateDayUI();
    if (!$("details").hidden) $("details").hidden = true;
  });
  document.querySelectorAll("#top .segmented button").forEach((b) => b.addEventListener("click", () => setMode(b.dataset.mode)));
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
  wireNotebook();
}

// Offline mode, registered after the first load: the worker then copies the files from the HTTP cache
// instead of downloading them a second time.
function registerWorker() {
  if ("serviceWorker" in navigator && window.isSecureContext) navigator.serviceWorker.register("sw.js").catch(() => { /* optional */ });
}

// Tiles displayed on the map are handed over to the offline worker, which keeps a copy of them.
const shownTiles = new Set();
let tileTimer = 0;
function keepTile(src) {
  if (!("serviceWorker" in navigator) || !window.isSecureContext) return;
  shownTiles.add(src);
  clearTimeout(tileTimer);
  tileTimer = setTimeout(() => {
    const tiles = [...shownTiles];
    shownTiles.clear();
    navigator.serviceWorker.ready.then((reg) => reg.active?.postMessage({ tiles }));
  }, 1500);
}

const loadedAt = Date.now();
init().catch((err) => {
  console.error(err);
  $("loading").textContent = "Impossible de charger les données : " + err.message;
}).finally(registerWorker);

// A tab left open on the phone: back in the foreground on a later day, reload to get the day's map.
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState !== "visible" || !navigator.onLine || !D?.weather || isReplay()) return;
  if (D.weather.today < localToday() && Date.now() - loadedAt > 30 * 60000) location.reload();
});
