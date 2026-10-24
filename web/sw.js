// Offline support: every file of the site is kept so that the map remains usable in the forest without network,
// as well as the map tiles already viewed (up to MAX_TILES).
// VERSION and FILES are written by the build (mushroomator/site.py): a new version of the application or of its data
// is downloaded in full by the browser in the background, then replaces the previous one at the next opening.
const VERSION = "mushroomator-dev";
const FILES = ["./"];
const TILES = "mushroomator-tiles";
const MAX_TILES = 1500;
const NETWORK_TIMEOUT_MS = 4000;     // weak signal: answer with the stored weather after this delay
const TILE_HOSTS = ["data.geopf.fr", "tile.opentopomap.org", "tile.openstreetmap.org"];

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

// Tiles displayed before this worker was installed (first visit): stored as well, from the HTTP cache.
self.addEventListener("message", (event) => {
  const urls = (event.data?.tiles || []).filter((u) => TILE_HOSTS.some((h) => new URL(u).hostname.endsWith(h)));
  event.waitUntil(Promise.all(urls.map((u) => tile(new Request(u, { mode: "cors", credentials: "omit" })).catch(() => null))));
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (event.request.method !== "GET") return;
  if (TILE_HOSTS.some((h) => url.hostname.endsWith(h))) {
    event.respondWith(tile(event.request));
  } else if (url.origin === location.origin && url.pathname.endsWith("/weather.json")) {
    event.respondWith(networkFirst(event));
  } else if (url.origin === location.origin) {
    event.respondWith(cacheFirst(event.request));
  }
});
