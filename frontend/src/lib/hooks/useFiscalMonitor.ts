import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';

export interface FiscalRegistryDetails {
  source?: 'brasilapi' | 'mock';
  consulted_at?: string;
  razao_social?: string | null;
  nome_fantasia?: string | null;
  descricao_situacao_cadastral?: string | null;
  data_situacao_cadastral?: string | null;
  motivo_situacao_cadastral?: number | string | null;
  cnae_fiscal?: number | null;
  cnae_fiscal_descricao?: string | null;
  natureza_juridica?: string | null;
  opcao_pelo_simples?: boolean | null;
  opcao_pelo_mei?: boolean | null;
  data_inicio_atividade?: string | null;
  status?: 'error';
  last_error?: string;
  last_error_at?: string;
}

/**
 * Situação cadastral real (BrasilAPI). Débitos, CND e NF-e não são consultados
 * (exigem SERPRO): o backend devolve debts/cnd nulos, nfes vazio e
 * source="unavailable" com a mensagem do que falta.
 */
export interface FiscalMonitorSummary {
  id: string;
  tenant_id: string;
  client_id: string;
  last_sync_at: string | null;
  /** Situação cadastral (ATIVA, BAIXADA, SUSPENSA, INAPTA, NULA) ou PENDENTE / ERRO_CONSULTA. */
  cnpj_status: string;
  situation_details: FiscalRegistryDetails | null;
  registry_source: 'brasilapi' | 'mock' | null;
  debts: null;
  cnd: null;
  nfes: never[];
  source: 'unavailable';
  message: string;
}

export interface SyncResponse {
  status: string;
  message: string;
  summary: FiscalMonitorSummary;
}

const fmKey = ['fiscal-monitor'] as const;

export function useFiscalMonitorStatus(clientId?: string) {
  return useQuery({
    queryKey: [...fmKey, 'status', clientId],
    queryFn: async () => {
      if (!clientId) return null;
      const { data } = await api.get<FiscalMonitorSummary>(
        `/api/v1/fiscal-monitor/status/${clientId}`
      );
      return data;
    },
    enabled: !!clientId,
    staleTime: 30_000, // 30 seconds
  });
}

export function useSyncFiscalMonitor(clientId?: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      if (!clientId) throw new Error('clientId é obrigatório para sincronização');
      const { data } = await api.post<SyncResponse>(
        `/api/v1/fiscal-monitor/sync/${clientId}`
      );
      return data;
    },
    onSuccess: () => {
      // Invalidate target queries to trigger updates across tabs and dashboard elements
      qc.invalidateQueries({ queryKey: [...fmKey, 'status', clientId] });
      // O sync cancela prazos e CNDs falsos deixados pelo simulador antigo.
      qc.invalidateQueries({ queryKey: ['deadlines'] });
      qc.invalidateQueries({ queryKey: ['client-documents', clientId] });
      qc.invalidateQueries({ queryKey: ['clients'] });
    },
  });
}
