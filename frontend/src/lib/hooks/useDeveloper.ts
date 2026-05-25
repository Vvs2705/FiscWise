import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';

// ──────────────────────────────────────────────────────────
// Types
// ──────────────────────────────────────────────────────────

export interface ApiKey {
  id: string;
  name: string;
  prefix: string;
  is_active: boolean;
  created_at: string;
  last_used_at: string | null;
}

export interface ApiKeyCreated extends ApiKey {
  /** Shown ONCE on creation. Store it securely — never returned again. */
  raw_key: string;
}

export interface WebhookSubscription {
  id: string;
  url: string;
  events: string[];
  is_active: boolean;
  created_at: string;
}

export interface WebhookSubscriptionCreated extends WebhookSubscription {
  /** Shown ONCE on creation for HMAC verification. Store securely. */
  signing_secret: string;
}

export interface WebhookDeliveryLog {
  id: string;
  subscription_id: string;
  event: string;
  url: string;
  status_code: number | null;
  success: boolean;
  duration_ms: number;
  created_at: string;
}

export interface CreateApiKeyInput {
  name: string;
}

export interface CreateWebhookInput {
  url: string;
  events: string[];
}

export interface UpdateWebhookInput {
  url?: string;
  events?: string[];
  is_active?: boolean;
}

// ──────────────────────────────────────────────────────────
// Query keys
// ──────────────────────────────────────────────────────────

const devKeys = {
  apiKeys: ['developer', 'api_keys'] as const,
  webhooks: ['developer', 'webhooks'] as const,
  logs: (subId?: string) => ['developer', 'webhook_logs', subId ?? 'all'] as const,
  availableEvents: ['developer', 'webhook_events'] as const,
};

// ──────────────────────────────────────────────────────────
// API Key Hooks
// ──────────────────────────────────────────────────────────

export function useApiKeys() {
  return useQuery({
    queryKey: devKeys.apiKeys,
    queryFn: async () => {
      const { data } = await api.get<ApiKey[]>('/api/v1/developer/api-keys');
      return data;
    },
    staleTime: 60_000,
  });
}

export function useCreateApiKey() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: CreateApiKeyInput) => {
      const { data } = await api.post<ApiKeyCreated>('/api/v1/developer/api-keys', payload);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: devKeys.apiKeys });
    },
  });
}

export function useRevokeApiKey() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (keyId: string) => {
      await api.delete(`/api/v1/developer/api-keys/${keyId}`);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: devKeys.apiKeys });
    },
  });
}

// ──────────────────────────────────────────────────────────
// Webhook Subscription Hooks
// ──────────────────────────────────────────────────────────

export function useWebhooks() {
  return useQuery({
    queryKey: devKeys.webhooks,
    queryFn: async () => {
      const { data } = await api.get<WebhookSubscription[]>('/api/v1/developer/webhooks');
      return data;
    },
    staleTime: 60_000,
  });
}

export function useCreateWebhook() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: CreateWebhookInput) => {
      const { data } = await api.post<WebhookSubscriptionCreated>('/api/v1/developer/webhooks', payload);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: devKeys.webhooks });
    },
  });
}

export function useUpdateWebhook() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, payload }: { id: string; payload: UpdateWebhookInput }) => {
      const { data } = await api.put<WebhookSubscription>(`/api/v1/developer/webhooks/${id}`, payload);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: devKeys.webhooks });
    },
  });
}

export function useDeleteWebhook() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (subId: string) => {
      await api.delete(`/api/v1/developer/webhooks/${subId}`);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: devKeys.webhooks });
    },
  });
}

// ──────────────────────────────────────────────────────────
// Delivery Logs & Available Events
// ──────────────────────────────────────────────────────────

export function useWebhookDeliveryLogs(subscriptionId?: string) {
  return useQuery({
    queryKey: devKeys.logs(subscriptionId),
    queryFn: async () => {
      const url = subscriptionId
        ? `/api/v1/developer/webhooks/logs?subscription_id=${subscriptionId}`
        : '/api/v1/developer/webhooks/logs';
      const { data } = await api.get<WebhookDeliveryLog[]>(url);
      return data;
    },
    staleTime: 30_000,
  });
}

export function useAvailableWebhookEvents() {
  return useQuery({
    queryKey: devKeys.availableEvents,
    queryFn: async () => {
      const { data } = await api.get<string[]>('/api/v1/developer/webhooks/events');
      return data;
    },
    staleTime: Infinity,
  });
}
