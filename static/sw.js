// Service Worker para o Passômetro
const CACHE_NAME = 'passometro-v1.0.0';
const STATIC_CACHE = 'passometro-static-v1.0.0';
const DYNAMIC_CACHE = 'passometro-dynamic-v1.0.0';

// Arquivos para cache estático
const STATIC_FILES = [
    '/',
    '/static/css/bootstrap.min.css',
    '/static/css/adminlte.min.css',
    '/static/css/fontawesome.min.css',
    '/static/js/bootstrap.bundle.min.js',
    '/static/js/jquery.min.js',
    '/static/js/adminlte.min.js',
    '/static/js/chart.min.js',
    '/static/manifest.json',
    '/static/icons/icon-192x192.png',
    '/static/icons/icon-512x512.png'
];

// Instalação do Service Worker
self.addEventListener('install', (event) => {
    console.log('Service Worker instalando...');
    
    event.waitUntil(
        caches.open(STATIC_CACHE)
            .then((cache) => {
                console.log('Cacheando arquivos estáticos');
                return cache.addAll(STATIC_FILES);
            })
            .then(() => {
                console.log('Service Worker instalado com sucesso');
                return self.skipWaiting();
            })
            .catch((error) => {
                console.error('Erro na instalação do Service Worker:', error);
            })
    );
});

// Ativação do Service Worker
self.addEventListener('activate', (event) => {
    console.log('Service Worker ativando...');
    
    event.waitUntil(
        caches.keys()
            .then((cacheNames) => {
                return Promise.all(
                    cacheNames.map((cacheName) => {
                        if (cacheName !== STATIC_CACHE && cacheName !== DYNAMIC_CACHE) {
                            console.log('Removendo cache antigo:', cacheName);
                            return caches.delete(cacheName);
                        }
                    })
                );
            })
            .then(() => {
                console.log('Service Worker ativado');
                return self.clients.claim();
            })
    );
});

// Interceptação de requisições
self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);
    
    // Estratégia de cache para diferentes tipos de requisição
    if (request.method === 'GET') {
        // API calls - Network First
        if (url.pathname.startsWith('/api/')) {
            event.respondWith(handleApiRequest(request));
        }
        // Páginas dinâmicas - Network First
        else if (url.pathname.startsWith('/registros/') || 
                 url.pathname.startsWith('/pendencias/') ||
                 url.pathname.startsWith('/dashboard')) {
            event.respondWith(handleDynamicRequest(request));
        }
        // Arquivos estáticos - Cache First
        else if (url.pathname.startsWith('/static/')) {
            event.respondWith(handleStaticRequest(request));
        }
        // Páginas principais - Cache First
        else {
            event.respondWith(handlePageRequest(request));
        }
    }
});

// Estratégia para requisições de API
async function handleApiRequest(request) {
    try {
        // Tentar buscar da rede primeiro
        const networkResponse = await fetch(request);
        
        if (networkResponse.ok) {
            // Cachear resposta bem-sucedida
            const cache = await caches.open(DYNAMIC_CACHE);
            cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
    } catch (error) {
        // Se falhar, tentar buscar do cache
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }
        
        // Se não houver cache, retornar página offline
        return new Response(
            JSON.stringify({
                error: 'Sem conexão com a internet',
                message: 'Verifique sua conexão e tente novamente'
            }),
            {
                status: 503,
                statusText: 'Service Unavailable',
                headers: { 'Content-Type': 'application/json' }
            }
        );
    }
}

// Estratégia para requisições dinâmicas
async function handleDynamicRequest(request) {
    try {
        const networkResponse = await fetch(request);
        
        if (networkResponse.ok) {
            const cache = await caches.open(DYNAMIC_CACHE);
            cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
    } catch (error) {
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }
        
        // Redirecionar para página offline
        return caches.match('/offline.html');
    }
}

// Estratégia para arquivos estáticos
async function handleStaticRequest(request) {
    const cachedResponse = await caches.match(request);
    
    if (cachedResponse) {
        return cachedResponse;
    }
    
    try {
        const networkResponse = await fetch(request);
        
        if (networkResponse.ok) {
            const cache = await caches.open(STATIC_CACHE);
            cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
    } catch (error) {
        return new Response('Arquivo não encontrado', { status: 404 });
    }
}

// Estratégia para páginas principais
async function handlePageRequest(request) {
    const cachedResponse = await caches.match(request);
    
    if (cachedResponse) {
        return cachedResponse;
    }
    
    try {
        const networkResponse = await fetch(request);
        
        if (networkResponse.ok) {
            const cache = await caches.open(STATIC_CACHE);
            cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
    } catch (error) {
        return caches.match('/offline.html');
    }
}

// Sincronização em background
self.addEventListener('sync', (event) => {
    console.log('Sincronização em background:', event.tag);
    
    if (event.tag === 'background-sync') {
        event.waitUntil(performBackgroundSync());
    }
});

// Função para sincronização em background
async function performBackgroundSync() {
    try {
        // Sincronizar dados offline
        const offlineData = await getOfflineData();
        
        for (const data of offlineData) {
            try {
                await fetch(data.url, {
                    method: data.method,
                    headers: data.headers,
                    body: data.body
                });
                
                // Remover do cache offline após sucesso
                await removeOfflineData(data.id);
            } catch (error) {
                console.error('Erro na sincronização:', error);
            }
        }
    } catch (error) {
        console.error('Erro na sincronização em background:', error);
    }
}

// Armazenar dados offline
async function storeOfflineData(data) {
    const db = await openOfflineDB();
    const transaction = db.transaction(['offlineData'], 'readwrite');
    const store = transaction.objectStore('offlineData');
    
    await store.add({
        id: Date.now(),
        timestamp: new Date(),
        ...data
    });
}

// Obter dados offline
async function getOfflineData() {
    const db = await openOfflineDB();
    const transaction = db.transaction(['offlineData'], 'readonly');
    const store = transaction.objectStore('offlineData');
    
    return await store.getAll();
}

// Remover dados offline
async function removeOfflineData(id) {
    const db = await openOfflineDB();
    const transaction = db.transaction(['offlineData'], 'readwrite');
    const store = transaction.objectStore('offlineData');
    
    await store.delete(id);
}

// Abrir banco de dados offline
async function openOfflineDB() {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open('PassometroOffline', 1);
        
        request.onerror = () => reject(request.error);
        request.onsuccess = () => resolve(request.result);
        
        request.onupgradeneeded = (event) => {
            const db = event.target.result;
            
            if (!db.objectStoreNames.contains('offlineData')) {
                const store = db.createObjectStore('offlineData', { keyPath: 'id' });
                store.createIndex('timestamp', 'timestamp', { unique: false });
            }
        };
    });
}

// Notificações push
self.addEventListener('push', (event) => {
    console.log('Push notification recebida');
    
    const options = {
        body: event.data ? event.data.text() : 'Nova notificação do Passômetro',
        icon: '/static/icons/icon-192x192.png',
        badge: '/static/icons/badge-72x72.png',
        vibrate: [100, 50, 100],
        data: {
            dateOfArrival: Date.now(),
            primaryKey: 1
        },
        actions: [
            {
                action: 'explore',
                title: 'Ver',
                icon: '/static/icons/checkmark.png'
            },
            {
                action: 'close',
                title: 'Fechar',
                icon: '/static/icons/xmark.png'
            }
        ]
    };
    
    event.waitUntil(
        self.registration.showNotification('Passômetro', options)
    );
});

// Clique em notificação
self.addEventListener('notificationclick', (event) => {
    console.log('Notificação clicada');
    
    event.notification.close();
    
    if (event.action === 'explore') {
        event.waitUntil(
            clients.openWindow('/dashboard')
        );
    }
});

// Mensagens do cliente
self.addEventListener('message', (event) => {
    console.log('Mensagem recebida:', event.data);
    
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
    
    if (event.data && event.data.type === 'GET_VERSION') {
        event.ports[0].postMessage({ version: CACHE_NAME });
    }
}); 