/// <reference types="vitest/config" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(),
    // PWA offline-first (docs/arquitetura/OFFLINE_SYNC.md, seção 7.1).
    // registerType 'prompt': a versão nova do app só assume quando o usuário
    // clica em "Atualizar" (src/lib/offline/pwa.ts). 'autoUpdate' recarregaria a
    // aba sozinho e poderia descartar um formulário em preenchimento; os dados
    // da outbox ficam no IndexedDB de qualquer forma.
    VitePWA({
      registerType: 'prompt',
      injectRegister: false,
      includeAssets: ['favicon.svg', 'apple-touch-icon.png', 'robots.txt'],
      manifest: {
        name: 'FiscWise',
        short_name: 'FiscWise',
        description: 'Gestão contábil e fiscal para escritórios de contabilidade.',
        lang: 'pt-BR',
        dir: 'ltr',
        display: 'standalone',
        start_url: '/painel',
        scope: '/',
        theme_color: '#e05e18',
        background_color: '#0b1020',
        icons: [
          { src: '/pwa-192x192.png', sizes: '192x192', type: 'image/png', purpose: 'any' },
          { src: '/pwa-512x512.png', sizes: '512x512', type: 'image/png', purpose: 'any' },
          { src: '/pwa-maskable-512x512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
      workbox: {
        // App shell: HTML, JS, CSS, fontes e ícones do build.
        globPatterns: ['**/*.{js,css,html,svg,png,ico,woff,woff2}'],
        maximumFileSizeToCacheInBytes: 5 * 1024 * 1024,
        navigateFallback: '/index.html',
        navigateFallbackDenylist: [/^\/api\//],
        cleanupOutdatedCaches: true,
        // Background Sync: o SW só avisa as abas (public/sw-sync.js).
        importScripts: ['/sw-sync.js'],
        runtimeCaching: [
          {
            // Leituras da API para as telas de consulta (seção 3.2). Nunca
            // /sync/* nem /auth/*, e nunca escrita (só GET). A API fica em outra
            // origem em produção, por isso o teste é pelo caminho.
            urlPattern: ({ url, request }) =>
              request.method === 'GET' &&
              url.pathname.startsWith('/api/v1/') &&
              !url.pathname.startsWith('/api/v1/sync/') &&
              !url.pathname.startsWith('/api/v1/auth/'),
            handler: 'NetworkFirst',
            method: 'GET',
            options: {
              // Mesmo nome de API_CACHE_NAME (src/lib/offline/db.ts): apagado no logout.
              cacheName: 'fiscwise-api',
              networkTimeoutSeconds: 8,
              expiration: { maxEntries: 300, maxAgeSeconds: 7 * 24 * 60 * 60 },
              cacheableResponse: { statuses: [200] },
            },
          },
          {
            urlPattern: ({ url }) => url.origin === 'https://fonts.googleapis.com' || url.origin === 'https://fonts.gstatic.com',
            handler: 'CacheFirst',
            options: {
              cacheName: 'google-fonts',
              expiration: { maxEntries: 30, maxAgeSeconds: 365 * 24 * 60 * 60 },
              cacheableResponse: { statuses: [0, 200] },
            },
          },
        ],
      },
      devOptions: { enabled: false },
    }),
  ],
  test: {
    // e2e/ holds Playwright specs (run separately) — vitest must not collect them.
    exclude: ['e2e/**', 'node_modules/**', 'dist/**'],
    // Testes da camada offline usam IndexedDB falso (fake-indexeddb).
    setupFiles: ['./src/lib/offline/test-setup.ts'],
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    // Raise warning threshold — each individual chunk should still be small
    // but the total app may legitimately exceed 500 kB after splitting.
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      output: {
        manualChunks: {
          // Core React ecosystem — cached independently from app code
          'vendor-react': ['react', 'react-dom', 'react-router-dom'],
          // Data fetching
          'vendor-query': ['@tanstack/react-query'],
          // Heavy UI libraries
          'vendor-charts': ['recharts'],
          'vendor-motion': ['framer-motion'],
          // Form handling
          'vendor-form': ['react-hook-form', '@hookform/resolvers', 'zod'],
          // Utilities
          'vendor-utils': ['axios', 'zustand', 'date-fns', 'react-hot-toast', 'class-variance-authority', 'clsx', 'tailwind-merge'],
        },
      },
    },
  },
})
