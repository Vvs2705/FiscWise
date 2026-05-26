import { MonthlyClosing } from './types';

const BASE_CHECKLIST = [
  { id: 'ck-01', label: 'Documentos do cliente recebidos', status: 'done' as const },
  { id: 'ck-02', label: 'Notas fiscais emitidas', status: 'done' as const },
  { id: 'ck-03', label: 'Guias geradas e enviadas', status: 'pending' as const },
  { id: 'ck-04', label: 'Comprovantes de pagamento anexados', status: 'pending' as const },
  { id: 'ck-05', label: 'Obrigações acessórias cumpridas', status: 'pending' as const },
  { id: 'ck-06', label: 'Consulta e-CAC realizada', status: 'done' as const },
  { id: 'ck-07', label: 'Pendências fiscais verificadas', status: 'blocked' as const, notes: 'Aguardando resposta do cliente' },
  { id: 'ck-08', label: 'Dossiê gerado e enviado', status: 'pending' as const },
];

const MOCK_CLOSINGS: MonthlyClosing[] = [
  {
    id: 'clos-001',
    clientId: 'cli-001',
    clientName: 'Tech Solutions Ltda',
    clientCnpj: '12.345.678/0001-90',
    competence: '2026-05',
    status: 'blocked',
    score: 42,
    blockers: ['Documentos do cliente não recebidos', 'Pendência e-CAC não resolvida'],
    checklist: BASE_CHECKLIST.map(c => ({
      ...c,
      status: c.id === 'ck-07' ? 'blocked' as const : c.status,
    })),
    invoicesCount: 3,
    invoicesPending: 1,
    guidesCount: 2,
    guidesPaid: 0,
    obligationsTotal: 4,
    obligationsDone: 2,
    ecacPendencies: 1,
    documentsTotal: 8,
    documentsReceived: 5,
    createdAt: '2026-05-01T08:00:00Z',
    updatedAt: '2026-05-26T08:00:00Z',
  },
  {
    id: 'clos-002',
    clientId: 'cli-002',
    clientName: 'Comércio São Paulo ME',
    clientCnpj: '98.765.432/0001-11',
    competence: '2026-05',
    status: 'in_progress',
    score: 68,
    blockers: [],
    checklist: BASE_CHECKLIST.map(c => ({
      ...c,
      status: ['ck-01', 'ck-02', 'ck-06'].includes(c.id) ? 'done' as const : 'pending' as const,
    })),
    invoicesCount: 5,
    invoicesPending: 0,
    guidesCount: 3,
    guidesPaid: 2,
    obligationsTotal: 3,
    obligationsDone: 2,
    ecacPendencies: 0,
    documentsTotal: 6,
    documentsReceived: 6,
    createdAt: '2026-05-01T09:00:00Z',
    updatedAt: '2026-05-25T14:00:00Z',
  },
  {
    id: 'clos-003',
    clientId: 'cli-003',
    clientName: 'Construtora Horizonte SA',
    clientCnpj: '11.222.333/0001-44',
    competence: '2026-05',
    status: 'ready_for_review',
    score: 88,
    blockers: [],
    checklist: BASE_CHECKLIST.map(c => ({
      ...c,
      status: c.id !== 'ck-08' ? 'done' as const : 'pending' as const,
    })),
    invoicesCount: 8,
    invoicesPending: 0,
    guidesCount: 4,
    guidesPaid: 4,
    obligationsTotal: 5,
    obligationsDone: 5,
    ecacPendencies: 0,
    documentsTotal: 10,
    documentsReceived: 10,
    createdAt: '2026-05-01T07:00:00Z',
    updatedAt: '2026-05-24T16:00:00Z',
  },
  {
    id: 'clos-004',
    clientId: 'cli-004',
    clientName: 'Clínica Saúde Total Ltda',
    clientCnpj: '55.666.777/0001-22',
    competence: '2026-04',
    status: 'completed',
    score: 100,
    blockers: [],
    checklist: BASE_CHECKLIST.map(c => ({ ...c, status: 'done' as const, completedAt: '2026-04-30T18:00:00Z' })),
    invoicesCount: 12,
    invoicesPending: 0,
    guidesCount: 3,
    guidesPaid: 3,
    obligationsTotal: 4,
    obligationsDone: 4,
    ecacPendencies: 0,
    documentsTotal: 15,
    documentsReceived: 15,
    createdAt: '2026-04-01T08:00:00Z',
    updatedAt: '2026-04-30T18:00:00Z',
    dossierGeneratedAt: '2026-04-30T18:30:00Z',
  },
  {
    id: 'clos-005',
    clientId: 'cli-005',
    clientName: 'Agência Digital Express ME',
    clientCnpj: '33.444.555/0001-66',
    competence: '2026-05',
    status: 'not_started',
    score: 0,
    blockers: ['Fechamento não iniciado'],
    checklist: BASE_CHECKLIST.map(c => ({ ...c, status: 'pending' as const })),
    invoicesCount: 0,
    invoicesPending: 0,
    guidesCount: 0,
    guidesPaid: 0,
    obligationsTotal: 2,
    obligationsDone: 0,
    ecacPendencies: 0,
    documentsTotal: 4,
    documentsReceived: 0,
    createdAt: '2026-05-01T08:00:00Z',
    updatedAt: '2026-05-01T08:00:00Z',
  },
];

export async function fetchMonthlyClosings(competence?: string): Promise<MonthlyClosing[]> {
  await new Promise(r => setTimeout(r, 500));
  if (competence) return MOCK_CLOSINGS.filter(c => c.competence === competence);
  return MOCK_CLOSINGS;
}

export async function fetchMonthlyClosing(id: string): Promise<MonthlyClosing | null> {
  await new Promise(r => setTimeout(r, 300));
  return MOCK_CLOSINGS.find(c => c.id === id) ?? null;
}

export async function updateChecklistItem(
  closingId: string,
  itemId: string,
  status: 'pending' | 'done' | 'blocked' | 'na',
  notes?: string,
): Promise<void> {
  await new Promise(r => setTimeout(r, 200));
  const closing = MOCK_CLOSINGS.find(c => c.id === closingId);
  if (closing) {
    const item = closing.checklist.find(i => i.id === itemId);
    if (item) {
      item.status = status;
      if (notes !== undefined) item.notes = notes;
      if (status === 'done') item.completedAt = new Date().toISOString();
    }
    // Recalculate score
    const done = closing.checklist.filter(i => i.status === 'done').length;
    closing.score = Math.round((done / closing.checklist.length) * 100);
  }
}

export async function generateDossier(closingId: string): Promise<{ url: string }> {
  await new Promise(r => setTimeout(r, 1500));
  return { url: `/mock-dossier-${closingId}.pdf` };
}
