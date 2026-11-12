import type { BrowserContext, Route } from '@playwright/test'

/**
 * API de demonstração do Minicurso FiscWise.
 *
 * Responde, em memória, às rotas que as aulas gravadas usam (painel, clientes,
 * obrigações, fechamento, certificados, portal). Nada sai da máquina: os dados
 * são fictícios e as escritas (POST/PATCH e /sync/push) valem só durante a
 * gravação, para a tela mostrar o registro salvo como no app real.
 */

const TENANT = 'demo-tenant'
const iso = (d: Date) => d.toISOString().slice(0, 10)
const today = new Date()
const addDays = (n: number) => {
  const d = new Date(today)
  d.setDate(d.getDate() + n)
  return iso(d)
}
const competence = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}`
const prev = new Date(today.getFullYear(), today.getMonth() - 1, 1)
const prevCompetence = `${prev.getFullYear()}-${String(prev.getMonth() + 1).padStart(2, '0')}`
const now = () => new Date().toISOString()

type Row = Record<string, unknown> & { id: string }

const base = { tenant_id: TENANT, created_at: '2026-09-01T12:00:00.000Z', updated_at: '2026-09-01T12:00:00.000Z', version: 1 }

/** Catálogo como o servidor devolve (tabela_precos só no essencial para a tela). */
const linhas = (m: number) =>
  ([['mensal', 'Mensal', 1, 0, 1], ['trimestral', 'Trimestral', 3, 15, 3], ['semestral', 'Semestral', 6, 15, 6], ['anual', 'Anual', 12, 15, 6]] as const).map(
    ([ciclo, label, meses, pix, parc]) => ({
      ciclo, label, meses, preco_cheio: m * meses, pix_total: Math.round(m * meses * (1 - pix / 100) * 100) / 100,
      desconto_pix_pct: pix, cartao_total: m * meses, desconto_cartao_pct: 0, cartao_max_parcelas: parc,
      cartao_parcela: Math.round(((m * meses) / parc) * 100) / 100, obs: '',
    }),
  )
export const DEMO_PLANS = [
  { id: 'plan-free', slug: 'free', name: 'Gratuito', description: 'Para experimentar.', price_monthly: 0, max_clients: 10, max_users: 2, max_ai_calls_month: 0, features: { calculator: true }, tabela_precos: null },
  { id: 'plan-intermediario', slug: 'intermediario', name: 'Intermediário', description: 'Para escritórios em crescimento.', price_monthly: 149, max_clients: 80, max_users: 5, max_ai_calls_month: 20, features: { calculator: true, portal_cliente: true, obrigacoes: true }, tabela_precos: linhas(149) },
  { id: 'plan-premium', slug: 'premium', name: 'Premium', description: 'Sem limites.', price_monthly: 349, max_clients: null, max_users: null, max_ai_calls_month: null, features: { calculator: true, pdf_export: true, portal_cliente: true, obrigacoes: true }, tabela_precos: linhas(349) },
  { id: 'plan-enterprise', slug: 'enterprise', name: 'Enterprise', description: 'Contrato personalizado.', price_monthly: null, max_clients: null, max_users: null, max_ai_calls_month: null, features: { enterprise: true }, tabela_precos: null },
]

export const DEMO_USER = {
  id: 'demo-user',
  email: 'ana@contabilidadeexemplo.com.br',
  full_name: 'Ana Ribeiro',
  role: 'owner',
}

function seedClients(): Row[] {
  const c = (id: string, code: string, name: string, document: string, tax_regime: string, email: string, fee: number, status = 'active') => ({
    ...base, id, client_code: code, name, document, entity_type: 'pj', tax_regime, email, phone: '(11) 3333-0000',
    status, monthly_fee: fee, billing_day: 10, notes: null,
  })
  return [
    c('cli-padaria', 'C001', 'Padaria Pão Dourado Ltda', '12.345.678/0001-90', 'Simples Nacional', 'financeiro@paodourado.com.br', 850),
    c('cli-clinica', 'C002', 'Clínica Sorriso Odontologia Ltda', '23.456.789/0001-01', 'Lucro Presumido', 'adm@clinicasorriso.com.br', 1600),
    c('cli-oficina', 'C003', 'Oficina Rodas & Cia ME', '34.567.890/0001-12', 'Simples Nacional', 'contato@rodasecia.com.br', 650),
    c('cli-mercado', 'C004', 'Mercado Bom Preço Ltda', '45.678.901/0001-23', 'Lucro Real', 'fiscal@bompreco.com.br', 2400),
    c('cli-studio', 'C005', 'Studio Fit Academia Ltda', '56.789.012/0001-34', 'Simples Nacional', 'ola@studiofit.com.br', 700, 'onboarding'),
  ]
}

function seedDeadlines(): Row[] {
  const d = (id: string, client_id: string, title: string, category: string, due: number, status = 'pending', priority = 'medium') => ({
    ...base, id, client_id, title, category, due_date: addDays(due), status, priority, description: null,
    completed_at: null, is_recurring: true, recurrence_interval: 'monthly', recurrence_parent_id: null,
  })
  return [
    d('dl-1', 'cli-padaria', 'DAS Simples Nacional', 'tributo', 3, 'pending', 'high'),
    d('dl-2', 'cli-clinica', 'DCTFWeb', 'declaracao', 2, 'pending', 'high'),
    d('dl-3', 'cli-mercado', 'EFD-Reinf', 'declaracao', 5),
    d('dl-4', 'cli-oficina', 'FGTS Digital', 'tributo', -1, 'overdue', 'high'),
    d('dl-5', 'cli-studio', 'Envio da folha de pagamento', 'folha', 6),
  ]
}

function seedCertificates(): Row[] {
  const c = (id: string, client_id: string, label: string, until: number, status: string) => ({
    ...base, id, client_id, label, certificate_type: 'A1', valid_from: addDays(until - 365), valid_until: addDays(until), status, notes: null,
  })
  return [
    c('cert-1', 'cli-padaria', 'e-CNPJ Pão Dourado', 18, 'expiring'),
    c('cert-2', 'cli-clinica', 'e-CNPJ Clínica Sorriso', 210, 'valid'),
    c('cert-3', 'cli-mercado', 'e-CNPJ Bom Preço', 95, 'valid'),
  ]
}

function seedReceivables(): Row[] {
  const r = (id: string, client_id: string, amount: number, due: number, status: string) => ({
    ...base, id, client_id, description: `Honorários ${competence}`, amount, due_date: addDays(due), status, paid_at: status === 'paid' ? now() : null, notes: null,
  })
  return [
    r('rec-1', 'cli-padaria', 850, -2, 'paid'),
    r('rec-2', 'cli-clinica', 1600, -2, 'paid'),
    r('rec-3', 'cli-oficina', 650, -5, 'overdue'),
    r('rec-4', 'cli-mercado', 2400, 8, 'pending'),
  ]
}

const RULES = [
  { id: 'rule-das', code: 'DAS', name: 'DAS Simples Nacional', description: 'Guia mensal do Simples Nacional', jurisdiction: 'federal', recurrence: 'monthly', due_day: 20, active: true },
  { id: 'rule-dctfweb', code: 'DCTFWEB', name: 'DCTFWeb', description: 'Declaração de débitos e créditos previdenciários', jurisdiction: 'federal', recurrence: 'monthly', due_day: 15, active: true },
  { id: 'rule-reinf', code: 'REINF', name: 'EFD-Reinf', description: 'Escrituração de retenções', jurisdiction: 'federal', recurrence: 'monthly', due_day: 15, active: true },
  { id: 'rule-iss', code: 'ISS', name: 'ISS municipal', description: 'Imposto sobre serviços', jurisdiction: 'municipal', recurrence: 'monthly', due_day: 10, active: true },
  { id: 'rule-icms', code: 'ICMS', name: 'GIA / ICMS', description: 'Apuração estadual do ICMS', jurisdiction: 'estadual', recurrence: 'monthly', due_day: 12, active: true },
]

function seedObligations(): Row[] {
  const o = (id: string, client_id: string, rule_id: string, due: number, status: string, priority: string) => ({
    id, client_id, rule_id, competence_month: `${competence}-01`, due_date: addDays(due), status, priority,
    assigned_to: 'Ana Ribeiro', notes: null, custom_name: null, completed_at: status === 'delivered' ? now() : null, created_at: base.created_at,
  })
  return [
    o('obl-1', 'cli-padaria', 'rule-das', 3, 'pending', 'high'),
    o('obl-2', 'cli-clinica', 'rule-dctfweb', 2, 'in_progress', 'high'),
    o('obl-3', 'cli-clinica', 'rule-iss', -2, 'delivered', 'medium'),
    o('obl-4', 'cli-mercado', 'rule-reinf', 5, 'pending', 'medium'),
    o('obl-5', 'cli-mercado', 'rule-icms', 1, 'pending', 'critical'),
    o('obl-6', 'cli-oficina', 'rule-das', -1, 'overdue', 'critical'),
    o('obl-7', 'cli-studio', 'rule-das', 8, 'pending', 'low'),
  ]
}

const CHECKLIST_LABELS = [
  'Receber extratos bancários',
  'Conferir notas fiscais de entrada e saída',
  'Apurar impostos do mês',
  'Emitir e enviar guias ao cliente',
  'Entregar obrigações acessórias',
  'Revisar e aprovar o fechamento',
]

function seedClosings(clients: Row[]): Row[] {
  const statuses = ['in_progress', 'ready_for_review', 'blocked', 'in_progress', 'not_started']
  return clients.map((cl, i) => {
    const doneCount = [3, 5, 1, 2, 0][i] ?? 0
    return {
      id: `fech-${cl.id}`,
      tenant_id: TENANT,
      client_id: cl.id,
      client_name: cl.name,
      client_cnpj: cl.document,
      competence: prevCompetence,
      status: statuses[i] ?? 'not_started',
      score: Math.round((doneCount / CHECKLIST_LABELS.length) * 100),
      blockers: statuses[i] === 'blocked' ? ['Extrato bancário de outubro não recebido'] : [],
      checklist: CHECKLIST_LABELS.map((label, j) => ({
        id: `${cl.id}-item-${j}`,
        label,
        status: j < doneCount ? 'done' : statuses[i] === 'blocked' && j === 0 ? 'blocked' : 'pending',
        notes: null,
        completed_at: j < doneCount ? now() : null,
      })),
      invoices_count: 42 - i * 6,
      invoices_pending: i === 2 ? 3 : 0,
      guides_count: 3,
      guides_paid: Math.min(3, doneCount),
      obligations_total: 4,
      obligations_done: Math.min(4, doneCount),
      ecac_pendencies: i === 2 ? 1 : 0,
      documents_total: 6,
      documents_received: Math.min(6, doneCount + 2),
      dossier_generated_at: null,
      created_at: base.created_at,
      updated_at: base.updated_at,
    }
  })
}

function recomputeClosing(c: Row) {
  const list = c.checklist as Array<{ status: string }>
  const done = list.filter((i) => i.status === 'done' || i.status === 'na').length
  c.score = Math.round((done / list.length) * 100)
  if (done === list.length) c.status = 'ready_for_review'
  else if (c.status === 'not_started') c.status = 'in_progress'
  c.updated_at = now()
}

const FOCUS = () => [
  { id: 'f1', group: 'critical', type: 'obligation', title: 'FGTS Digital em atraso', client: 'Oficina Rodas & Cia ME', competence, deadline: addDays(-1), risk: 'critical', status: 'Vencida', responsible: 'Ana Ribeiro', primary_action: { label: 'Resolver', href: '/obrigacoes' } },
  { id: 'f2', group: 'today', type: 'certificate', title: 'Certificado A1 vence em 18 dias', client: 'Padaria Pão Dourado Ltda', competence: null, deadline: addDays(18), risk: 'high', status: 'Vencendo', responsible: 'Ana Ribeiro', primary_action: { label: 'Renovar', href: '/certificados' } },
  { id: 'f3', group: 'today', type: 'obligation', title: 'GIA / ICMS vence amanhã', client: 'Mercado Bom Preço Ltda', competence, deadline: addDays(1), risk: 'high', status: 'Pendente', responsible: 'Ana Ribeiro', primary_action: { label: 'Abrir', href: '/obrigacoes' } },
  { id: 'f4', group: 'week', type: 'closing', title: 'Fechamento pronto para revisão', client: 'Clínica Sorriso Odontologia Ltda', competence: prevCompetence, deadline: addDays(4), risk: 'medium', status: 'Revisão', responsible: 'Ana Ribeiro', primary_action: { label: 'Revisar', href: '/fechamento' } },
  { id: 'f5', group: 'waiting_client', type: 'document', title: 'Extrato bancário de outubro', client: 'Oficina Rodas & Cia ME', competence: prevCompetence, deadline: addDays(2), risk: 'medium', status: 'Aguardando cliente', responsible: 'Ana Ribeiro', primary_action: { label: 'Cobrar', href: '/documentos' } },
]

const DOCUMENTS = () => [
  { ...base, id: 'doc-1', client_id: 'cli-padaria', name: 'Extrato Itaú outubro.pdf', document_type: 'extrato', status: 'available', file_url: null, issued_at: addDays(-6), expires_at: null, notes: null, parse_status: 'done', parsed_data: null },
  { ...base, id: 'doc-2', client_id: 'cli-clinica', name: 'Notas de serviço outubro.xml', document_type: 'nfse', status: 'review', file_url: null, issued_at: addDays(-4), expires_at: null, notes: null, parse_status: 'done', parsed_data: null },
  { ...base, id: 'doc-3', client_id: 'cli-oficina', name: 'Extrato bancário outubro', document_type: 'extrato', status: 'missing', file_url: null, issued_at: null, expires_at: null, notes: 'Pedido ao cliente pelo portal', parse_status: null, parsed_data: null },
  { ...base, id: 'doc-4', client_id: 'cli-mercado', name: 'Alvará de funcionamento.pdf', document_type: 'alvara', status: 'available', file_url: null, issued_at: addDays(-200), expires_at: addDays(160), notes: null, parse_status: 'done', parsed_data: null },
]

export interface DemoApi {
  /** Rotas pedidas que não têm resposta específica (para ajustar o mock). */
  unknown: Set<string>
}

/** Instala a API de demonstração e a sessão fictícia do contador no contexto. */
export async function installDemoApi(context: BrowserContext): Promise<DemoApi> {
  const tables: Record<string, Row[]> = {
    clients: seedClients(),
    deadlines: seedDeadlines(),
    certificates: seedCertificates(),
    receivables: seedReceivables(),
    invoices: [],
  }
  const obligations = seedObligations()
  const closings = seedClosings(tables.clients)
  const unknown = new Set<string>()

  await context.addInitScript(
    ({ user, tenant }) => {
      localStorage.setItem('access_token', 'demo-token')
      localStorage.setItem('tenant_id', tenant)
      localStorage.setItem('user', JSON.stringify(user))
      // As aulas mostram cada tela; o tour de boas-vindas tem aula própria.
      if (!location.search.includes('tour=1')) localStorage.setItem(`fiscwise:tour-boas-vindas:${user.id}`, 'done')
    },
    { user: DEMO_USER, tenant: TENANT },
  )

  const clientName = (id: unknown) => (tables.clients.find((c) => c.id === id)?.name as string) ?? 'Cliente'

  const overview = () => ({
    active_clients: tables.clients.filter((c) => c.status !== 'inactive').length,
    pending_deadlines: obligations.filter((o) => o.status === 'pending' || o.status === 'in_progress').length,
    overdue_deadlines: obligations.filter((o) => o.status === 'overdue').length,
    certificates_expiring_30d: 1,
    open_receivables: 2,
    overdue_receivables: 1,
    receivables_amount_open: 3050,
    receivables_amount_overdue: 650,
    upcoming_deadlines: tables.deadlines,
    total_received_month: 2450,
    monthly_received: [
      { mes: 'Jun', valor: 5200 }, { mes: 'Jul', valor: 5600 }, { mes: 'Ago', valor: 5900 },
      { mes: 'Set', valor: 6100 }, { mes: 'Out', valor: 6200 }, { mes: 'Nov', valor: 2450 },
    ],
    weekly_received: [],
    recent_receivables: tables.receivables.map((r) => ({ ...r, client_name: clientName(r.client_id) })),
  })

  const productivity = () => ({
    competence_month: competence,
    compliance_rate: 86,
    total_pending: 4,
    total_in_progress: 1,
    total_delivered: 1,
    total_overdue: 1,
    total_blocked: 0,
    obligations_by_collaborator: [
      { user_id: 'demo-user', user_name: 'Ana Ribeiro', pending: 3, in_progress: 1, delivered: 1, overdue: 1, total: 6 },
      { user_id: 'u2', user_name: 'Bruno Lima', pending: 1, in_progress: 0, delivered: 0, overdue: 0, total: 1 },
    ],
    clients_with_most_pending: [
      { client_id: 'cli-mercado', client_name: 'Mercado Bom Preço Ltda', pending_count: 2 },
      { client_id: 'cli-oficina', client_name: 'Oficina Rodas & Cia ME', pending_count: 1 },
    ],
    pending_documents: [{ id: 'doc-3', client_name: 'Oficina Rodas & Cia ME', document_name: 'Extrato bancário outubro', days_waiting: 4, status: 'missing' }],
    docs_awaiting_approval: 1,
    certificates_expiring_30d: 1,
    overdue_receivables_count: 1,
    overdue_receivables_amount: 650,
  })

  const json = (route: Route, body: unknown, status = 200) =>
    route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) })

  const handle = async (route: Route) => {
    const req = route.request()
    const url = new URL(req.url())
    const path = url.pathname
    const method = req.method()
    const body = (() => {
      try {
        return req.postDataJSON() as Record<string, unknown>
      } catch {
        return {}
      }
    })()

    // ── Sincronização offline-first ──
    if (path === '/api/v1/sync/devices' && method === 'POST') {
      return json(route, { device: { id: 'demo-device', name: 'Navegador', platform: 'web', app_version: '1', last_seen_at: now(), revoked_at: null, created_at: now(), user_id: DEMO_USER.id }, device_token: 'demo-device-token' })
    }
    if (path === '/api/v1/sync/devices/token') return json(route, { device_token: 'demo-device-token', access_token: 'demo-token', tenant_id: TENANT })
    if (path === '/api/v1/sync/pull') {
      const entity = url.searchParams.get('entity') ?? ''
      const rows = url.searchParams.get('since') ? [] : tables[entity] ?? []
      return json(route, { rows, next: { since: rows.length ? now() : url.searchParams.get('since'), after_id: null }, has_more: false })
    }
    if (path === '/api/v1/sync/push') {
      const events = (body.events as Array<Record<string, unknown>>) ?? []
      const acks = events.map((e) => {
        const table = tables[`${e.entity_type}s`] ?? (tables[`${e.entity_type}s`] = [])
        let row = table.find((r) => r.id === e.entity_id)
        if (!row) {
          row = { ...base, ...(e.payload as object), id: e.entity_id as string, created_at: now(), updated_at: now() }
          if (e.entity_type === 'client' && !row.client_code) row.client_code = `C${String(table.length + 1).padStart(3, '0')}`
          table.push(row)
        } else {
          Object.assign(row, e.payload as object, { version: (row.version as number) + 1, updated_at: now() })
        }
        return { id: e.id, status: 'ack', entity: { ...row } }
      })
      return json(route, { acks })
    }

    // ── Sessão / escritório ──
    if (path === '/api/v1/auth/me') return json(route, { ...DEMO_USER, phone: '(11) 98888-0000' })
    if (path === '/api/v1/auth/tenant') {
      return json(route, { id: TENANT, name: 'Ribeiro Contabilidade', document: '40.204.602/0001-85', email: DEMO_USER.email, phone: '(11) 3333-0000', address: 'Av. Paulista, 1000 - São Paulo/SP', crc: 'SP-123456/O-7', plan: 'pro' })
    }

    // ── Painel e foco ──
    if (path === '/api/v1/dashboard/overview') return json(route, overview())
    if (path === '/api/v1/dashboard/productivity') return json(route, productivity())
    if (path === '/api/v1/focus') return json(route, { items: FOCUS() })

    // ── Cadastros REST (espelham o banco local) ──
    for (const name of ['clients', 'deadlines', 'certificates', 'receivables'] as const) {
      const prefix = `/api/v1/${name}`
      if (path === prefix && method === 'GET') return json(route, tables[name])
      if (path === prefix && method === 'POST') {
        const row = { ...base, id: `${name}-${Date.now()}`, ...body, created_at: now(), updated_at: now() }
        tables[name].push(row)
        return json(route, row, 201)
      }
      if (path.startsWith(`${prefix}/`)) {
        const id = path.slice(prefix.length + 1).split('/')[0]
        const row = tables[name].find((r) => r.id === id)
        if (path.split('/').length === 5) {
          if (method === 'GET') return row ? json(route, row) : json(route, { detail: 'Não encontrado' }, 404)
          if (method === 'PATCH' || method === 'PUT') return json(route, Object.assign(row ?? {}, body, { updated_at: now() }))
        }
      }
    }

    // ── Obrigações ──
    if (path === '/api/v1/obligations/rules') return json(route, RULES)
    if (path === '/api/v1/obligations/instances' && method === 'GET') return json(route, obligations)
    if (path === '/api/v1/obligations/instances' && method === 'POST') {
      const row = { id: `obl-${Date.now()}`, status: 'pending', priority: 'medium', assigned_to: null, notes: null, completed_at: null, created_at: now(), ...body }
      obligations.push(row as Row)
      return json(route, row, 201)
    }
    if (path.startsWith('/api/v1/obligations/instances/') && method === 'PATCH') {
      const row = obligations.find((o) => o.id === path.split('/').pop())
      if (row) {
        Object.assign(row, body)
        if (body.status === 'delivered') row.completed_at = now()
      }
      return json(route, row ?? {})
    }
    if (path === '/api/v1/obligations/generate') return json(route, { created: 0, skipped: obligations.length })

    // ── Fechamento mensal ──
    if (path === '/api/v1/monthly-closing' && method === 'GET') return json(route, closings)
    if (path === '/api/v1/monthly-closing/generate') return json(route, { competence: prevCompetence, created: 0, skipped: closings.length })
    const closingMatch = path.match(/^\/api\/v1\/monthly-closing\/([^/]+)(\/.*)?$/)
    if (closingMatch) {
      const closing = closings.find((c) => c.id === closingMatch[1])
      const rest = closingMatch[2] ?? ''
      if (!closing) return json(route, { detail: 'Não encontrado' }, 404)
      if (!rest && method === 'GET') return json(route, closing)
      const itemMatch = rest.match(/^\/checklist\/(.+)$/)
      if (itemMatch && method === 'PATCH') {
        const item = (closing.checklist as Array<Record<string, unknown>>).find((i) => i.id === itemMatch[1])
        if (item) Object.assign(item, body, { completed_at: body.status === 'done' ? now() : null })
        recomputeClosing(closing)
        return json(route, closing)
      }
      if (rest.startsWith('/dossier')) {
        closing.dossier_generated_at = now()
        if (rest.endsWith('.pdf')) return route.fulfill({ status: 200, contentType: 'application/pdf', body: '%PDF-1.4\n%demo\n' })
        return json(route, { url: null, generated_at: closing.dossier_generated_at })
      }
      if (method === 'PATCH' || method === 'POST') {
        Object.assign(closing, body, { updated_at: now() })
        return json(route, closing)
      }
    }

    // ── Documentos ──
    if (path === '/api/v1/documents') return json(route, DOCUMENTS())

    // ── Portal do cliente ──
    const preview = path.match(/^\/api\/v1\/portal\/preview\/(.+)$/)
    if (preview) {
      const cl = tables.clients.find((c) => c.id === preview[1]) ?? tables.clients[0]
      const closing = closings.find((c) => c.client_id === cl.id)
      return json(route, {
        client: { id: cl.id, name: cl.name, document: cl.document },
        closing: closing ? { id: closing.id, competence: closing.competence, status: closing.status, score: closing.score } : null,
        documents: [
          { id: 'pd-1', name: 'Extrato bancário de outubro', status: 'requested', requested_at: addDays(-3) },
          { id: 'pd-2', name: 'Notas de compra de outubro', status: 'received', requested_at: addDays(-6) },
        ],
        guides: [
          { id: 'pg-1', type: 'DAS', competence: prevCompetence, value: 1287.45, due: addDays(8), status: 'pending' },
          { id: 'pg-2', type: 'FGTS', competence: prevCompetence, value: 412.3, due: addDays(-1), status: 'paid' },
        ],
        pendencies: [{ id: 'pp-1', title: 'Enviar extrato bancário de outubro', deadline: addDays(2), status: 'pending' }],
      })
    }
    if (path === '/api/v1/portal/magic-link/request') {
      return json(route, { sent: true, delivery: 'email', email: (body.email as string) || 'financeiro@paodourado.com.br', expires_at: addDays(7) })
    }

    // ── Plano e assinatura ──
    if (path === '/api/v1/subscription/plans') return json(route, DEMO_PLANS)
    if (path === '/api/v1/subscription/usage') {
      return json(route, {
        plan_slug: 'intermediario', plan_name: 'Intermediário',
        clients: { used: 5, limit: 80, percent: 6.3 }, users: { used: 1, limit: 5, percent: 20 },
        ai_calls_this_month: { used: 3, limit: 20, percent: 15 }, features: {},
      })
    }
    if (path === '/api/v1/billing/subscription') {
      return json(route, {
        id: 'sub-demo', tenant_id: TENANT, plan_id: 'plan-intermediario', billing_provider: 'mercadopago',
        status: 'active', current_period_end: addDays(18), trial_ends_at: null, amount: '149.00',
        currency: 'BRL', created_at: now(), billing_cycle: 'mensal', cancelled_at: null,
      })
    }
    if (path === '/api/v1/billing/config') return json(route, { gateway: 'mercadopago', public_key: '', go_live: false })

    // ── Financeiro ──
    if (path === '/api/v1/financeiro/inadimplencia') {
      return json(route, { total_overdue: 650, clients: [{ client_id: 'cli-oficina', client_name: 'Oficina Rodas & Cia ME', overdue_amount: 650, overdue_count: 1, oldest_due_date: addDays(-5) }] })
    }

    // ── Relatórios ──
    if (path === '/api/v1/reports/operational') {
      return json(route, {
        competence: url.searchParams.get('competence') ?? competence,
        clients_by_status: { active: 4, onboarding: 1, inactive: 0, total: 5 },
        obligations_by_status: { delivered: 1, pending: 4, in_progress: 1, overdue: 1, total: 7 },
        guias_by_status: { paid: 6, awaiting: 3, overdue: 1, total: 10 },
        closings_by_status: { completed: 0, in_progress: 2, blocked: 1, not_started: 1, total: 5 },
        invoices_by_status: { issued: 120, rejected: 2, cancelled: 1, total: 123 },
        proxies_expiring: { d30: 1, d60: 0, d90: 1, total: 2 },
      })
    }
    if (path === '/api/v1/reports/summary') {
      return json(route, {
        competence: url.searchParams.get('competence') ?? competence,
        revenue_billed: 6200, revenue_received: 2450, overdue_amount: 650,
        overdue_clients: 1, active_clients: 4, new_clients_month: 1,
      })
    }

    unknown.add(`${method} ${path}`)
    return json(route, method === 'GET' ? [] : {})
  }

  await context.route(/fiscwise-api-[^/]*\.run\.app|localhost:8000/, handle)
  // Consulta de CNPJ (BrasilAPI) usada no cadastro de cliente: resposta fixa.
  await context.route(/brasilapi\.com\.br/, (route) =>
    json(route, {
      cnpj: '67890123000145',
      razao_social: 'CAFETERIA GRÃO NOBRE LTDA',
      nome_fantasia: 'Grão Nobre',
      email: 'contato@graonobre.com.br',
      ddd_telefone_1: '1133334444',
      opcao_pelo_simples: true,
      opcao_pelo_mei: false,
      descricao_situacao_cadastral: 'ATIVA',
      municipio: 'SAO PAULO',
      uf: 'SP',
    }),
  )
  return { unknown }
}
