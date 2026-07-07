import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';

export interface SubscriptionData {
  id: string;
  tenant_id: string;
  plan_id: string;
  billing_provider: string | null;
  status: string;
  current_period_end: string | null;
  trial_ends_at: string | null;
  amount: string | null;
  currency: string;
  created_at: string;
  /** Asaas hosted checkout URL (invoiceUrl) — redirect the user here to pay */
  checkout_url?: string | null;
}

export interface CreateSubscriptionRequest {
  plan_id: string;
  billing_provider?: string;
  cpf_cnpj?: string;
  name?: string;
  email?: string;
}

export function useSubscription() {
  return useQuery<SubscriptionData>({
    queryKey: ['subscription'],
    queryFn: async () => {
      const res = await api.get('/api/v1/billing/subscription');
      return res.data;
    },
    retry: false, // Don't infinite retry if 404 (i.e. free plan / not set up in billing)
  });
}

export function useCreateSubscription() {
  const queryClient = useQueryClient();
  return useMutation<SubscriptionData, Error, CreateSubscriptionRequest>({
    mutationFn: async (data) => {
      const res = await api.post<SubscriptionData>('/api/v1/billing/subscription', data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['subscription'] });
      queryClient.invalidateQueries({ queryKey: ['subscription-usage'] });
    },
  });
}
