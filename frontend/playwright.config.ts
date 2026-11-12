import { defineConfig, devices } from '@playwright/test'
import type { ThrottleOptions } from './e2e/fixtures'

/**
 * E2E do front. Roda contra o build de produção servido por `vite preview`
 * (porta 4173), então mede o bundle real, sem backend.
 *
 * Projetos:
 * - desktop-chromium: Chrome desktop.
 * - mobile-pixel-5:   Pixel 5 (viewport, DPR, touch, UA de celular).
 *                     Não roda o contrast.spec.ts (job "Frontend contrast (axe)" do CI).
 * - mobile-slow-4g:   Pixel 5 + rede Slow 4G (400 kbps / 400 ms) + CPU 4x
 *                     (fixture `throttle` em e2e/fixtures.ts). Só as páginas públicas.
 *
 * Variáveis:
 * - PW_CHROMIUM_PATH: usa este executável do Chromium (ex.: /opt/pw-browsers/chromium)
 *   em vez do baixado por `npx playwright install`.
 * - E2E_BASE_URL: testa outro endereço (ex.: preview do Cloudflare Pages); desliga o webServer.
 * - E2E_API_URL:  habilita os specs que precisam de API real (fiscal-operations).
 */
const PORT = 4173
const externalBaseURL = process.env.E2E_BASE_URL
const baseURL = externalBaseURL ?? `http://127.0.0.1:${PORT}`
const chromiumPath = process.env.PW_CHROMIUM_PATH
const launchOptions = chromiumPath ? { executablePath: chromiumPath } : {}

export default defineConfig<ThrottleOptions>({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 2 : undefined,
  timeout: 60_000,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : [['list']],
  use: {
    baseURL,
    trace: 'retain-on-failure',
    locale: 'pt-BR',
    timezoneId: 'America/Sao_Paulo',
  },
  projects: [
    {
      name: 'desktop-chromium',
      use: { ...devices['Desktop Chrome'], launchOptions },
    },
    {
      name: 'mobile-pixel-5',
      // Contraste depende do tema, não do aparelho: roda só no desktop-chromium.
      testIgnore: /contrast\.spec\.ts/,
      use: { ...devices['Pixel 5'], launchOptions },
    },
    {
      name: 'mobile-slow-4g',
      testMatch: /public-pages\.spec\.ts/,
      timeout: 180_000,
      use: { ...devices['Pixel 5'], launchOptions, throttle: true },
    },
  ],
  webServer: externalBaseURL
    ? undefined
    : {
        // Build de produção + preview: o que o Cloudflare Pages serve.
        command: `npx vite build && npx vite preview --host 127.0.0.1 --port ${PORT} --strictPort`,
        url: baseURL,
        reuseExistingServer: !process.env.CI,
        timeout: 240_000,
      },
})
