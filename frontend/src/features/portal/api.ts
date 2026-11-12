import { useMutation } from '@tanstack/react-query';
import { api } from '@/lib/api';

/** Aggregated portal preview returned by GET /api/v1/portal/preview/{clientId}. */

export interface PortalPreviewClosing {
  id: string;
  competence: string; // YYYY-MM
  status: string;
  score: number;
}

export interface PortalPreviewDocument {
  id: string;
  name: string;
  status: string;
  requestedAt: string | null;
}

export interface PortalPreviewGuide {
  id: string;
  type: string;
  competence: string | null;
  value: number;
  due: string | null;
  status: string;
}

export interface PortalPreviewPendency {
  id: string;
  title: string;
  deadline: string | null;
  status: string;
}

export interface PortalPreview {
  client: { id: string; name: string; document: string | null };
  closing: PortalPreviewClosing | null;
  documents: PortalPreviewDocument[];
  guides: PortalPreviewGuide[];
  pendencies: PortalPreviewPendency[];
}

export interface ApiPortalPreview {
  client: { id: string; name: string; document: string | null };
  closing: PortalPreviewClosing | null;
  documents: { id: string; name: string; status: string; requested_at: string | null }[];
  guides: PortalPreviewGuide[];
  pendencies: PortalPreviewPendency[];
}

export function mapPortalPreview(data: ApiPortalPreview): PortalPreview {
  return {
    client: data.client,
    closing: data.closing,
    documents: data.documents.map(d => ({
      id: d.id,
      name: d.name,
      status: d.status,
      requestedAt: d.requested_at,
    })),
    guides: data.guides,
    pendencies: data.pendencies,
  };
}

export async function fetchPortalPreview(clientId: string): Promise<PortalPreview> {
  const { data } = await api.get<ApiPortalPreview>(`/api/v1/portal/preview/${clientId}`);
  return mapPortalPreview(data);
}

/** Portal do cliente final: o backend resolve o cliente pelo usuário logado. */
export async function fetchMyPortal(): Promise<PortalPreview> {
  const { data } = await api.get<ApiPortalPreview>('/api/v1/portal/my-overview');
  return mapPortalPreview(data);
}

// ---------------------------------------------------------------------------
// Link de acesso ao portal (magic link)
// ---------------------------------------------------------------------------

/** Resposta de POST /api/v1/portal/magic-link/request. */
export interface PortalAccessResult {
  sent: boolean;
  delivery: 'email' | 'manual';
  email: string;
  expires_at: string;
  reason?: string;
  /** Só vem quando o envio de e-mail não está configurado (delivery = manual). */
  portal_link?: string;
}

export type PortalAccessOutcome =
  | { kind: 'sent'; message: string }
  | { kind: 'manual'; message: string; link: string }
  | { kind: 'failed'; message: string };

/** Traduz a resposta do backend para o que a tela mostra (toast honesto). */
export function describePortalAccessResult(result: PortalAccessResult): PortalAccessOutcome {
  if (result.sent) {
    return { kind: 'sent', message: `Link de acesso enviado para ${result.email}.` };
  }
  if (result.delivery === 'manual' && result.portal_link) {
    return {
      kind: 'manual',
      message: 'O envio de e-mail não está configurado. Copie o link e envie ao cliente.',
      link: result.portal_link,
    };
  }
  return { kind: 'failed', message: result.reason || 'Não foi possível enviar o link de acesso.' };
}

export async function requestPortalAccess(payload: {
  clientId: string;
  email?: string;
}): Promise<PortalAccessResult> {
  const { data } = await api.post<PortalAccessResult>('/api/v1/portal/magic-link/request', {
    client_id: payload.clientId,
    ...(payload.email ? { email: payload.email } : {}),
  });
  return data;
}

/** Escritório: cria/garante o acesso do cliente ao portal e envia o link. */
export function useRequestPortalAccess() {
  return useMutation({ mutationFn: requestPortalAccess });
}

/** Cliente final: pede o próprio link na tela de login (resposta sempre genérica). */
export async function selfRequestPortalLink(email: string): Promise<{ message: string }> {
  const { data } = await api.post<{ message: string }>(
    '/api/v1/portal/magic-link/self-request',
    { email },
  );
  return data;
}

export function useSelfRequestPortalLink() {
  return useMutation({ mutationFn: selfRequestPortalLink });
}
