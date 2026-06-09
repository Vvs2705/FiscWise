import { api } from '@/lib/api';
import { MailboxMessage, MailboxMessageRisk, MailboxMessageStatus } from './types';

/** Raw message shape returned by the backend (snake_case). */
interface ApiMailboxMessage {
  id: string;
  tenant_id: string;
  client_id: string | null;
  external_id: string | null;
  client_name: string | null;
  client_cnpj: string | null;
  subject: string;
  summary: string | null;
  body: string | null;
  organ: string | null;
  received_at: string | null;
  deadline: string | null;
  risk: MailboxMessageRisk;
  status: MailboxMessageStatus;
  task_created: boolean;
  obligation_linked: string | null;
  tags: string[] | null;
  created_at: string;
}

function mapMessage(m: ApiMailboxMessage): MailboxMessage {
  return {
    id: m.id,
    clientId: m.client_id ?? '',
    clientName: m.client_name ?? '',
    clientCnpj: m.client_cnpj ?? '',
    subject: m.subject,
    summary: m.summary ?? '',
    body: m.body ?? '',
    organ: m.organ ?? '',
    receivedAt: m.received_at ?? m.created_at,
    deadline: m.deadline,
    risk: m.risk,
    status: m.status,
    taskCreated: m.task_created,
    obligationLinked: m.obligation_linked,
    tags: m.tags ?? [],
  };
}

export async function fetchMailboxMessages(filters?: {
  clientId?: string;
  risk?: string;
  status?: string;
  organ?: string;
}): Promise<MailboxMessage[]> {
  const params: Record<string, string> = {};
  if (filters?.clientId) params.client_id = filters.clientId;
  if (filters?.risk && filters.risk !== 'all') params.risk = filters.risk;
  if (filters?.status && filters.status !== 'all') params.status = filters.status;
  if (filters?.organ && filters.organ !== 'all') params.organ = filters.organ;

  const { data } = await api.get<ApiMailboxMessage[]>('/api/v1/fiscal-mailbox/messages', { params });
  return data.map(mapMessage);
}

export async function fetchMailboxMessage(id: string): Promise<MailboxMessage | null> {
  const { data } = await api.get<ApiMailboxMessage>(`/api/v1/fiscal-mailbox/messages/${id}`);
  return mapMessage(data);
}

export async function markMessageRead(id: string): Promise<void> {
  await api.post(`/api/v1/fiscal-mailbox/messages/${id}/read`);
}

export async function markMessageResolved(id: string): Promise<void> {
  await api.post(`/api/v1/fiscal-mailbox/messages/${id}/resolve`);
}

/** Trigger ingestion of new messages from the e-CAC/DTE provider. */
export async function syncMailboxMessages(): Promise<{ synced: number; created: number; skipped: number }> {
  const { data } = await api.post<{ synced: number; created: number; skipped: number }>(
    '/api/v1/fiscal-mailbox/sync',
  );
  return data;
}
