const CACHE='bot-avisos-v2';
// FIX BUG-8.2: Cachear rotas locais úteis (removida URL cross-origin do Google Fonts)
const STATIC=['/','/login','/manifest.json','/icon-192.png','/icon-512.png'];

self.addEventListener('install',e=>{
  // FIX BUG-8.2: Agora usa o array STATIC corretamente
  e.waitUntil(caches.open(CACHE).then(c=>c.addAll(STATIC)).catch(()=>{}));
  self.skipWaiting();
});
self.addEventListener('activate',e=>{
  e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==CACHE).map(k=>caches.delete(k)))));
  self.clients.claim();
});
self.addEventListener('fetch',e=>{
  // API calls: sempre rede
  if(e.request.url.includes('/api/')) return;
  e.respondWith(fetch(e.request).catch(()=>caches.match(e.request)));
});
