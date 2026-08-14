var KAS_ISMI = "sgk-bot-site-v1";
var VARLIKLAR = ["/e-kesinti-otomasyon/"];

self.addEventListener("install", function (e) {
  e.waitUntil(caches.open(KAS_ISMI).then(function (k) { return k.addAll(VARLIKLAR); }));
  self.skipWaiting();
});

self.addEventListener("activate", function (e) {
  e.waitUntil(caches.keys().then(function (anahtarlar) {
    return Promise.all(anahtarlar.filter(function (k) { return k !== KAS_ISMI; }).map(function (k) { return caches.delete(k); }));
  }));
  self.clients.claim();
});

self.addEventListener("fetch", function (e) {
  e.respondWith(
    caches.match(e.request).then(function (yanit) {
      return yanit || fetch(e.request).then(function (agYaniti) {
        if (e.request.method === "GET" && e.request.url.indexOf("api.github.com") === -1) {
          var kopya = agYaniti.clone();
          caches.open(KAS_ISMI).then(function (k) { k.put(e.request, kopya); });
        }
        return agYaniti;
      });
    })
  );
});
