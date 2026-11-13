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
  billing_cycle?: string;
  /** Preenchido quando o dono cancelou: o acesso vale até current_period_end. */
  cancelled_at?: string | null;
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
  /** Oferta de reconquista: o servidor confere a oferta e calcula o preço. */
  oferta?: boolean;
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

/** Cancela a assinatura (sem multa). O período já pago continua valendo. */
export function useCancelSubscription() {
  const queryClient = useQueryClient();
  return useMutation<SubscriptionData, Error, void>({
    mutationFn: async () => {
      const res = await api.post<SubscriptionData>('/api/v1/billing/subscription/cancel');
      return res.data;
    },
    onSuccess: (data) => {
      queryClient.setQueryData(['subscription'], data);
      queryClient.invalidateQueries({ queryKey: ['subscription-usage'] });
      queryClient.invalidateQueries({ queryKey: ['tenant'] });
    },
  });
}

// ─── Oferta de reconquista (depois do teste grátis) ──────────────────────────

export interface OfertaPlano {
  plan_slug: string;
  plan_name: string;
  mensal_promo: number;
  mensal_cheio: number;
  mensal_desconto_pct: number;
  anual_promo: number;
  anual_cheio: number;
  anual_desconto_pct: number;
  anual_max_parcelas: number;
  anual_parcela: number;
}

export interface OfertaData {
  ativa: boolean;
  expires_at: string | null;
  planos: OfertaPlano[];
}

/** Oferta vigente do escritório (só o dono recebe; os demais veem ativa=false). */
export function useOferta(enabled = true) {
  return useQuery<OfertaData>({
    queryKey: ['billing-oferta'],
    queryFn: async () => {
      const res = await api.get<OfertaData>('/api/v1/billing/oferta');
      return res.data;
    },
    enabled,
    staleTime: 5 * 60 * 1000,
    retry: false,
  });
}

/** Data curta (DD/MM) do fim da oferta. */
export function dataOferta(iso: string | null): string {
  if (!iso) return '';
  return new Date(iso).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' });
}
