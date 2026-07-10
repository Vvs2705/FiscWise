import { useQuery, useMutation } from '@tanstack/react-query';
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

// ─── Mercado Pago (Checkout Pro) ─────────────────────────────────────────────

export interface BillingConfig {
  gateway: string;
  public_key: string;
  go_live: boolean;
}

export function useBillingConfig() {
  return useQuery<BillingConfig>({
    queryKey: ['billing-config'],
    queryFn: async () => {
      const res = await api.get('/api/v1/billing/config');
      return res.data;
    },
    staleTime: 5 * 60 * 1000,
  });
}

export type CicloCobranca = 'mensal' | 'trimestral' | 'semestral' | 'anual';
export type MetodoPagamento = 'pix' | 'cartao';

export interface CheckoutRequest {
  plan_slug: string;
  ciclo: CicloCobranca;
  metodo: MetodoPagamento;
}

export interface CheckoutResponse {
  tipo: string;
  id: string | null;
  init_point: string | null;
}

export function useCheckout() {
  return useMutation<CheckoutResponse, Error, CheckoutRequest>({
    mutationFn: async (data) => {
      const res = await api.post<CheckoutResponse>('/api/v1/billing/checkout', data);
      return res.data;
    },
  });
}
