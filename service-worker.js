const CACHE_NAME = "memory-ai-v4";

self.addEventListener("install", (event) => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((names) =>
      Promise.all(names.map((n) => n !== CACHE_NAME && caches.delete(n)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  if (event.request.url.includes("/chat") || 
      event.request.url.includes("/chats") ||
      event.request.url.includes("/messages") ||
      event.request.url.includes("/delete-chat") ||
      event.request.url.includes("/extract-info")) {
    return;
  }
  event.respondWith(fetch(event.request).catch(() => caches.match(event.request)));
});
