import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type {
  CertificadoCofre,
  ConfigEmissao,
  ConfigEmissaoUpdate,
  EscopoCertificado,
} from '@/lib/certificados';

const CHAVE_CERTIFICADOS = 'certificados-cofre';
const CHAVE_EMISSAO = 'certificados-emissao';

export function useCertificadosCofre(filtros?: { client_id?: string; escopo?: EscopoCertificado }) {
  return useQuery({
    queryKey: [CHAVE_CERTIFICADOS, filtros ?? {}],
    queryFn: async (): Promise<CertificadoCofre[]> => {
      const params: Record<string, string> = {};
      if (filtros?.client_id) params.client_id = filtros.client_id;
      if (filtros?.escopo) params.escopo = filtros.escopo;
      const { data } = await api.get<CertificadoCofre[]>('/api/v1/certificados', { params });
      return Array.isArray(data) ? data : [];
    },
  });
}

export interface EnvioCertificado {
  arquivo: File;
  senha: string;
  escopo: EscopoCertificado;
  client_id?: string | null;
}

export function useEnviarCertificado() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ arquivo, senha, escopo, client_id }: EnvioCertificado) => {
      const form = new FormData();
      form.append('arquivo', arquivo);
      form.append('senha', senha);
      form.append('escopo', escopo);
      if (escopo === 'cliente' && client_id) form.append('client_id', client_id);
      const { data } = await api.post<CertificadoCofre>('/api/v1/certificados', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [CHAVE_CERTIFICADOS] });
      qc.invalidateQueries({ queryKey: [CHAVE_EMISSAO] });
    },
  });
}

function useAcaoCertificado(acao: (id: string) => Promise<unknown>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: acao,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [CHAVE_CERTIFICADOS] });
      qc.invalidateQueries({ queryKey: [CHAVE_EMISSAO] });
    },
  });
}

export function useRemoverCertificado() {
  return useAcaoCertificado((id) => api.delete(`/api/v1/certificados/${id}`));
}

export function useBloquearCertificado() {
  return useAcaoCertificado((id) => api.post(`/api/v1/certificados/${id}/bloquear`));
}

export function useDesbloquearCertificado() {
  return useAcaoCertificado((id) => api.post(`/api/v1/certificados/${id}/desbloquear`));
}

export function useConfigEmissao(issuerId: string | null | undefined) {
  return useQuery({
    queryKey: [CHAVE_EMISSAO, issuerId],
    queryFn: async (): Promise<ConfigEmissao> => {
      const { data } = await api.get<ConfigEmissao>(`/api/v1/certificados/emissao/${issuerId}`);
      return { ...data, pendencias: Array.isArray(data?.pendencias) ? data.pendencias : [] };
    },
    enabled: !!issuerId,
  });
}

export function useSalvarConfigEmissao(issuerId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: ConfigEmissaoUpdate) => {
      const { data } = await api.put<ConfigEmissao>(`/api/v1/certificados/emissao/${issuerId}`, body);
      return data;
    },
    onSuccess: (data) => {
      qc.setQueryData([CHAVE_EMISSAO, issuerId], data);
      qc.invalidateQueries({ queryKey: [CHAVE_EMISSAO, issuerId] });
    },
  });
}

export function useTestarEmissao(issuerId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data } = await api.post<ConfigEmissao>(`/api/v1/certificados/emissao/${issuerId}/testar`);
      return data;
    },
    onSuccess: (data) => {
      qc.setQueryData([CHAVE_EMISSAO, issuerId], data);
      qc.invalidateQueries({ queryKey: [CHAVE_CERTIFICADOS] });
    },
  });
}
