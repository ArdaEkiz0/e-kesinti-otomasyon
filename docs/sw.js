var KAS_ISMI = "sgk-bot-site-v4";
var VARLIKLAR = [
  "/e-kesinti-otomasyon/",
  "/e-kesinti-otomasyon/index.html"
];

self.addEventListener("install", function (e) {
  e.waitUntil(
    caches.open(KAS_ISMI).then(function (k) {
      return k.addAll(VARLIKLAR).catch(function (err) {
        console.warn("SW: Precache başarısız:", err);
      });
    })
  );
});

self.addEventListener("message", function (e) {
  if (e.data && e.data.tip === "atla") {
    self.skipWaiting();
  }
});

self.addEventListener("activate", function (e) {
  e.waitUntil(
    caches.keys().then(function (anahtarlar) {
      return Promise.all(
        anahtarlar.filter(function (k) { return k !== KAS_ISMI; }).map(function (k) { return caches.delete(k); })
      );
    }).then(function () {
      return self.clients.claim();
    })
  );
});

self.addEventListener("fetch", function (e) {
  var istek = e.request;
  var apiMi = istek.url.indexOf("api.github.com") !== -1;

  if (istek.method !== "GET" || apiMi) {
    return;
  }

  if (istek.mode === "navigate") {
    e.respondWith(
      fetch(istek, { cache: "no-store" }).then(function (yanit) {
        var kopya = yanit.clone();
        caches.open(KAS_ISMI).then(function (k) { k.put(istek, kopya); });
        return yanit;
      }).catch(function () {
        return caches.match(istek);
      })
    );
    return;
  }

  e.respondWith(
    caches.match(istek).then(function (yanit) {
      var agIstek = fetch(istek).then(function (agYaniti) {
        var kopya = agYaniti.clone();
        caches.open(KAS_ISMI).then(function (k) { k.put(istek, kopya); });
        return agYaniti;
      }).catch(function () { return yanit; });
      return yanit || agIstek;
    })
  );
});
