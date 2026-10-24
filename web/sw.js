// Offline support: application shell and data are cached; map tiles already viewed are kept (up to MAX_TILES)
// so that the map remains usable in the forest without network.
const VERSION = "mushroomator-v1";
const TILES = "mushroomator-tiles";
const MAX_TILES = 1500;
const SHELL = ["./", "index.html", "style.css", "app.js", "model.js", "manifest.webmanifest", "icons/icon.svg",
  "icons/icon-192.png", "vendor/leaflet/leaflet.js", "vendor/leaflet/leaflet.css"];
const TILE_HOSTS = ["data.geopf.fr", "tile.opentopomap.org", "tile.openstreetmap.org"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(VERSION).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(caches.keys()
    .then((keys) => Promise.all(keys.filter((k) => k !== VERSION && k !== TILES).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});

async function networkFirst(request) {
  const cache = await caches.open(VERSION);
  try {
    const response = await fetch(request);
    if (response.ok) cache.put(request, response.clone());
    return response;
  } catch (err) {
    const cached = await cache.match(request);
    if (cached) return cached;
    throw err;
  }
}

async function staleWhileRevalidate(request) {
  const cache = await caches.open(VERSION);
  const cached = await cache.match(request);
  const update = fetch(request).then((response) => {
    if (response.ok) cache.put(request, response.clone());
    return response;
  }).catch(() => cached);
  return cached || update;
}

async function tile(request) {
  const cache = await caches.open(TILES);
  const cached = await cache.match(request);
  if (cached) return cached;
  const response = await fetch(request);
  if (response.ok && response.type === "cors") {
    await cache.put(request, response.clone());
    const keys = await cache.keys();
    for (let i = 0; i < keys.length - MAX_TILES; i++) await cache.delete(keys[i]);
  }
  return response;
}

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (event.request.method !== "GET") return;
  if (TILE_HOSTS.some((h) => url.hostname.endsWith(h))) {
    event.respondWith(tile(event.request));
  } else if (url.origin === location.origin && url.pathname.endsWith(".json")) {
    event.respondWith(networkFirst(event.request));     // weather and models: freshest available
  } else if (url.origin === location.origin) {
    event.respondWith(staleWhileRevalidate(event.request));
  }
});
