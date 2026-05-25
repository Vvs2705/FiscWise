import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';

export interface WhatsAppInbox {
  id: string;
  tenant_id: string;
  client_id: string | null;
  phone_number: string;
  customer_name: string | null;
  last_message_at: string | null;
  last_message_preview: string | null;
  unread_count: number;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface WhatsAppMessage {
  id: string;
  tenant_id: string;
  inbox_id: string;
  direction: 'inbound' | 'outbound';
  sender_name: string | null;
  sender_phone: string | null;
  message_type: 'text' | 'document' | 'image' | 'audio';
  body: string | null;
  media_url: string | null;
  external_message_id: string | null;
  status: string;
  created_at: string;
}

const waKey = ['whatsapp'] as const;

export function useWhatsAppInboxes(clientId?: string, statusFilter = 'active') {
  return useQuery({
    queryKey: [...waKey, 'inboxes', { clientId, statusFilter }],
    queryFn: async () => {
      let url = `/api/v1/whatsapp/inboxes?status=${statusFilter}`;
      if (clientId) {
        url += `&client_id=${clientId}`;
      }
      const { data } = await api.get<WhatsAppInbox[]>(url);
      return data;
    },
    staleTime: 10_000, // 10 seconds stale time for inbox list
    refetchInterval: 15_000, // auto refetch list every 15s to show live new threads
  });
}

export function useWhatsAppMessages(inboxId?: string, limit = 50) {
  return useQuery({
    queryKey: [...waKey, 'messages', inboxId, limit],
    queryFn: async () => {
      if (!inboxId) return [];
      const { data } = await api.get<WhatsAppMessage[]>(
        `/api/v1/whatsapp/inboxes/${inboxId}/messages?limit=${limit}`
      );
      return data;
    },
    enabled: !!inboxId,
    staleTime: 5_000,
    refetchInterval: 5_000, // check for new messages every 5 seconds when in a chat
  });
}

export function useSendWhatsAppMessage(inboxId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { body: string; media_url?: string; message_type?: string }) => {
      const { data } = await api.post<WhatsAppMessage>(
        `/api/v1/whatsapp/inboxes/${inboxId}/send`,
        payload
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [...waKey, 'messages', inboxId] });
      qc.invalidateQueries({ queryKey: [...waKey, 'inboxes'] });
    },
  });
}

export function useLinkInboxClient(inboxId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (clientId: string | null) => {
      const { data } = await api.post<WhatsAppInbox>(
        `/api/v1/whatsapp/inboxes/${inboxId}/link`,
        { client_id: clientId }
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: waKey });
    },
  });
}

export function useConvertMessageToTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (params: { messageId: string; title: string; due_date: string; priority?: string }) => {
      const { messageId, ...payload } = params;
      const { data } = await api.post<{ status: string; message: string; task_id: string }>(
        `/api/v1/whatsapp/messages/${messageId}/convert-task`,
        payload
      );
      return data;
    },
    onSuccess: () => {
      // Invalidate deadlines/tasks queries to refresh agenda
      qc.invalidateQueries({ queryKey: ['deadlines'] });
    },
  });
}
