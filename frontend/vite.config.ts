/// <reference types="vitest/config" />
import { defineConfig, type Plugin } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'
import path from 'path'
import { renderPlanCards, renderPlansFallback } from './src/features/subscription/precosHtml'
import type { Plan } from './src/lib/hooks/useSubscription'

/**
 * Cloudflare Web Analytics (grátis, sem cookies, inclui Core Web Vitals).
 * Injeta o beacon no index.html SÓ quando VITE_CF_BEACON_TOKEN existe no
 * build (variável do projeto no Cloudflare Pages — ver DEPLOY.md, passo 9).
 * Sem token, o HTML sai idêntico. O token é validado (hex de 32) para não
 * permitir injeção de HTML por variável mal preenchida.
 */
function cloudflareBeacon(): Plugin {
  let token = ''
  return {
    name: 'fiscwise:cloudflare-beacon',
    apply: 'build',
    configResolved(config) {
      const raw = String(config.env.VITE_CF_BEACON_TOKEN ?? '').trim()
      if (raw && !/^[a-f0-9]{32}$/i.test(raw)) {
        config.logger.warn('[cloudflare-beacon] VITE_CF_BEACON_TOKEN inválido (esperado hex de 32); beacon não injetado.')
        return
      }
      token = raw
    },
    transformIndexHtml() {
      if (!token) return
      return [
        {
          tag: 'script',
          attrs: {
            defer: true,
            src: 'https://static.cloudflareinsights.com/beacon.min.js',
            'data-cf-beacon': JSON.stringify({ token }),
          },
          injectTo: 'body',
        },
      ]
    },
  }
}

/**
 * Trava de segurança do build (docs/audit/PROTECAO_CONTRA_COPIA.md).
 * Derruba o build — e com ele o deploy no Cloudflare Pages — se o dist sair
 * com source map (que entregaria o código-fonte original) ou com algo que
 * parece segredo de servidor. Tudo que vai para o navegador é público.
 */
const SEGREDOS_PROIBIDOS: Array<[string, RegExp]> = [
  ['chave secreta do Stripe', /\b[sr]k_(live|test)_[0-9A-Za-z]{10,}/],
  ['chave privada', /-----BEGIN [A-Z ]*PRIVATE KEY-----/],
  ['chave da API do Resend', /\bre_[A-Za-z0-9]{8,}_[A-Za-z0-9]{10,}/],
  ['chave service_role do Supabase', /SUPABASE_SERVICE_ROLE|SERVICE_ROLE_KEY/],
  ['segredo do JWT', /JWT_SECRET_KEY/],
]

function guardaBuild(): Plugin {
  return {
    name: 'fiscwise:guarda-build',
    apply: 'build',
    generateBundle(_options, bundle) {
      const problemas: string[] = []
      for (const [nome, item] of Object.entries(bundle)) {
        if (nome.endsWith('.map')) problemas.push(`${nome}: source map no build`)
        const codigo = item.type === 'chunk' ? item.code : typeof item.source === 'string' ? item.source : ''
        if (!codigo) continue
        if (/[#@] sourceMappingURL=/.test(codigo)) problemas.push(`${nome}: aponta para source map`)
        for (const [rotulo, re] of SEGREDOS_PROIBIDOS) {
          if (re.test(codigo)) problemas.push(`${nome}: parece conter ${rotulo}`)
        }
      }
      if (problemas.length) {
        this.error(`Build bloqueado para não expor código ou segredo:\n- ${problemas.join('\n- ')}`)
      }
    },
  }
}

/**
 * Pré-renderiza a página estática /precos (precos.html) com o catálogo que a
 * API devolve no momento do build (GET /api/v1/subscription/plans), para
 * buscadores e prévias de link lerem os planos sem rodar JavaScript. No
 * navegador, src/precos.ts busca de novo e substitui: o preço exibido é sempre
 * o do banco. Se a API não responder no build, sai o aviso de carregamento e
 * o script preenche depois; o build não falha por isso.
 */
function precosPrerender(): Plugin {
  let apiUrl = ''
  let logger: { info(msg: string): void; warn(msg: string): void } = console
  return {
    name: 'fiscwise:precos-prerender',
    apply: 'build',
    configResolved(config) {
      apiUrl = String(config.env.VITE_API_URL || 'https://fiscwise-api-45ckqevl6a-rj.a.run.app').replace(/\/+$/, '')
      logger = config.logger
    },
    transformIndexHtml: {
      order: 'pre',
      async handler(html, ctx) {
        if (!html.includes('<!--precos:planos-->')) return html
        let cards = ''
        try {
          const res = await fetch(`${apiUrl}/api/v1/subscription/plans`, { signal: AbortSignal.timeout(8000) })
          if (!res.ok) throw new Error(`HTTP ${res.status}`)
          cards = renderPlanCards((await res.json()) as Plan[])
          logger.info(`[precos] ${path.basename(ctx.filename)} pré-renderizado com o catálogo de ${apiUrl}`)
        } catch (err) {
          logger.warn(`[precos] catálogo indisponível no build (${String(err)}); a página carrega os preços no navegador.`)
        }
        return html.replace('<!--precos:planos-->', cards || renderPlansFallback('loading'))
      },
    },
  }
}

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(),
    cloudflareBeacon(),
    guardaBuild(),
    precosPrerender(),
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
  // Proteção contra cópia (docs/audit/PROTECAO_CONTRA_COPIA.md): o build de
  // produção sai minificado, sem `debugger` e sem source map. Não ligar
  // `sourcemap` aqui: ele publicaria o código-fonte original junto com o site.
  // Se um dia os mapas forem para o Sentry, usar 'hidden' + upload + apagar os
  // .map do dist (o plugin guardaBuild abaixo barra .map no deploy).
  esbuild: { drop: ['debugger'] },
  build: {
    // Navegadores alvo já suportam ES2020; evita transpilar/polyfills extras.
    target: 'es2020',
    cssCodeSplit: true,
    sourcemap: false,
    minify: 'esbuild',
    // Todos os navegadores alvo suportam <link rel="modulepreload">; o polyfill
    // só adicionaria bytes ao chunk de entrada.
    modulePreload: { polyfill: false },
    // Raise warning threshold — each individual chunk should still be small
    // but the total app may legitimately exceed 500 kB after splitting.
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      // Duas páginas: o app (index.html) e a página estática de preços.
      input: {
        main: path.resolve(__dirname, 'index.html'),
        precos: path.resolve(__dirname, 'precos.html'),
      },
      output: {
        // Aviso de autoria em cada arquivo JS do app (comentário /*! sobrevive à
        // minificação). Serve de prova de origem se o código aparecer copiado.
        banner: (chunk) =>
          chunk.name.startsWith('vendor-')
            ? ''
            : `/*! FiscWise (c) ${new Date().getFullYear()} VStack Solutions. Software proprietario, todos os direitos reservados. Copia, engenharia reversa e redistribuicao proibidas (Lei 9.609/1998). */`,
        manualChunks: {
          // Core React ecosystem — cached independently from app code
          'vendor-react': ['react', 'react-dom', 'react-router-dom'],
          // Data fetching
          'vendor-query': ['@tanstack/react-query'],
          // Heavy UI libraries
          'vendor-motion': ['framer-motion'],
          // Form handling
          'vendor-form': ['react-hook-form', '@hookform/resolvers', 'zod'],
          // Utilities
          'vendor-utils': ['axios', 'zustand', 'class-variance-authority', 'clsx', 'tailwind-merge'],
        },
      },
    },
  },
})
