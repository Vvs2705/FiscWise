import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';

export interface NotificationMessage {
  id: string;
  tenant_id: string;
  client_id: string | null;
  channel: string;
  recipient: string;
  subject: string | null;
  status: 'pending' | 'sent' | 'delivered' | 'failed' | 'skipped';
  provider: string | null;
  sent_at: string | null;
  created_at: string;
}

export interface NotificationStats {
  period: string;
  sent: number;
  skipped: number;
  failed: number;
  pending: number;
  total: number;
}

export interface TriggerResult {
  sent: number;
  skipped: number;
  failed: number;
  clients_notified: number;
  competence_month: string;
}

const notifKey = ['notifications'] as const;

export function useNotificationMessages(limit = 50) {
  return useQuery({
    queryKey: [...notifKey, 'messages', limit],
    queryFn: async () => {
      const { data } = await api.get<NotificationMessage[]>(
        `/api/v1/notifications?limit=${limit}`
      );
      return data;
    },
    staleTime: 60_000,
    retry: false,
  });
}

export function useNotificationStats() {
  return useQuery({
    queryKey: [...notifKey, 'stats'],
    queryFn: async () => {
      const { data } = await api.get<NotificationStats>('/api/v1/notifications/stats');
      return data;
    },
    staleTime: 2 * 60_000,
    retry: false,
  });
}

export function useTriggerPendingDocNotifications() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (competenceMonth?: string) => {
      const { data } = await api.post<TriggerResult>(
        '/api/v1/notifications/trigger-pending-docs',
        { competence_month: competenceMonth ?? null }
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: notifKey });
    },
  });
}

// ─── E-mail ao cliente (aviso de certificado, lembretes) ─────────────────────

/** Resposta do backend para qualquer e-mail enviado a um cliente: sempre a verdade. */
export interface ClientEmailResult {
  queued: boolean;
  sent: boolean;
  status: 'sent' | 'skipped' | 'failed' | string;
  reason: 'email_disabled' | 'no_recipient' | 'provider_error' | string | null;
  recipient: string | null;
  notification_id: string;
  message: string;
}

export type ClientEmailToast = { kind: 'success' | 'warning' | 'error'; message: string };

/** Traduz o resultado em um toast honesto: sucesso só quando o provedor aceitou. */
export function describeClientEmailResult(result: ClientEmailResult): ClientEmailToast {
  if (result.sent) {
    return { kind: 'success', message: result.message || 'E-mail enviado ao cliente.' };
  }
  if (result.reason === 'email_disabled') {
    return {
      kind: 'warning',
      message: 'E-mail desligado nesta instalação: configure RESEND_ENABLED e RESEND_API_KEY.',
    };
  }
  if (result.reason === 'no_recipient') {
    return { kind: 'warning', message: 'O cliente não tem e-mail cadastrado. Nada foi enviado.' };
  }
  return { kind: 'error', message: result.message || 'O e-mail não foi enviado.' };
}

export interface CertExpiryWarningInput {
  client_id: string;
  client_name: string;
  cert_label: string;
  days_until_expiry: number;
}

export function useCertExpiryWarning() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: CertExpiryWarningInput) => {
      const { data } = await api.post<ClientEmailResult>(
        '/api/v1/notifications/cert-expiry-warning',
        input
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: notifKey });
    },
  });
}

export type ClientReminderKind = 'pending_documents' | 'payment' | 'custom';

export interface ClientReminderInput {
  clientId: string;
  kind: ClientReminderKind;
  message?: string;
}

/** POST /api/v1/clients/{id}/reminders — e-mail real ao cliente, com o resultado verdadeiro. */
export function useSendClientReminder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ clientId, kind, message }: ClientReminderInput) => {
      const { data } = await api.post<ClientEmailResult>(
        `/api/v1/clients/${clientId}/reminders`,
        { kind, message: message ?? null }
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: notifKey });
    },
  });
}
