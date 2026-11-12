import { test, expect, measureVitals } from './fixtures'

/**
 * Páginas públicas, sem backend: renderizam, mostram o formulário e não
 * "pulam" (CLS <= 0,1, meta do Google). LCP só é registrado, não reprova:
 * a meta de LCP é da Frente C. Os valores vão para as anotações do
 * relatório do Playwright (e para o stdout, para colar no PR).
 */

const CLS_LIMIT = 0.1

const pages = [
  {
    path: '/login',
    title: /Entrar/,
    ready: (p: import('@playwright/test').Page) => p.getByRole('heading', { name: 'Entrar no FiscWise' }),
    field: (p: import('@playwright/test').Page) => p.getByLabel('E-mail'),
  },
  {
    path: '/register',
    title: /Criar conta/,
    ready: (p: import('@playwright/test').Page) => p.getByRole('heading', { name: 'Criar conta' }),
    field: (p: import('@playwright/test').Page) => p.getByLabel(/Nome do escritório/),
  },
]

for (const spec of pages) {
  test(`${spec.path}: renderiza o formulário e mantém CLS <= ${CLS_LIMIT}`, async ({ page }, testInfo) => {
    await page.goto(spec.path, { waitUntil: 'load' })

    await expect(page).toHaveTitle(spec.title)
    await expect(spec.ready(page)).toBeVisible()
    await expect(spec.field(page)).toBeVisible()
    await expect(page.locator('form button[type="submit"]').first()).toBeVisible()

    const vitals = await measureVitals(page)
    const project = testInfo.project.name
    testInfo.annotations.push(
      { type: 'FCP (ms)', description: String(vitals.fcp) },
      { type: 'LCP (ms)', description: String(vitals.lcp) },
      { type: 'CLS', description: String(vitals.cls) },
    )
    console.log(`[vitals] ${project} ${spec.path} FCP=${vitals.fcp}ms LCP=${vitals.lcp}ms CLS=${vitals.cls}`)

    expect(vitals.lcp, 'LCP precisa ser observado').not.toBeNull()
    expect(vitals.cls, `CLS ${vitals.cls} acima de ${CLS_LIMIT}`).toBeLessThanOrEqual(CLS_LIMIT)
  })
}
