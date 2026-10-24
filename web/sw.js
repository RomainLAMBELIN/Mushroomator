// Offline support: every file of the site is kept so that the map remains usable in the forest without network,
// as well as the map tiles already viewed (up to MAX_TILES).
// VERSION and FILES are written by the build (mushroomator/site.py): a new version of the application or of its data
// is downloaded in full by the browser in the background, then replaces the previous one at the next opening.
const VERSION = "mushroomator-dev";
const FILES = ["./"];
const TILES = "mushroomator-tiles";
const MAX_TILES = 1500;
const NETWORK_TIMEOUT_MS = 4000;     // weak signal: answer with the stored weather after this delay
// Map tiles (IGN WMTS, OpenTopoMap, OpenStreetMap); the IGN place search on the same host is left to the network.
const isTile = (url) => (url.hostname === "data.geopf.fr" ? url.pathname.startsWith("/wmts")
  : url.hostname.endsWith("tile.opentopomap.org") || url.hostname.endsWith("tile.openstreetmap.org"));

self.addEventListener("install", (event) => {
  // "no-cache": revalidated with the server, so unchanged files just loaded by the page are not downloaded again
  event.waitUntil(caches.open(VERSION)
    .then((c) => c.addAll(FILES.map((f) => new Request(f, { cache: "no-cache" }))))
    .then(() => self.skipWaiting()));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(caches.keys()
    .then((keys) => Promise.all(keys.filter((k) => k !== VERSION && k !== TILES).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});

async function fetchAndKeep(request) {
  const response = await fetch(request);
  if (response.ok) await (await caches.open(VERSION)).put(request, response.clone());
  return response;
}

// The weather changes every day: from the network when it answers in time, otherwise the last one stored.
async function networkFirst(event) {
  const network = fetchAndKeep(event.request);
  event.waitUntil(network.catch(() => null));        // keeps downloading after a timeout, for the next opening
  const cached = await caches.match(event.request);
  if (!cached) return network;
  const late = new Promise((resolve) => setTimeout(() => resolve(cached), NETWORK_TIMEOUT_MS));
  return Promise.race([network.catch(() => cached), late]);
}

// Application and layers: the stored version, consistent with each other until the next version is installed.
async function cacheFirst(request) {
  const cached = await caches.match(request, { ignoreSearch: request.mode === "navigate" });
  return cached || fetchAndKeep(request);
}

// Tiles: only those already stored are answered by this worker (at once, even offline). The others are loaded by the
// browser itself, which cancels them when the map moves on; the page then hands over the tiles it has displayed and
// they are copied from the HTTP cache, without a new download.
let tileIndex = null;                    // URLs of the stored tiles, so that the fetch handler can decide at once
caches.open(TILES).then((c) => c.keys()).then((keys) => { tileIndex = new Set(keys.map((k) => k.url)); });

async function storedTile(request) {
  return (await (await caches.open(TILES)).match(request)) || fetch(request);
}

async function keepTile(url) {
  const response = await fetch(new Request(url, { mode: "cors", credentials: "omit", cache: "force-cache" }));
  if (!response.ok || response.type !== "cors") return;
  await (await caches.open(TILES)).put(url, response);
  tileIndex?.add(url);
}

async function trimTiles() {             // oldest tiles beyond MAX_TILES are removed
  const cache = await caches.open(TILES);
  const keys = await cache.keys();
  await Promise.all(keys.slice(0, Math.max(0, keys.length - MAX_TILES)).map((k) => {
    tileIndex?.delete(k.url);
    return cache.delete(k);
  }));
}

self.addEventListener("message", (event) => {
  const urls = (event.data?.tiles || []).filter((u) => isTile(new URL(u)) && !tileIndex?.has(u));
  if (urls.length) event.waitUntil(Promise.all(urls.map((u) => keepTile(u).catch(() => null))).then(trimTiles));
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (event.request.method !== "GET") return;
  if (isTile(url)) {
    if (!tileIndex || tileIndex.has(event.request.url)) event.respondWith(storedTile(event.request));
  } else if (url.origin === location.origin && url.pathname.endsWith("/weather.json")) {
    event.respondWith(networkFirst(event));
  } else if (url.origin === location.origin) {
    event.respondWith(cacheFirst(event.request));
  }
});
