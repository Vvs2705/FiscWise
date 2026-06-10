import { api } from '@/lib/api';
import { ChecklistItem, ClosingStatus, MonthlyClosing } from './types';

/** Raw shapes returned by the backend (snake_case). */
interface ApiChecklistItem {
  id: string;
  label: string;
  status: 'pending' | 'done' | 'blocked' | 'na';
  notes?: string | null;
  completed_at?: string | null;
}

interface ApiMonthlyClosing {
  id: string;
  tenant_id: string;
  client_id: string;
  client_name: string | null;
  client_cnpj: string | null;
  competence: string;
  status: ClosingStatus;
  score: number;
  blockers: string[] | null;
  checklist: ApiChecklistItem[] | null;
  invoices_count: number;
  invoices_pending: number;
  guides_count: number;
  guides_paid: number;
  obligations_total: number;
  obligations_done: number;
  ecac_pendencies: number;
  documents_total: number;
  documents_received: number;
  dossier_generated_at: string | null;
  created_at: string;
  updated_at: string;
}

function mapChecklistItem(item: ApiChecklistItem): ChecklistItem {
  return {
    id: item.id,
    label: item.label,
    status: item.status,
    notes: item.notes ?? undefined,
    completedAt: item.completed_at ?? undefined,
  };
}

function mapClosing(c: ApiMonthlyClosing): MonthlyClosing {
  return {
    id: c.id,
    clientId: c.client_id,
    clientName: c.client_name ?? '',
    clientCnpj: c.client_cnpj ?? '',
    competence: c.competence,
    status: c.status,
    score: c.score,
    blockers: c.blockers ?? [],
    checklist: (c.checklist ?? []).map(mapChecklistItem),
    invoicesCount: c.invoices_count,
    invoicesPending: c.invoices_pending,
    guidesCount: c.guides_count,
    guidesPaid: c.guides_paid,
    obligationsTotal: c.obligations_total,
    obligationsDone: c.obligations_done,
    ecacPendencies: c.ecac_pendencies,
    documentsTotal: c.documents_total,
    documentsReceived: c.documents_received,
    createdAt: c.created_at,
    updatedAt: c.updated_at,
    dossierGeneratedAt: c.dossier_generated_at ?? undefined,
  };
}

export async function fetchMonthlyClosings(competence?: string): Promise<MonthlyClosing[]> {
  const params: Record<string, string> = {};
  if (competence) params.competence = competence;
  const { data } = await api.get<ApiMonthlyClosing[]>('/api/v1/monthly-closing', { params });
  return data.map(mapClosing);
}

export async function fetchMonthlyClosing(id: string): Promise<MonthlyClosing | null> {
  const { data } = await api.get<ApiMonthlyClosing>(`/api/v1/monthly-closing/${id}`);
  return mapClosing(data);
}

export async function updateChecklistItem(
  closingId: string,
  itemId: string,
  status: 'pending' | 'done' | 'blocked' | 'na',
  notes?: string,
): Promise<void> {
  await api.patch(`/api/v1/monthly-closing/${closingId}/checklist/${itemId}`, {
    status,
    ...(notes !== undefined ? { notes } : {}),
  });
}

export async function generateDossier(closingId: string): Promise<{ url: string }> {
  const { data } = await api.post<{ url: string | null; generated_at: string }>(
    `/api/v1/monthly-closing/${closingId}/dossier`,
  );
  return { url: data.url ?? '' };
}

/** Create the closing pipeline for every active client in a competence. */
export async function generateMonthlyClosings(
  competence: string,
): Promise<{ competence: string; created: number; skipped: number }> {
  const { data } = await api.post<{ competence: string; created: number; skipped: number }>(
    '/api/v1/monthly-closing/generate',
    null,
    { params: { competence } },
  );
  return data;
}
