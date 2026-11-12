/**
 * Ponto único de contato com o SDK do Sentry, importado só por import()
 * dinâmico em lib/monitoring.ts. Usar imports nomeados aqui (e não o namespace
 * inteiro) mantém o tree-shaking: o chunk fica ~30 kB gz em vez de ~150 kB gz.
 */
import { init, browserTracingIntegration, captureException } from '@sentry/react';

export function initSentry(dsn: string): void {
  init({
    dsn,
    environment: import.meta.env.MODE,
    release: `fiscwise-frontend@${import.meta.env.VITE_APP_VERSION ?? '1.0.0'}`,
    integrations: [browserTracingIntegration()],
    tracesSampleRate: Number(import.meta.env.VITE_SENTRY_TRACES_SAMPLE_RATE ?? '0.1'),
    sendDefaultPii: false,
  });
}

export { captureException };
