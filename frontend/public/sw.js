// Service worker mínimo: guarda la app para que abra sin señal.
// Los datos (/api) siempre van a la red; los registros sin señal los maneja la cola de la app.
const CACHE = "verdad-contable-v1";

self.addEventListener("install", (evento) => {
  evento.waitUntil(caches.open(CACHE).then((c) => c.addAll(["/", "/manifest.webmanifest", "/icono.svg"])));
  self.skipWaiting();
});

self.addEventListener("activate", (evento) => {
  evento.waitUntil(
    caches.keys().then((claves) => Promise.all(claves.filter((k) => k !== CACHE).map((k) => caches.delete(k)))),
  );
  self.clients.claim();
});

self.addEventListener("fetch", (evento) => {
  const url = new URL(evento.request.url);
  if (evento.request.method !== "GET" || url.origin !== location.origin || url.pathname.startsWith("/api/")) return;
  // Red primero; si no hay señal, lo guardado.
  evento.respondWith(
    fetch(evento.request)
      .then((respuesta) => {
        const copia = respuesta.clone();
        caches.open(CACHE).then((c) => c.put(evento.request, copia));
        return respuesta;
      })
      .catch(() =>
        caches.match(evento.request).then((r) => r || (evento.request.mode === "navigate" ? caches.match("/") : r)),
      ),
  );
});
