import { MailboxMessage } from './types';

const MOCK_MESSAGES: MailboxMessage[] = [
  {
    id: 'msg-001',
    clientId: 'cli-001',
    clientName: 'Tech Solutions Ltda',
    clientCnpj: '12.345.678/0001-90',
    subject: 'Intimação — Malha Fina IRPJ 2023',
    summary: 'Contribuinte apresentou divergência na declaração de IRPJ. Prazo de 30 dias para resposta.',
    body: `Prezado contribuinte,\n\nIdentificamos divergências na sua Declaração de IRPJ relativa ao exercício 2023. Os rendimentos informados diferem dos valores cruzados com as fontes pagadoras.\n\nVocê tem 30 dias a partir desta data para apresentar documentação comprobatória ou retificar a declaração.\n\nCase não haja manifestação, o processo seguirá para lançamento de ofício.`,
    organ: 'Receita Federal',
    receivedAt: '2026-05-20T09:00:00Z',
    deadline: '2026-06-20T23:59:00Z',
    risk: 'critical',
    status: 'unread',
    taskCreated: false,
    obligationLinked: null,
    tags: ['IRPJ', 'malha-fina', 'intimação'],
  },
  {
    id: 'msg-002',
    clientId: 'cli-002',
    clientName: 'Comércio São Paulo ME',
    clientCnpj: '98.765.432/0001-11',
    subject: 'Débito Automático — DAS Maio/2026',
    summary: 'Confirmação de débito automático do DAS Simples Nacional referente a Maio/2026.',
    body: `DAS Simples Nacional — Competência 05/2026\n\nValor: R$ 1.240,00\nVencimento: 20/06/2026\nSituação: Agendado para débito automático`,
    organ: 'PGFN',
    receivedAt: '2026-05-22T08:30:00Z',
    deadline: '2026-06-20T23:59:00Z',
    risk: 'low',
    status: 'read',
    taskCreated: true,
    obligationLinked: 'obl-das-0526',
    tags: ['DAS', 'Simples Nacional'],
  },
  {
    id: 'msg-003',
    clientId: 'cli-003',
    clientName: 'Construtora Horizonte SA',
    clientCnpj: '11.222.333/0001-44',
    subject: 'Notificação — Parcelamento REFIS pendente',
    summary: 'Parcela de parcelamento REFIS vencida. Risco de exclusão do programa.',
    body: `Sua parcela do parcelamento REFIS venceu em 15/05/2026.\n\nValor: R$ 4.750,00\n\nA não regularização em até 15 dias resultará na exclusão do programa de parcelamento e inclusão do débito na dívida ativa.`,
    organ: 'PGFN',
    receivedAt: '2026-05-18T14:00:00Z',
    deadline: '2026-06-02T23:59:00Z',
    risk: 'high',
    status: 'in_progress',
    taskCreated: true,
    obligationLinked: null,
    tags: ['REFIS', 'parcelamento', 'PGFN'],
  },
  {
    id: 'msg-004',
    clientId: 'cli-004',
    clientName: 'Clínica Saúde Total Ltda',
    clientCnpj: '55.666.777/0001-22',
    subject: 'Consulta situação fiscal — OK',
    summary: 'Situação fiscal regularizada. Certidão Negativa emitida com sucesso.',
    body: `Situação fiscal verificada em 25/05/2026.\n\nStatus: REGULAR\n\nCertidão Negativa de Débitos (CND) emitida com validade até 24/11/2026.`,
    organ: 'Receita Federal',
    receivedAt: '2026-05-25T10:15:00Z',
    deadline: null,
    risk: 'none',
    status: 'resolved',
    taskCreated: false,
    obligationLinked: null,
    tags: ['CND', 'situação-fiscal'],
  },
  {
    id: 'msg-005',
    clientId: 'cli-001',
    clientName: 'Tech Solutions Ltda',
    clientCnpj: '12.345.678/0001-90',
    subject: 'Alerta — Procuração e-CAC vencendo',
    summary: 'Procuração digital vence em 15 dias. Necessário renovação para acesso aos serviços.',
    body: `A procuração digital registrada no e-CAC para acesso aos serviços da Receita Federal vence em 10/06/2026.\n\nServiços afetados:\n- Consulta de pendências fiscais\n- Emissão de certidões\n- Consulta de declarações\n\nRenove a procuração para evitar interrupção dos serviços.`,
    organ: 'Receita Federal',
    receivedAt: '2026-05-26T08:00:00Z',
    deadline: '2026-06-10T23:59:00Z',
    risk: 'medium',
    status: 'unread',
    taskCreated: false,
    obligationLinked: null,
    tags: ['procuração', 'e-CAC', 'vencimento'],
  },
];

export async function fetchMailboxMessages(filters?: {
  clientId?: string;
  risk?: string;
  status?: string;
  organ?: string;
}): Promise<MailboxMessage[]> {
  await new Promise(r => setTimeout(r, 400));
  let msgs = [...MOCK_MESSAGES];
  if (filters?.clientId) msgs = msgs.filter(m => m.clientId === filters.clientId);
  if (filters?.risk && filters.risk !== 'all') msgs = msgs.filter(m => m.risk === filters.risk);
  if (filters?.status && filters.status !== 'all') msgs = msgs.filter(m => m.status === filters.status);
  if (filters?.organ && filters.organ !== 'all') msgs = msgs.filter(m => m.organ === filters.organ);
  return msgs;
}

export async function fetchMailboxMessage(id: string): Promise<MailboxMessage | null> {
  await new Promise(r => setTimeout(r, 200));
  return MOCK_MESSAGES.find(m => m.id === id) ?? null;
}

export async function markMessageRead(id: string): Promise<void> {
  await new Promise(r => setTimeout(r, 100));
  const msg = MOCK_MESSAGES.find(m => m.id === id);
  if (msg) msg.status = 'read';
}

export async function markMessageResolved(id: string): Promise<void> {
  await new Promise(r => setTimeout(r, 200));
  const msg = MOCK_MESSAGES.find(m => m.id === id);
  if (msg) msg.status = 'resolved';
}
