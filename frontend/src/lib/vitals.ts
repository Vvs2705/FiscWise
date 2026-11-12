/**
 * Web Vitals de campo (RUM) sem dependência: LCP, CLS, INP, FCP e TTFB via
 * PerformanceObserver. Carregado por import() dinâmico depois do `load`
 * (ver main.tsx), então não pesa o caminho crítico.
 *
 * Por que não o pacote `web-vitals` do Google: ~2 KB gz a mais e uma
 * dependência nova para cobrir só o Chromium com mais precisão (INP por
 * percentil, bfcache). Para tendência de p75 por página, esta versão basta.
 *
 * Envio: `navigator.sendBeacon` para VITE_VITALS_ENDPOINT (texto JSON, sem
 * preflight CORS) quando a aba fica oculta. Sem endpoint: console.debug só em
 * DEV. Não manda cookies próprios, query string, IP nem dados do usuário —
 * só a rota (pathname com números longos mascarados) e os números.
 */

export type VitalName = 'LCP' | 'CLS' | 'INP' | 'FCP' | 'TTFB'

export interface VitalsReport {
  path: string
  nav: string
  conn?: string
  vitals: Partial<Record<VitalName, number>>
}

type LayoutShiftEntry = PerformanceEntry & { value: number; hadRecentInput: boolean }
type EventTimingEntry = PerformanceEntry & { interactionId?: number }

const values: Partial<Record<VitalName, number>> = {}
let started = false
let sent = false
let landingPath: string | undefined

/** Mascara CPF/CNPJ e números longos (11+ dígitos, mesmo formatados) da URL. */
export function scrubPath(pathname: string): string {
  return pathname.replace(/\d[\d.\-/]*\d/g, (m) => (m.replace(/\D/g, '').length >= 11 ? ':id' : m))
}

function observe(type: string, cb: (entries: PerformanceEntry[]) => void, extra: Record<string, unknown> = {}) {
  try {
    if (!PerformanceObserver.supportedEntryTypes?.includes(type)) return
    const po = new PerformanceObserver((list) => cb(list.getEntries()))
    po.observe({ type, buffered: true, ...extra } as PerformanceObserverInit)
  } catch {
    /* navegador sem suporte: ignora a métrica */
  }
}

function round(name: VitalName, v: number) {
  return name === 'CLS' ? Math.round(v * 10000) / 10000 : Math.round(v)
}

export function buildReport(): VitalsReport {
  const nav = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming | undefined
  const conn = (navigator as Navigator & { connection?: { effectiveType?: string } }).connection
  const vitals: VitalsReport['vitals'] = {}
  for (const [k, v] of Object.entries(values) as [VitalName, number][]) vitals[k] = round(k, v)
  return {
    path: landingPath ?? scrubPath(location.pathname),
    nav: nav?.type ?? 'navigate',
    conn: conn?.effectiveType,
    vitals,
  }
}

function flush() {
  if (sent || Object.keys(values).length === 0) return
  const report = buildReport()
  const endpoint = import.meta.env.VITE_VITALS_ENDPOINT
  if (endpoint) {
    sent = true
    try {
      navigator.sendBeacon(endpoint, JSON.stringify(report))
    } catch {
      /* sem beacon: perde a amostra, nunca quebra a página */
    }
  } else if (import.meta.env.DEV) {
    console.debug('[vitals]', report)
  }
}

export function startVitals(): void {
  if (started || typeof PerformanceObserver === 'undefined') return
  started = true

  const nav = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming | undefined
  // Rota da carga inicial: LCP/FCP/TTFB dizem respeito a ela, não à rota ativa ao sair.
  landingPath = scrubPath(location.pathname)
  if (nav) {
    const activation = (nav as PerformanceNavigationTiming & { activationStart?: number }).activationStart ?? 0
    values.TTFB = Math.max(nav.responseStart - activation, 0)
  }

  observe('paint', (entries) => {
    for (const e of entries) if (e.name === 'first-contentful-paint') values.FCP = e.startTime
  })

  // LCP: o último candidato antes da primeira interação é o valor final.
  observe('largest-contentful-paint', (entries) => {
    const last = entries[entries.length - 1]
    if (last) values.LCP = last.startTime
  })

  // CLS: maior "janela de sessão" (gap < 1 s, janela < 5 s), como no Chrome.
  let sessionValue = 0
  let sessionStart = 0
  let sessionLast = 0
  observe('layout-shift', (entries) => {
    for (const e of entries as LayoutShiftEntry[]) {
      if (e.hadRecentInput) continue
      if (sessionValue && e.startTime - sessionLast < 1000 && e.startTime - sessionStart < 5000) {
        sessionValue += e.value
      } else {
        sessionValue = e.value
        sessionStart = e.startTime
      }
      sessionLast = e.startTime
      values.CLS = Math.max(values.CLS ?? 0, sessionValue)
    }
  })
  values.CLS ??= 0

  // INP aproximado: maior duração por interação (com >= 50 interações,
  // descarta 1 a cada 50, como o percentil 98 do Chrome).
  const perInteraction = new Map<number, number>()
  observe(
    'event',
    (entries) => {
      for (const e of entries as EventTimingEntry[]) {
        if (!e.interactionId) continue
        perInteraction.set(e.interactionId, Math.max(perInteraction.get(e.interactionId) ?? 0, e.duration))
      }
      const sorted = [...perInteraction.values()].sort((a, b) => b - a)
      const idx = Math.min(sorted.length - 1, Math.floor(sorted.length / 50))
      if (sorted.length) values.INP = sorted[idx]
    },
    { durationThreshold: 40 },
  )

  addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') flush()
  })
  addEventListener('pagehide', flush)
}
