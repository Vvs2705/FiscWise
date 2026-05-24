import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';

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
}

export interface Plan {
  slug: string;
  name: string;
  description: string | null;
  price_monthly: number | null;
  max_clients: number | null;
  max_users: number | null;
  max_ai_calls_month: number | null;
  features: Record<string, boolean> | null;
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
