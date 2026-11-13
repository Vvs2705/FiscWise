import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { fetchTenant, type TenantData } from '@/lib/auth';

export interface UsageItem {
  used: number;
  limit: number | null;
  percent: number | null;
}

export interface SubscriptionUsage {
  plan_slug: string;
  plan_name: string;
  clients: UsageItem;
  users: UsageItem;
  ai_calls_this_month: UsageItem;
  features: Record<string, boolean>;
  /** Limite de documentos por cliente (null = sem limite). */
  documents_per_client_limit?: number | null;
}

// Linha da matriz de preços calculada no servidor (backend/app/core/pricing.py)
export interface LinhaPreco {
  ciclo: 'mensal' | 'trimestral' | 'semestral' | 'anual';
  label: string;
  meses: number;
  preco_cheio: number;
  pix_total: number;
  desconto_pix_pct: number;
  cartao_total: number;
  desconto_cartao_pct: number;
  cartao_max_parcelas: number;
  cartao_parcela: number;
  obs: string;
}

export interface Plan {
  id: string;
  slug: string;
  name: string;
  description: string | null;
  price_monthly: number | null;
  max_clients: number | null;
  max_users: number | null;
  max_ai_calls_month: number | null;
  max_documents_per_client?: number | null;
  features: Record<string, boolean> | null;
  tabela_precos?: LinhaPreco[] | null;
}

export function useSubscriptionUsage() {
  return useQuery<SubscriptionUsage>({
    queryKey: ['subscription-usage'],
    queryFn: async () => {
      const res = await api.get('/api/v1/subscription/usage');
      return res.data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

export function useAvailablePlans() {
  return useQuery<Plan[]>({
    queryKey: ['plans'],
    queryFn: async () => {
      const res = await api.get('/api/v1/subscription/plans');
      return res.data;
    },
    staleTime: 30 * 60 * 1000, // 30 minutes — plans rarely change
  });
}

/**
 * Escritório atual (GET /api/v1/auth/tenant): plano efetivo e situação do
 * teste grátis (`em_teste`, `trial_dias_restantes`, `acesso_expirado`).
 * Mesma chave ['tenant'] usada nas outras telas, para uma busca só.
 */
export function useTenantInfo(enabled = true) {
  return useQuery<TenantData>({
    queryKey: ['tenant'],
    queryFn: fetchTenant,
    staleTime: 5 * 60 * 1000,
    enabled,
  });
}
