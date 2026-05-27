import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';

export interface PowerOfAttorneyResponse {
  id: string;
  tenant_id: string;
  client_id: string | null;
  cnpj_grantor: string;
  cnpj_attorney: string;
  services: string[];
  valid_from: string | null;
  valid_until: string | null;
  status: string;
  provider: string;
  last_verified_at: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface PowerOfAttorneyCreate {
  client_id?: string;
  cnpj_grantor: string;
  cnpj_attorney: string;
  services?: string[];
  valid_from?: string;
  valid_until?: string;
  provider?: string;
  notes?: string;
}

const KEY = ['powers-of-attorney'] as const;

export function usePowersOfAttorney() {
  return useQuery({
    queryKey: KEY,
    queryFn: async () => {
      const { data } = await api.get<PowerOfAttorneyResponse[]>('/api/v1/powers-of-attorney');
      return data;
    },
    retry: false,
  });
}

export function useCreatePowerOfAttorney() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: PowerOfAttorneyCreate) => {
      const { data } = await api.post<PowerOfAttorneyResponse>('/api/v1/powers-of-attorney', body);
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useRevokePowerOfAttorney() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, reason }: { id: string; reason: string }) => {
      const { data } = await api.post<PowerOfAttorneyResponse>(
        `/api/v1/powers-of-attorney/${id}/revoke`,
        { reason }
      );
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}
