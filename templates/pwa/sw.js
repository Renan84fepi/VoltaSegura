{% load static %}"use strict";
// Service worker do VoltaSegura (RNF01/RNF02).
// - Páginas: sempre da rede; sem conexão, mostra a página offline.
// - Arquivos estáticos: do cache, atualizados em segundo plano.
// - API, admin e documentos: nunca guardados (dados pessoais e de tempo real).
const CACHE = "voltasegura-{{ versao }}";
const OFFLINE = "{% url 'pwa:offline' %}";
const ESSENCIAIS = [
  OFFLINE,
  "{% static 'corridas/comum.js' %}?v={{ versao }}",
  "{% static 'corridas/cliente.js' %}?v={{ versao }}",
  "{% static 'corridas/motorista.js' %}?v={{ versao }}",
  "{% static 'pwa/pwa.js' %}?v={{ versao }}",
  "{% static 'pwa/offline.js' %}?v={{ versao }}",
  "{% static 'pwa/tema.css' %}?v={{ versao }}",
  "{% static 'pwa/icone-192.png' %}",
];
const EXTERNOS = ["https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/css/bootstrap.min.css"];
const NUNCA_GUARDAR = ["/api/", "/admin/", "/motorista/arquivo/"];

self.addEventListener("install", (evento) => {
  evento.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    await cache.addAll(ESSENCIAIS);
    // O CDN pode estar fora do ar: sem ele a página offline ainda funciona (tem CSS próprio).
    await Promise.all(EXTERNOS.map((url) => cache.add(url).catch(() => null)));
    await self.skipWaiting();
  })());
});

self.addEventListener("activate", (evento) => {
  evento.waitUntil((async () => {
    const nomes = await caches.keys();
    await Promise.all(nomes.filter((n) => n.startsWith("voltasegura-") && n !== CACHE).map((n) => caches.delete(n)));
    await self.clients.claim();
  })());
});

async function doCacheAtualizando(pedido) {
  const cache = await caches.open(CACHE);
  const guardado = await cache.match(pedido);
  const rede = fetch(pedido)
    .then((resposta) => {
      if (resposta.ok) cache.put(pedido, resposta.clone());
      return resposta;
    })
    .catch(() => guardado);
  return guardado || rede;
}

self.addEventListener("fetch", (evento) => {
  const pedido = evento.request;
  if (pedido.method !== "GET") return;
  const url = new URL(pedido.url);
  const mesmoSite = url.origin === self.location.origin;
  if (mesmoSite && NUNCA_GUARDAR.some((prefixo) => url.pathname.startsWith(prefixo))) return;

  if (pedido.mode === "navigate") {
    evento.respondWith(fetch(pedido).catch(async () => (await caches.match(OFFLINE)) || Response.error()));
    return;
  }
  if ((mesmoSite && url.pathname.startsWith("{% get_static_prefix %}")) || EXTERNOS.includes(pedido.url)) {
    evento.respondWith(doCacheAtualizando(pedido));
  }
});
