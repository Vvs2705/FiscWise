import AxeBuilder from '@axe-core/playwright'
import { test, expect, type Browser, type BrowserContext, type Page } from '@playwright/test'
import { DEMO_PLANS, installDemoApi } from './minicurso-demo-api'

/**
 * Contraste de cor (WCAG AA) em todas as telas, nos temas claro e escuro.
 *
 * Regra do dono do produto: texto ilegível (ex.: branco em fundo branco) não
 * pode acontecer em nenhuma página, em nenhum tema. Este spec roda o axe só com
 * a regra `color-contrast` e reprova o CI em qualquer violação.
 *
 * - Tema: gravado em localStorage (`fw-theme`) antes do carregamento e conferido
 *   pela classe `dark` no <html>.
 * - Telas autenticadas: API em memória do Minicurso (e2e/minicurso-demo-api.ts).
 * - Espera o conteúdo real (sem skeletons nem `aria-busy`) antes de medir.
 *
 * - O que o axe deixa em "incomplete" (texto de SVG como o wordmark da logo,
 *   fundo com pseudo-elemento) é medido por `checkContrastFallback`.
 *
 * Exclusões: nenhuma. Elementos desabilitados já são ignorados pelo próprio
 * axe (WCAG 1.4.3 não se aplica a componentes inativos). O botão do Google
 * (iframe de terceiro, cores do Google) é bloqueado para o teste não depender
 * da rede externa.
 *
 * Rodar: npx playwright test e2e/contrast.spec.ts --project=desktop-chromium
 */

type Theme = 'light' | 'dark'
const THEMES: Theme[] = ['light', 'dark']

async function newThemedContext(browser: Browser, theme: Theme): Promise<BrowserContext> {
  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 },
    locale: 'pt-BR',
    timezoneId: 'America/Sao_Paulo',
    colorScheme: theme,
    // Sem animações: o axe mede a cor final, não um quadro do fade de entrada.
    reducedMotion: 'reduce',
    serviceWorkers: 'block',
  })
  await context.addInitScript((t) => localStorage.setItem('fw-theme', t), theme)
  // Login com Google: iframe e script de terceiro, fora do nosso tema.
  await context.route(/accounts\.google\.com|apis\.google\.com/, (r) => r.abort())
  // Vitrine de planos da página inicial (catálogo público): medida com os cards.
  await context.route(/\/api\/v1\/subscription\/plans/, (r) =>
    r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(DEMO_PLANS) }),
  )
  return context
}

/** Espera a tela assentar: rede ociosa, sem skeletons nem carregadores. */
async function waitForContent(page: Page) {
  await page.waitForLoadState('networkidle').catch(() => undefined)
  await expect(page.locator('.skeleton, [aria-busy="true"]')).toHaveCount(0, { timeout: 15_000 })
  // A tela quebrada (ErrorBoundary) não pode passar por "sem violação".
  await expect(page.getByText('Algo deu errado')).toHaveCount(0)
  await page.evaluate(() => document.fonts.ready)
  await page.waitForTimeout(150)
}

async function expectTheme(page: Page, theme: Theme) {
  if (theme === 'dark') await expect(page.locator('html')).toHaveClass(/(^|\s)dark(\s|$)/)
  else await expect(page.locator('html')).not.toHaveClass(/(^|\s)dark(\s|$)/)
}

/**
 * Contraste calculado na página para o que o axe deixa em "incomplete" (texto
 * de SVG, como o wordmark da logo; fundo com pseudo-elemento, como o painel de
 * ajuda; elemento parcialmente coberto). Compõe as cores de fundo dos ancestrais
 * (com alfa e opacity) até o <html> e compara com a cor do texto. Devolve só
 * os que ficam abaixo do mínimo AA; os que nem assim dá para medir (fundo com
 * imagem ou gradiente) voltam em `unknown`.
 */
async function checkContrastFallback(page: Page, selectors: string[]) {
  return page.evaluate((sels) => {
    type RGBA = [number, number, number, number]
    const ctx = document.createElement('canvas').getContext('2d')!
    const parse = (c: string): RGBA => {
      ctx.clearRect(0, 0, 1, 1)
      ctx.fillStyle = '#000'
      ctx.fillStyle = c
      ctx.fillRect(0, 0, 1, 1)
      const [r, g, b, a] = ctx.getImageData(0, 0, 1, 1).data
      return [r, g, b, a / 255]
    }
    const over = (top: RGBA, bottom: RGBA): RGBA => {
      const a = top[3] + bottom[3] * (1 - top[3])
      if (a === 0) return [0, 0, 0, 0]
      const mix = (i: number) => (top[i] * top[3] + bottom[i] * bottom[3] * (1 - top[3])) / a
      return [mix(0), mix(1), mix(2), a]
    }
    const lum = ([r, g, b]: RGBA) => {
      const f = (v: number) => {
        v /= 255
        return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4
      }
      return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)
    }
    const ratio = (a: RGBA, b: RGBA) => {
      const [x, y] = [lum(a), lum(b)].sort((m, n) => n - m)
      return (x + 0.05) / (y + 0.05)
    }
    const failures: string[] = []
    const unknown: string[] = []
    for (const sel of sels) {
      const el = document.querySelector(sel)
      if (!el) continue
      const cs = getComputedStyle(el)
      const isSvgText = el instanceof SVGElement
      // Fundo: composição dos ancestrais, do <html> (branco do canvas) para baixo.
      const chain: Element[] = []
      for (let n: Element | null = el; n; n = n.parentElement) chain.push(n)
      let bg: RGBA = [255, 255, 255, 1]
      let opacity = 1
      let measurable = true
      for (const n of chain.reverse()) {
        const ncs = getComputedStyle(n)
        if (ncs.backgroundImage !== 'none' && !(n instanceof SVGElement)) measurable = false
        const c = parse(ncs.backgroundColor)
        if (!(n instanceof SVGElement) && c[3] > 0) bg = over(c, bg)
        opacity *= Number(ncs.opacity)
      }
      if (!measurable) {
        unknown.push(`${sel}: fundo com imagem/gradiente`)
        continue
      }
      const fgRaw = parse(isSvgText ? cs.fill : cs.color)
      const fg = over([fgRaw[0], fgRaw[1], fgRaw[2], fgRaw[3] * opacity], bg)
      const size = parseFloat(cs.fontSize)
      const bold = Number(cs.fontWeight) >= 700
      const min = size >= 24 || (bold && size >= 18.66) ? 3 : 4.5
      const r = ratio(fg, bg)
      if (r < min) {
        failures.push(`${sel}: ${r.toFixed(2)}:1 (mínimo ${min}:1) — "${(el.textContent ?? '').trim().slice(0, 60)}"`)
      }
    }
    return { failures, unknown }
  }, selectors)
}

async function expectNoContrastViolations(page: Page, label: string, include?: string) {
  let builder = new AxeBuilder({ page }).withRules(['color-contrast'])
  if (include) builder = builder.include(include)
  const results = await builder.analyze()

  const report = results.violations
    .flatMap((v) => v.nodes)
    .map((n) => `  ${n.target.join(' ')}\n    ${n.failureSummary?.split('\n').slice(1).join(' ').trim()}\n    ${n.html.slice(0, 160)}`)
    .join('\n')
  expect(results.violations, `Contraste insuficiente em ${label}:\n${report}`).toEqual([])

  // O que o axe não decidiu é medido aqui; nada fica sem verificação.
  const pending = results.incomplete
    .flatMap((v) => v.nodes)
    .map((n) => n.target)
    .filter((t): t is [string] => t.length === 1 && typeof t[0] === 'string')
    .map((t) => t[0])
  const fallback = await checkContrastFallback(page, pending)
  if (fallback.unknown.length) {
    test.info().annotations.push({ type: 'contraste não medido', description: `${label}: ${fallback.unknown.join('; ')}` })
  }
  expect(fallback.failures, `Contraste insuficiente (medição própria) em ${label}:\n  ${fallback.failures.join('\n  ')}`).toEqual([])
}

// ─── Telas públicas ────────────────────────────────────────────────────────────

const PUBLIC_ROUTES: Array<{ path: string; ready: (p: Page) => ReturnType<Page['locator']> }> = [
  { path: '/', ready: (p) => p.getByRole('heading', { level: 1 }) },
  { path: '/login', ready: (p) => p.getByRole('heading', { name: 'Entrar no FiscWise' }) },
  { path: '/register', ready: (p) => p.getByRole('heading', { name: 'Criar conta' }) },
  { path: '/esqueci-senha', ready: (p) => p.getByRole('heading', { level: 1 }) },
  { path: '/redefinir-senha?token=x', ready: (p) => p.getByRole('heading', { name: 'Criar nova senha' }) },
  // Sem token: estado de erro "link incompleto".
  { path: '/redefinir-senha', ready: (p) => p.getByRole('alert') },
  // Página estática de preços (precos.html), com o catálogo simulado acima.
  { path: '/precos', ready: (p) => p.getByRole('heading', { name: 'Planos e preços' }) },
  { path: '/termos', ready: (p) => p.getByRole('heading', { level: 1 }) },
  { path: '/privacidade', ready: (p) => p.getByRole('heading', { level: 1 }) },
  { path: '/404', ready: (p) => p.getByRole('heading', { level: 1 }) },
  { path: '/portal/login', ready: (p) => p.getByRole('heading', { level: 1 }) },
]

// ─── Telas do escritório (API em memória) ──────────────────────────────────────

const OFFICE_ROUTES = [
  '/painel',
  '/foco',
  '/clientes',
  '/clientes/cli-padaria',
  '/fechamento',
  '/fechamento/fech-cli-padaria',
  '/obrigacoes',
  '/documentos',
  '/notas-fiscais',
  '/notas-fiscais/nova',
  '/ecac',
  '/guias',
  '/caixa-postal-fiscal',
  '/procuracoes',
  '/certificados',
  '/financeiro',
  '/whatsapp',
  '/portal',
  '/relatorios',
  '/aprender',
  '/minicurso',
  '/configuracoes',
  '/configuracoes?aba=plano',
  '/sincronizacao',
  '/calculadora',
]

for (const theme of THEMES) {
  test.describe(`contraste (${theme})`, () => {
    for (const route of PUBLIC_ROUTES) {
      test(`público ${route.path}`, async ({ browser }) => {
        const context = await newThemedContext(browser, theme)
        const page = await context.newPage()
        await page.goto(route.path)
        await expect(route.ready(page).first()).toBeVisible()
        await waitForContent(page)
        await expectTheme(page, theme)
        await expectNoContrastViolations(page, `${route.path} (${theme})`)
        await context.close()
      })
    }

    test('público /login: verificação em 2 etapas', async ({ browser }) => {
      const context = await newThemedContext(browser, theme)
      await context.route(/\/api\/v1\/auth\/login$/, (r) =>
        r.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            status: 'requires_2fa',
            mfa_token: 'mfa-demo',
            two_factor_method: 'email',
            message: 'Enviamos um código de 6 dígitos para o seu e-mail.',
          }),
        }),
      )
      const page = await context.newPage()
      await page.goto('/login')
      await page.locator('#email').fill('ana@contabilidadeexemplo.com.br')
      await page.locator('#password').fill('senha-de-teste-123')
      await page.locator('form button[type="submit"]').first().click()
      await expect(page.getByRole('heading', { name: 'Verificação em 2 etapas' })).toBeVisible()
      await waitForContent(page)
      await expectTheme(page, theme)
      await expectNoContrastViolations(page, `/login 2FA (${theme})`)
      await context.close()
    })

    for (const path of OFFICE_ROUTES) {
      test(`escritório ${path}`, async ({ browser }) => {
        const context = await newThemedContext(browser, theme)
        await installDemoApi(context)
        const page = await context.newPage()
        await page.goto(path)
        await expect(page.locator('main')).toBeVisible()
        await waitForContent(page)
        await expectTheme(page, theme)
        await expectNoContrastViolations(page, `${path} (${theme})`)
        await context.close()
      })
    }

    test('escritório: relatório de situação do cliente (modal)', async ({ browser }) => {
      const context = await newThemedContext(browser, theme)
      await installDemoApi(context)
      const page = await context.newPage()
      await page.goto('/clientes/cli-padaria')
      await waitForContent(page)
      await page.getByRole('button', { name: /Gerar Relatório/ }).click()
      const dialog = page.getByRole('dialog')
      await expect(dialog).toBeVisible()
      await waitForContent(page)
      await expectTheme(page, theme)
      await expectNoContrastViolations(page, `relatório do cliente (${theme})`, '[role="dialog"]')
      await context.close()
    })

    test('escritório: painel de ajuda', async ({ browser }) => {
      const context = await newThemedContext(browser, theme)
      await installDemoApi(context)
      const page = await context.newPage()
      await page.goto('/painel')
      await waitForContent(page)
      await page.locator('[data-tour="ajuda"]').click()
      await expect(page.getByRole('button', { name: 'Fechar ajuda' })).toBeVisible()
      await waitForContent(page)
      await expectNoContrastViolations(page, `ajuda (${theme})`)
      await context.close()
    })

    test('escritório: novo cliente (formulário)', async ({ browser }) => {
      const context = await newThemedContext(browser, theme)
      await installDemoApi(context)
      const page = await context.newPage()
      await page.goto('/clientes')
      await waitForContent(page)
      await page.getByRole('button', { name: 'Novo cliente' }).first().click()
      await expect(page.locator('#document')).toBeVisible()
      await waitForContent(page)
      await expectNoContrastViolations(page, `novo cliente (${theme})`)
      await context.close()
    })

    test('portal do cliente /portal/dashboard', async ({ browser }) => {
      const context = await newThemedContext(browser, theme)
      await installDemoApi(context)
      // Sessão de cliente final (role client) por cima da sessão do contador.
      await context.addInitScript(() => {
        localStorage.setItem(
          'user',
          JSON.stringify({ id: 'demo-client', email: 'financeiro@paodourado.com.br', full_name: 'Carlos Dourado', role: 'client' }),
        )
      })
      // O mock só conhece a prévia do portal; a visão do cliente usa o mesmo formato.
      await context.route(/\/api\/v1\/portal\/my-overview/, (r) =>
        r.fallback({ url: r.request().url().replace('/portal/my-overview', '/portal/preview/cli-padaria') }),
      )
      const page = await context.newPage()
      await page.goto('/portal/dashboard')
      await expect(page).toHaveURL(/\/portal\/dashboard/)
      await waitForContent(page)
      await expect(page.getByText('Padaria Pão Dourado Ltda').first()).toBeVisible()
      await expectTheme(page, theme)
      await expectNoContrastViolations(page, `/portal/dashboard (${theme})`)
      await context.close()
    })
  })
}
