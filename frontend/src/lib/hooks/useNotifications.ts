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
