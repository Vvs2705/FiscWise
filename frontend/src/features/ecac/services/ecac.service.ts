import { api } from '@/lib/api';

export interface EcacProxyCreate {
  client_id?: string;
  outorgante_cpf_cnpj: string;
  outorgante_nome?: string;
  procurador_cpf: string;
  tipo?: string;
  servicos_autorizados?: string[];
  data_inicio?: string;
  data_validade?: string;
  status?: string;
}

export interface EcacProxyResponse extends EcacProxyCreate {
  id: string;
  tenant_id: string;
  ultima_verificacao?: string;
  created_at: string;
}

export interface ClientWithoutProxy {
  id: string;
  name: string;
  document?: string;
}

export interface EcacFiscalSituationResponse {
  id: string;
  tenant_id: string;
  client_id?: string;
  cpf_cnpj: string;
  status_geral?: string;
  pendencias?: unknown;
  debitos?: unknown;
  certidao_status?: string;
  certidao_validade?: string;
  raw_response?: unknown;
  consultado_em: string;
}

export const ecacService = {
  listProxies: async (): Promise<EcacProxyResponse[]> => {
    const res = await api.get<EcacProxyResponse[]>('/api/v1/ecac/proxies');
    return res.data;
  },

  createProxy: async (data: EcacProxyCreate): Promise<EcacProxyResponse> => {
    const res = await api.post<EcacProxyResponse>('/api/v1/ecac/proxies', data);
    return res.data;
  },

  getProxy: async (id: string): Promise<EcacProxyResponse> => {
    const res = await api.get<EcacProxyResponse>(`/api/v1/ecac/proxies/${id}`);
    return res.data;
  },

  updateProxy: async (id: string, data: Partial<EcacProxyCreate>): Promise<EcacProxyResponse> => {
    const res = await api.put<EcacProxyResponse>(`/api/v1/ecac/proxies/${id}`, data);
    return res.data;
  },

  listExpiringProxies: async (): Promise<EcacProxyResponse[]> => {
    const res = await api.get<EcacProxyResponse[]>('/api/v1/ecac/proxies/expiring');
    return res.data;
  },

  getFiscalSituation: async (clientId: string): Promise<EcacFiscalSituationResponse> => {
    const res = await api.get<EcacFiscalSituationResponse>(`/api/v1/ecac/fiscal-situation/${clientId}`);
    return res.data;
  },

  refreshFiscalSituation: async (clientId: string): Promise<{ status: string }> => {
    const res = await api.post<{ status: string }>(`/api/v1/ecac/fiscal-situation/${clientId}/refresh`);
    return res.data;
  },

  listClientsWithoutProxy: async (): Promise<ClientWithoutProxy[]> => {
    const res = await api.get<ClientWithoutProxy[]>('/api/v1/ecac/clients-without-proxy');
    return res.data;
  },
};
