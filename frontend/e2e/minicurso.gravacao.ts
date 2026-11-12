import { test } from '@playwright/test'
import { Recorder } from './minicurso-gravador'

/**
 * Aulas do Minicurso FiscWise. Cada teste grava uma aula em vídeo, narrada.
 * Rodar com: npm run minicurso:gravar   (ou só uma: npm run minicurso:gravar -- -g "cliente")
 *
 * Os títulos e ids precisam bater com src/lib/minicurso.ts. Cada `r.chapter()`
 * toca a próxima fala de e2e/minicurso-roteiro.ts, na ordem.
 */

/** CSV "exportado do sistema antigo" usado na aula de cadastro. */
const CSV_LINHAS = [
  ['Razão Social', 'CNPJ', 'Regime', 'E-mail', 'Telefone'],
  ['Floricultura Jardim Real Ltda', '23.456.789/0001-10', 'Simples', 'contato@jardimreal.com.br', '(11) 3222-1100'],
  ['Auto Peças Ligeiro Ltda', '34.567.890/0001-21', 'Lucro Presumido', 'fiscal@ligeiro.com.br', '(11) 3444-2200'],
  ['Escola Pequeno Saber Ltda', '45.678.901/0001-32', 'Simples', 'adm@pequenosaber.com.br', '(11) 3555-3300'],
  ['Restaurante Sabor da Terra', '56.789.012/0001-43', 'Simples', 'financeiro@sabordaterra.com.br', '(11) 3666-4400'],
]
const CSV = CSV_LINHAS.map((l) => l.join(';')).join('\r\n')

test('aula 1: primeiros passos', async ({ browser }) => {
  const r = await Recorder.open(browser, {
    id: 'primeiros-passos',
    title: 'Primeiros passos no FiscWise',
    subtitle: 'O tour de boas-vindas, o painel do dia e onde fica cada coisa no menu.',
  })
  const { page } = r
  await r.goto('/painel?tour=1')
  await page.locator('.driver-popover').waitFor()
  await r.titleCard()

  await r.chapter(1800)
  const next = () => page.locator('.driver-popover-next-btn')
  for (let i = 0; i < 10; i++) {
    // i = passo do tour na tela menos 1
    if (!(await next().isVisible().catch(() => false))) break
    await r.wait(350)
    if (i === 1) await r.chapter(300)
    if (i === 8) await r.chapter(300)
    await r.wait(i === 0 ? 1500 : 1900)
    await r.click(next(), { after: 900, zoom: false })
  }
  await r.wait(600)
  // O tour rolou o menu até o fim: volta ao topo para a próxima parte.
  await page.locator('nav[aria-label="Navegação principal"]').evaluate((el) => el.scrollTo({ top: 0, behavior: 'smooth' }))
  await r.wait(500)

  await r.chapter(600)
  const main = page.locator('main')
  await r.hover(main.getByText('Foco de hoje').first(), 1600)
  await r.hover(main.getByText('Obrigações em aberto').first(), 1600)
  await r.hover(main.getByText('Recebíveis').first(), 1600)

  await r.chapter(300)
  await r.click(page.locator('[data-tour="nav-/foco"]'), { after: 2600 })

  await r.chapter(300)
  await r.click(page.locator('[data-tour="ajuda"]'), { after: 2200 })
  await r.hover(page.getByText('Resolver as pendências do dia'), 2200)
  await r.click(page.getByRole('button', { name: 'Fechar ajuda' }), { after: 800 })

  await r.chapter(300)
  await r.click(page.locator('[data-tour="nav-/minicurso"]'), { after: 2400 })
  await r.endCard('Agora cadastre seu primeiro cliente: é a próxima aula.')
  await r.finish()
})

test('aula 2: cadastrar cliente', async ({ browser }) => {
  const r = await Recorder.open(browser, {
    id: 'cadastrar-cliente',
    title: 'Cadastrar clientes',
    subtitle: 'Pelo CNPJ, com os dados da Receita, ou vários de uma vez com planilha Excel ou CSV.',
  })
  const { page } = r
  await r.goto('/clientes')
  await r.titleCard()

  await r.chapter(400)
  await r.hover(page.locator('[data-tour="nav-/clientes"]'), 1000)
  await r.click(page.getByRole('button', { name: 'Novo cliente' }), { after: 1200 })

  await r.chapter(200)
  await r.type(page.locator('#document'), '67.890.123/0001-45', { after: 1600 })
  await r.hover(page.locator('#name'), 1300)
  await r.hover(page.locator('#email'), 1200)

  await r.chapter(300)
  await r.select(page.locator('#tax_regime'), 'Simples Nacional', 1400)

  await r.chapter(200)
  await r.click(page.locator('#phone'), { after: 200 })
  await page.locator('#phone').fill('')
  await page.keyboard.type('(11) 3333-4444', { delay: 60 })
  await r.wait(400)
  await r.type(page.locator('#notes'), 'Cafeteria, 2 lojas. Fechamento até o dia 5.', { delay: 40 })
  await r.click(page.getByRole('button', { name: 'Salvar cliente' }), { after: 1800 })

  await r.chapter(300)
  await r.type(page.getByLabel('Buscar clientes'), 'Grão', { delay: 110, after: 2600 })
  await page.getByLabel('Buscar clientes').fill('')
  await r.wait(600)

  await r.chapter(300)
  await r.showFile('clientes-sistema-antigo.csv', CSV_LINHAS, 3800)
  await r.hover(page.getByRole('button', { name: 'Importar planilha' }), 1400)

  await r.chapter(200)
  await r.hideFile()
  await r.uploadVia(
    page.getByRole('button', { name: 'Importar planilha' }),
    { name: 'clientes-sistema-antigo.csv', mimeType: 'text/csv', buffer: Buffer.from(CSV, 'utf8') },
    1200,
  )
  const relatorio = page.getByRole('dialog', { name: 'Resultado da importação' })
  await relatorio.waitFor()
  await r.hover(relatorio.getByText('4 cadastrado(s)', { exact: false }), 1600)
  await r.hover(relatorio.getByText('Restaurante Sabor da Terra'), 1400)
  await page.keyboard.press('Escape')
  await r.wait(500)
  await r.hover(page.getByText('Floricultura Jardim Real Ltda').first(), 1500)
  await r.endCard('Com o regime certo, o FiscWise já sabe quais obrigações cada cliente tem.')
  await r.finish()
})

test('aula 3: obrigacoes', async ({ browser }) => {
  const r = await Recorder.open(browser, {
    id: 'obrigacoes',
    title: 'Acompanhar as obrigações do mês',
    subtitle: 'Filtrar, iniciar e dar baixa em uma obrigação entregue.',
  })
  const { page } = r
  await r.goto('/obrigacoes')
  await r.titleCard()

  await r.chapter(300)
  await r.hover(page.getByText('Pendentes', { exact: true }), 1300)
  await r.hover(page.getByText('Entregues', { exact: true }), 1100)
  await r.hover(page.getByText('Vencidas', { exact: true }), 1300)

  await r.chapter(300)
  await r.hover(page.getByRole('button', { name: /Gerar automáticas/ }), 2400)

  await r.chapter(200)
  await r.select(page.getByLabel('Filtrar por prioridade'), 'Crítica', 1800)
  await page.getByLabel('Filtrar por prioridade').selectOption({ label: 'Todas prioridades' })

  await r.chapter(200)
  await r.type(page.getByLabel('Buscar obrigações'), 'Padaria', { delay: 90, after: 1000 })

  await r.chapter(300)
  await r.click(page.getByTitle('Iniciar').first(), { after: 2000 })

  await r.chapter(300)
  await r.click(page.getByTitle('Marcar como entregue').first(), { after: 2000 })
  await page.getByLabel('Buscar obrigações').fill('')
  await r.wait(800)
  await r.hover(page.getByText('Entregues', { exact: true }), 1600)
  await r.endCard('Use "Gerar automáticas" no começo do mês para criar as obrigações de todos os clientes.')
  await r.finish()
})

test('aula 4: fechamento mensal', async ({ browser }) => {
  const r = await Recorder.open(browser, {
    id: 'fechamento-mensal',
    title: 'Fazer o fechamento mensal',
    subtitle: 'Concluir o checklist de um cliente e gerar o dossiê em PDF.',
  })
  const { page } = r
  await r.goto('/fechamento')
  await r.titleCard()

  await r.chapter(400)
  await r.hover(page.getByText('Pronto p/ revisão').first(), 1600)

  await r.chapter(300)
  await r.hover(page.getByText('Bloqueado', { exact: true }).first(), 2200)

  await r.chapter(300)
  await r.click(page.locator('a[href="/fechamento/fech-cli-clinica"]'), { after: 2600 })

  await r.chapter(300)
  await r.click(page.getByRole('button', { name: 'Marcar como feito' }).first(), { after: 1600 })
  await r.hover(page.getByText('score', { exact: true }), 1400)

  await r.chapter(300)
  await r.click(page.getByRole('button', { name: /Gerar dossiê/ }), { after: 2600 })
  await r.endCard('O dossiê reúne notas, guias e obrigações do mês em um PDF para o cliente.')
  await r.finish()
})

test('aula 5: certificados', async ({ browser }) => {
  const r = await Recorder.open(browser, {
    id: 'certificados',
    title: 'Cadastrar um certificado digital',
    subtitle: 'Registrar o certificado do cliente e acompanhar o alerta de vencimento.',
  })
  const { page } = r
  await r.goto('/certificados')
  await r.titleCard()

  await r.chapter(1500)

  await r.chapter(300)
  await r.hover(page.getByText('18 dias restantes'), 2600)

  await r.chapter(200)
  await r.click(page.getByRole('button', { name: 'Novo certificado' }).first(), { after: 1000 })
  await r.select(page.locator('#client_id'), 'Oficina Rodas & Cia ME')
  await r.type(page.locator('#label'), 'e-CNPJ Rodas & Cia')

  await r.chapter(200)
  await r.select(page.locator('#certificate_type'), 'A1')
  await r.click(page.locator('#valid_until'), { after: 300 })
  await page.locator('#valid_until').fill('2027-01-20')
  await r.wait(900)
  await r.click(page.getByRole('button', { name: 'Salvar certificado' }), { after: 2000 })

  await r.chapter(300)
  await r.hover(page.getByRole('button', { name: 'Avisar cliente' }).first(), 2000)
  await r.endCard('Você recebe o alerta 30 dias antes e avisa o cliente com um clique.')
  await r.finish()
})

test('aula 6: portal do cliente', async ({ browser }) => {
  const r = await Recorder.open(browser, {
    id: 'portal-cliente',
    title: 'Dar acesso ao portal do cliente',
    subtitle: 'Ver o portal como o cliente vê e enviar o link de acesso por e-mail.',
  })
  const { page } = r
  await r.goto('/portal')
  await r.titleCard()

  await r.chapter(300)
  await r.select(page.getByLabel('Selecionar cliente para visualizar o portal'), 'Padaria Pão Dourado Ltda', 1200)

  await r.chapter(300)
  await r.click(page.getByRole('button', { name: /Guias/ }).first(), { after: 1800 })
  await r.click(page.getByRole('button', { name: /Pendências/ }).first(), { after: 1800 })

  await r.chapter(300)
  await r.click(page.getByRole('button', { name: 'Enviar link de acesso ao portal' }), { after: 1400 })

  await r.chapter(300)
  await r.click(page.getByRole('button', { name: 'Enviar link', exact: true }), { after: 2400 })
  await r.endCard('O cliente entra pelo link, sem senha, e acompanha tudo sozinho.')
  await r.finish()
})
