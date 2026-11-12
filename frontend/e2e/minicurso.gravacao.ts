import { test } from '@playwright/test'
import { Recorder } from './minicurso-gravador'

/**
 * Aulas do Minicurso FiscWise. Cada teste grava uma aula em vídeo.
 * Rodar com: npm run minicurso:gravar   (ou só uma: npm run minicurso:gravar -- -g "cliente")
 *
 * Os títulos e ids precisam bater com src/lib/minicurso.ts.
 */

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

  await r.chapter('No primeiro acesso, um tour mostra as partes mais importantes', 1800)
  const next = () => page.locator('.driver-popover-next-btn')
  for (let i = 0; i < 10; i++) {
    // i = passo do tour na tela menos 1
    if (!(await next().isVisible().catch(() => false))) break
    await r.wait(350)
    if (i === 1) await r.chapter('Painel, Foco de hoje, Clientes, Obrigações e Fechamento ficam no menu', 300)
    if (i === 8) await r.chapter('O botão Ajuda mostra o passo a passo da tela em que você está', 300)
    await r.avoid(page.locator('.driver-popover'))
    await r.wait(i === 0 ? 1500 : 2000)
    await r.click(next(), { after: 900 })
  }
  await r.wait(600)
  // O tour rolou o menu até o fim: volta ao topo para a próxima parte.
  await page.locator('nav[aria-label="Navegação principal"]').evaluate((el) => el.scrollTo({ top: 0, behavior: 'smooth' }))
  await r.wait(500)

  await r.chapter('O painel resume o dia: o que vence, o que está atrasado e quem precisa de atenção', 1200)
  const main = page.locator('main')
  await r.hover(main.getByText('Foco de hoje').first(), 1400)
  await r.hover(main.getByText('Obrigações em aberto').first(), 900)
  await r.hover(main.getByText('Recebíveis').first(), 1200)

  await r.chapter('Clique em Foco de hoje para ver tudo que pede ação, por prioridade')
  await r.click(page.locator('[data-tour="nav-/foco"]'), { after: 2200 })

  await r.chapter('Em qualquer tela, clique em Ajuda para ver como fazer cada tarefa')
  await r.click(page.locator('[data-tour="ajuda"]'), { after: 2600 })
  await r.hover(page.getByText('Resolver as pendências do dia'), 1800)
  await r.click(page.getByRole('button', { name: 'Fechar ajuda' }), { after: 800 })

  await r.chapter('As aulas em vídeo ficam no Minicurso, no fim do menu')
  await r.click(page.locator('[data-tour="nav-/minicurso"]'), { after: 2400 })
  await r.endCard('Agora cadastre seu primeiro cliente: é a próxima aula.')
  await r.finish()
})

test('aula 2: cadastrar cliente', async ({ browser }) => {
  const r = await Recorder.open(browser, {
    id: 'cadastrar-cliente',
    title: 'Cadastrar um cliente',
    subtitle: 'Do CNPJ ao cliente salvo na carteira, com regime tributário e contato.',
  })
  const { page } = r
  await r.goto('/clientes')
  await r.titleCard()

  await r.chapter('Abra Clientes no menu e clique em Novo cliente')
  await r.hover(page.locator('[data-tour="nav-/clientes"]'), 700)
  await r.click(page.getByRole('button', { name: 'Novo cliente' }), { after: 1000 })

  await r.chapter('Digite o CNPJ: a razão social e o contato vêm da Receita')
  await r.type(page.locator('#document'), '67.890.123/0001-45', { after: 1800 })
  await r.hover(page.locator('#name'), 1200)

  await r.chapter('Confira o tipo e escolha o regime tributário')
  await r.select(page.locator('#tax_regime'), 'Simples Nacional')

  await r.chapter('Complete os dados que faltarem')
  await r.click(page.locator('#phone'), { after: 200 })
  await page.locator('#phone').fill('')
  await page.keyboard.type('(11) 3333-4444', { delay: 60 })
  await r.wait(400)
  await r.type(page.locator('#notes'), 'Cafeteria, 2 lojas. Fechamento até o dia 5.', { delay: 45 })

  await r.chapter('Clique em Salvar cliente')
  await r.click(page.getByRole('button', { name: 'Salvar cliente' }), { after: 2200 })

  await r.chapter('O cliente já aparece na carteira. Busque pelo nome ou CNPJ')
  await r.type(page.getByLabel('Buscar clientes'), 'Grão', { delay: 110, after: 2400 })
  await r.endCard('Com o regime certo, o FiscWise já sabe quais obrigações esse cliente tem.')
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

  await r.chapter('Obrigações mostra tudo que vence na competência escolhida')
  await r.hover(page.getByText('Pendentes', { exact: true }), 900)
  await r.hover(page.getByText('Vencidas', { exact: true }), 1100)

  await r.chapter('Filtre por status ou prioridade para focar no urgente')
  await r.select(page.getByLabel('Filtrar por prioridade'), 'Crítica')
  await r.wait(1200)
  await r.select(page.getByLabel('Filtrar por prioridade'), 'Todas prioridades')

  await r.chapter('Busque pela obrigação ou pelo cliente')
  await r.type(page.getByLabel('Buscar obrigações'), 'Padaria', { delay: 90, after: 1400 })

  await r.chapter('Clique em Iniciar quando começar a trabalhar nela')
  await r.click(page.getByTitle('Iniciar').first(), { after: 1800 })

  await r.chapter('Entregou? Clique no ✓ para dar baixa')
  await r.click(page.getByTitle('Marcar como entregue').first(), { after: 2200 })
  await page.getByLabel('Buscar obrigações').fill('')
  await r.wait(1200)
  await r.hover(page.getByText('Entregues', { exact: true }), 1400)
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

  await r.chapter('Cada cliente tem o fechamento da competência, com score e bloqueios')
  await r.hover(page.getByText('Bloqueado', { exact: true }).first(), 1200)
  await r.hover(page.getByText('Pronto p/ revisão').first(), 1000)

  await r.chapter('Clique em Abrir no cliente que você vai fechar')
  await r.click(page.locator('a[href="/fechamento/fech-cli-clinica"]'), { after: 2000 })

  await r.chapter('Marque como feita cada etapa do checklist')
  await r.click(page.getByRole('button', { name: 'Marcar como feito' }).first(), { after: 2200 })
  await r.hover(page.getByText('score', { exact: true }), 1400)

  await r.chapter('Com tudo pronto, clique em Gerar dossiê')
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

  await r.chapter('Certificados mostra a validade de cada certificado dos clientes')
  await r.hover(page.getByText('18 dias restantes'), 1500)

  await r.chapter('Clique em Novo certificado')
  await r.click(page.getByRole('button', { name: 'Novo certificado' }).first(), { after: 1000 })

  await r.chapter('Escolha o cliente e dê um nome ao certificado')
  await r.select(page.locator('#client_id'), 'Oficina Rodas & Cia ME')
  await r.type(page.locator('#label'), 'e-CNPJ Rodas & Cia')

  await r.chapter('Informe o tipo e a data de vencimento')
  await r.select(page.locator('#certificate_type'), 'A1')
  await r.click(page.locator('#valid_until'), { after: 300 })
  await page.locator('#valid_until').fill('2027-01-20')
  await r.wait(900)

  await r.chapter('Clique em Salvar certificado')
  await r.click(page.getByRole('button', { name: 'Salvar certificado' }), { after: 2400 })

  await r.chapter('Vencendo em até 30 dias? Clique em Avisar cliente')
  await r.hover(page.getByRole('button', { name: 'Avisar cliente' }).first(), 1600)
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

  await r.chapter('Escolha o cliente para ver o portal como ele vê')
  await r.select(page.getByLabel('Selecionar cliente para visualizar o portal'), 'Padaria Pão Dourado Ltda')
  await r.wait(800)

  await r.chapter('Confira guias e pendências que o cliente vai ver')
  await r.click(page.getByRole('button', { name: /Guias/ }).first(), { after: 1600 })
  await r.click(page.getByRole('button', { name: /Pendências/ }).first(), { after: 1600 })

  await r.chapter('Clique em Enviar link de acesso ao portal')
  await r.click(page.getByRole('button', { name: 'Enviar link de acesso ao portal' }), { after: 1200 })

  await r.chapter('Confira o e-mail e clique em Enviar link')
  await r.click(page.getByRole('button', { name: 'Enviar link', exact: true }), { after: 2400 })
  await r.endCard('O cliente entra pelo link, sem senha, e acompanha tudo sozinho.')
  await r.finish()
})
