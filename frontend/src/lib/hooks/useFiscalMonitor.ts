import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';

export interface FiscalDebt {
  id: string;
  type: 'FEDERAL' | 'STATE' | 'MUNICIPAL';
  description: string;
  value: number;
  due_date: string;
}

export interface FiscalMonitorSummary {
  id: string;
  tenant_id: string;
  client_id: string;
  last_sync_at: string | null;
  cnpj_status: 'REGULAR' | 'SUSPENSO' | 'INAPTA' | 'BAIXADA' | 'PENDENTE';
  situation_details: {
    situacao_cadastral?: string;
    motivo_situacao_cadastral?: string;
    data_situacao_cadastral?: string;
    nome_empresarial?: string;
    natureza_juridica?: string;
    atividade_principal?: Array<{ code: string; text: string }>;
  } | null;
  has_debts: boolean;
  debt_count: number;
  total_debt_value: number;
  debts_list: {
    debts: FiscalDebt[];
  } | null;
  cnd_status: 'REGULAR' | 'COM_PENDENCIAS' | 'EXPIRADA' | 'PENDENTE';
  last_cnd_download_at: string | null;
  last_cnd_document_id: string | null;
}

export interface FiscalNFe {
  id: string;
  tenant_id: string;
  client_id: string;
  access_key: string;
  nfe_number: string;
  nfe_type: 'ENTRADA' | 'SAIDA';
  issuer_name: string;
  issuer_document: string;
  recipient_name: string;
  recipient_document: string;
  value: number;
  issued_at: string;
  retrieved_at: string;
  xml_url: string | null;
  status: string;
}

export interface SyncResponse {
  status: string;
  message: string;
  summary: FiscalMonitorSummary;
  nfes_fetched: number;
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

export function useFiscalNFes(clientId?: string, nfeType?: string, limit = 50) {
  return useQuery({
    queryKey: [...fmKey, 'nfes', clientId, { nfeType, limit }],
    queryFn: async () => {
      if (!clientId) return [];
      let url = `/api/v1/fiscal-monitor/nfes/${clientId}?limit=${limit}`;
      if (nfeType) {
        url += `&nfe_type=${nfeType}`;
      }
      const { data } = await api.get<FiscalNFe[]>(url);
      return data;
    },
    enabled: !!clientId,
    staleTime: 30_000,
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
      qc.invalidateQueries({ queryKey: [...fmKey, 'nfes', clientId] });
      qc.invalidateQueries({ queryKey: ['deadlines'] });
      qc.invalidateQueries({ queryKey: ['client-documents', clientId] });
      qc.invalidateQueries({ queryKey: ['clients'] });
    },
  });
}
