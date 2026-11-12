/*
 * Importado pelo service worker gerado (vite-plugin-pwa / Workbox, importScripts).
 * Background Sync (tag 'fiscwise-outbox'): o SW NÃO roda a engine de sync —
 * só avisa as abas abertas para rodarem syncNow (OFFLINE_SYNC.md, seção 5.6).
 * Sem aba aberta, a outbox espera a próxima abertura do app.
 */
self.addEventListener('sync', function (event) {
  if (event.tag !== 'fiscwise-outbox') return;
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function (clients) {
      clients.forEach(function (client) {
        client.postMessage({ type: 'fiscwise-sync' });
      });
    })
  );
});
