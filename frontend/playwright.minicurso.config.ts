import { defineConfig } from '@playwright/test'

/**
 * Gravação das aulas do Minicurso FiscWise (não faz parte da suíte E2E).
 *
 *   npm run minicurso:gravar
 *
 * Sobe o build de produção (vite preview), troca a API por dados de
 * demonstração (e2e/minicurso-demo-api.ts) e grava cada aula em vídeo.
 * Precisa do ffmpeg: cada .webm vira .mp4 + capa .jpg em public/minicurso/
 * e os capítulos vão para src/lib/minicursoGravacoes.json.
 */
const PORT = 4174
const chromiumPath = process.env.PW_CHROMIUM_PATH

export default defineConfig({
  testDir: './e2e',
  testMatch: /minicurso\.gravacao\.ts/,
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 240_000,
  reporter: [['list']],
  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
    locale: 'pt-BR',
    timezoneId: 'America/Sao_Paulo',
    viewport: { width: 1280, height: 720 },
    deviceScaleFactor: 1,
    serviceWorkers: 'block',
    colorScheme: 'light',
    trace: 'off',
    launchOptions: chromiumPath ? { executablePath: chromiumPath } : {},
  },
  webServer: {
    command: `npx vite build && npx vite preview --host 127.0.0.1 --port ${PORT} --strictPort`,
    url: `http://127.0.0.1:${PORT}`,
    reuseExistingServer: true,
    timeout: 240_000,
  },
})
