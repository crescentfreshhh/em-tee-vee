// em tee vee service worker
// Caches the app shell so the player launches instantly on the tablet.
// API calls and video streams always go to the network (never cached).
const CACHE = "mtv-shell-v1";
const SHELL = [
  "/",
  "/player",
  "/library",
  "/static/style.css",
  "/static/library.css",
  "/static/profiles.css",
  "/static/player.js",
  "/static/library.js",
  "/static/profiles.js",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
  "/manifest.webmanifest",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);

  // Never intercept video streams or API/auth traffic.
  if (url.pathname.startsWith("/videos/") ||
      url.pathname.startsWith("/api/") ||
      url.pathname.startsWith("/auth/")) {
    return;
  }

  // App shell: cache-first, falling back to network and updating the cache.
  event.respondWith(
    caches.match(event.request).then((cached) => {
      const fetched = fetch(event.request).then((resp) => {
        if (resp.ok && event.request.method === "GET") {
          const copy = resp.clone();
          caches.open(CACHE).then((c) => c.put(event.request, copy));
        }
        return resp;
      }).catch(() => cached);
      return cached || fetched;
    })
  );
});
