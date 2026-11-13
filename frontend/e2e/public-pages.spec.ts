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

test('/: página inicial pública mostra o H1 e o cadastro', async ({ page }) => {
  await page.goto('/', { waitUntil: 'load' })

  await expect(page).toHaveTitle(/obrigações fiscais/)
  const h1 = page.getByRole('heading', { level: 1 })
  await expect(h1).toHaveCount(1)
  await expect(h1).toHaveText('Sua carteira de clientes em dia, sem planilha e sem prazo perdido.')
  await expect(page.getByRole('link', { name: 'Testar grátis por 14 dias' }).first()).toBeVisible()
})

test('/: planos e preços sem plano Gratuito e com o teste grátis em cada plano', async ({ page }) => {
  const { DEMO_PLANS } = await import('./minicurso-demo-api')
  await page.route(/\/api\/v1\/subscription\/plans/, (r) =>
    r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(DEMO_PLANS) }),
  )
  await page.goto('/')
  await page.getByRole('link', { name: 'Ver planos e preços' }).click()
  await expect(page.getByRole('heading', { name: 'Planos e preços' })).toBeInViewport()
  const teste = page.getByRole('link', { name: 'Começar teste grátis' }).first()
  await expect(teste).toBeVisible()
  await expect(teste).toHaveAttribute('href', '/register')
  await expect(page.getByRole('heading', { name: 'Gratuito' })).toHaveCount(0)
  await expect(page.getByText('Sem multa', { exact: false }).first()).toBeVisible()
})
