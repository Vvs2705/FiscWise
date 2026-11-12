/// <reference types="vitest/config" />
import { defineConfig, type Plugin } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

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

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react(), cloudflareBeacon()],
  test: {
    // e2e/ holds Playwright specs (run separately) — vitest must not collect them.
    exclude: ['e2e/**', 'node_modules/**', 'dist/**'],
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
    // Navegadores alvo já suportam ES2020; evita transpilar/polyfills extras.
    target: 'es2020',
    cssCodeSplit: true,
    sourcemap: false,
    // Todos os navegadores alvo suportam <link rel="modulepreload">; o polyfill
    // só adicionaria bytes ao chunk de entrada.
    modulePreload: { polyfill: false },
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
