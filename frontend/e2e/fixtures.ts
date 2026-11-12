import { test as base, expect, type Page } from '@playwright/test'

/**
 * Fixture compartilhada dos E2E.
 *
 * `throttle: true` (projeto `mobile-slow-4g`) aplica via CDP, antes de cada
 * teste, rede "Slow 4G" (400 kbps, 400 ms de latência) e CPU 4x mais lenta,
 * o mesmo perfil do diagnóstico A0 (docs/audit/DIAGNOSTICO_A0_PERFORMANCE.md).
 * Só funciona no Chromium (CDP); nos outros navegadores é ignorado.
 */
export interface ThrottleOptions {
  throttle: boolean
}

const SLOW_4G = {
  offline: false,
  latency: 400,
  downloadThroughput: (400 * 1000) / 8,
  uploadThroughput: (400 * 1000) / 8,
}

export const test = base.extend<ThrottleOptions>({
  throttle: [false, { option: true }],
  // 2º argumento renomeado de `use` para não acionar a regra de hooks do React no lint.
  page: async ({ page, throttle, browserName }, provide) => {
    if (throttle && browserName === 'chromium') {
      const cdp = await page.context().newCDPSession(page)
      await cdp.send('Network.enable')
      await cdp.send('Network.emulateNetworkConditions', SLOW_4G)
      await cdp.send('Emulation.setCPUThrottlingRate', { rate: 4 })
    }
    await provide(page)
  },
})

export { expect }

export interface PageVitals {
  fcp: number | null
  lcp: number | null
  cls: number
}

/**
 * Lê FCP/LCP/CLS com PerformanceObserver (`buffered: true`) depois do load,
 * esperando `settleMs` para o último candidato de LCP e os layout shifts
 * tardios. CLS aqui é a soma dos shifts sem input recente (página curta,
 * sem rolagem: equivale à maior janela de sessão).
 */
export async function measureVitals(page: Page, settleMs = 1500): Promise<PageVitals> {
  return page.evaluate(
    (wait) =>
      new Promise<PageVitals>((resolve) => {
        let lcp: number | null = null
        let fcp: number | null = null
        let cls = 0
        try {
          new PerformanceObserver((list) => {
            for (const e of list.getEntries()) if (e.name === 'first-contentful-paint') fcp = e.startTime
          }).observe({ type: 'paint', buffered: true })
          new PerformanceObserver((list) => {
            const entries = list.getEntries()
            const last = entries[entries.length - 1]
            if (last) lcp = last.startTime
          }).observe({ type: 'largest-contentful-paint', buffered: true })
          new PerformanceObserver((list) => {
            for (const e of list.getEntries() as (PerformanceEntry & { value: number; hadRecentInput: boolean })[]) {
              if (!e.hadRecentInput) cls += e.value
            }
          }).observe({ type: 'layout-shift', buffered: true })
        } catch {
          /* sem suporte */
        }
        const ms = (v: number | null) => (v === null ? null : Math.round(v))
        setTimeout(() => resolve({ fcp: ms(fcp), lcp: ms(lcp), cls: Math.round(cls * 10000) / 10000 }), wait)
      }),
    settleMs,
  )
}
