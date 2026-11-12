/**
 * Monitoramento de erros (Sentry) carregado de forma preguiçosa.
 *
 * O SDK do Sentry é grande (~30 kB gz) e não precisa estar no caminho crítico
 * das rotas públicas. `initMonitoring()` agenda o `import('./sentryClient')`
 * para quando o navegador estiver ocioso, e só se `VITE_SENTRY_DSN` existir.
 *
 * `captureException()` mantém a semântica de antes: com DSN configurado, todo
 * erro chega ao Sentry. Erros capturados antes do SDK terminar de carregar
 * ficam numa fila e são enviados assim que o init acontece.
 */
type SentryModule = typeof import('./sentryClient');
type CaptureContext = Parameters<SentryModule['captureException']>[1];

const SENTRY_DSN: string = import.meta.env.VITE_SENTRY_DSN ?? '';

let sentry: SentryModule | null = null;
let loading: Promise<SentryModule | null> | null = null;
const pending: Array<[unknown, CaptureContext]> = [];
// Limite da fila para não acumular memória se o SDK nunca carregar (rede off).
const MAX_PENDING = 20;

function loadSentry(): Promise<SentryModule | null> {
  if (!SENTRY_DSN) return Promise.resolve(null);
  if (loading) return loading;
  loading = import('./sentryClient')
    .then((mod) => {
      mod.initSentry(SENTRY_DSN);
      sentry = mod;
      // Esvazia a fila de erros capturados antes do carregamento.
      for (const [error, ctx] of pending.splice(0)) mod.captureException(error, ctx);
      return mod;
    })
    .catch(() => {
      // Falha ao baixar o chunk (rede, deploy novo): permite tentar de novo depois.
      loading = null;
      return null;
    });
  return loading;
}

/** Agenda o carregamento do Sentry para depois da primeira pintura. */
export function initMonitoring(): void {
  if (!SENTRY_DSN || typeof window === 'undefined') return;
  const start = () => void loadSentry();
  if ('requestIdleCallback' in window) {
    window.requestIdleCallback(start, { timeout: 4000 });
  } else {
    setTimeout(start, 2000);
  }
}

/** Envia um erro ao Sentry (se configurado), carregando o SDK se preciso. */
export function captureException(error: unknown, context?: CaptureContext): void {
  if (!SENTRY_DSN) return;
  if (sentry) {
    sentry.captureException(error, context);
    return;
  }
  if (pending.length < MAX_PENDING) pending.push([error, context]);
  void loadSentry();
}
