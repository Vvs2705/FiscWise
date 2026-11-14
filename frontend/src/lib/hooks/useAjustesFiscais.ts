import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import {
  montarCorpoAjuste,
  type AjusteAtivo,
  type AjusteFiscal,
  type AjusteFiscalEquipe,
  type AjusteFiscalEquipeDetalhe,
  type AjusteFiscalInput,
  type AjustesAtivosResposta,
  type ObrigacaoOpcao,
} from '@/lib/ajustesFiscais';

const ajustesKey = ['ajustes-fiscais'] as const;
const equipeKey = ['equipe-ajustes-fiscais'] as const;

export function useAjustesFiscais() {
  return useQuery({
    queryKey: [...ajustesKey, 'lista'],
    queryFn: async () => {
      const { data } = await api.get<AjusteFiscal[]>('/api/v1/ajustes-fiscais');
      return data;
    },
    staleTime: 60_000,
    retry: false,
  });
}

export function useObrigacoesAjustaveis() {
  return useQuery({
    queryKey: [...ajustesKey, 'obrigacoes'],
    queryFn: async () => {
      const { data } = await api.get<ObrigacaoOpcao[]>('/api/v1/ajustes-fiscais/obrigacoes');
      return data;
    },
    staleTime: 10 * 60_000,
    retry: false,
  });
}

/** Aceita {escritorio, gerais} ou uma lista com `escopo` em cada item. */
export function normalizarAjustesAtivos(data: unknown): AjustesAtivosResposta {
  if (Array.isArray(data)) {
    const itens = data as AjusteAtivo[];
    return {
      escritorio: itens.filter((i) => i.escopo !== 'geral'),
      gerais: itens.filter((i) => i.escopo === 'geral'),
    };
  }
  const obj = (data ?? {}) as Partial<AjustesAtivosResposta>;
  return { escritorio: obj.escritorio ?? [], gerais: obj.gerais ?? [] };
}

export function useAjustesAtivos() {
  return useQuery({
    queryKey: [...ajustesKey, 'ativos'],
    queryFn: async () => {
      const { data } = await api.get<unknown>('/api/v1/ajustes-fiscais/ajustes-ativos');
      return normalizarAjustesAtivos(data);
    },
    staleTime: 60_000,
    retry: false,
  });
}

export function useCriarAjusteFiscal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: AjusteFiscalInput) => {
      const { data } = await api.post<AjusteFiscal>('/api/v1/ajustes-fiscais', montarCorpoAjuste(input));
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ajustesKey });
      // Prazos podem ter sido recalculados.
      qc.invalidateQueries({ queryKey: ['obligation-instances'] });
    },
  });
}

export function useDesfazerAjusteFiscal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/api/v1/ajustes-fiscais/${id}`);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ajustesKey });
      qc.invalidateQueries({ queryKey: ['obligation-instances'] });
    },
  });
}

// ─── Equipe FiscWise ─────────────────────────────────────────────────────────

export interface FiltrosEquipe {
  status?: string;
  uf?: string;
  tipo?: string;
}

export function useEquipeAjustes(filtros: FiltrosEquipe) {
  return useQuery({
    queryKey: [...equipeKey, 'lista', filtros],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filtros.status) params.set('status', filtros.status);
      if (filtros.uf) params.set('uf', filtros.uf);
      if (filtros.tipo) params.set('tipo', filtros.tipo);
      const qs = params.toString();
      const { data } = await api.get<AjusteFiscalEquipe[]>(
        `/api/v1/equipe/ajustes-fiscais${qs ? `?${qs}` : ''}`,
      );
      return data;
    },
    staleTime: 30_000,
    retry: false,
  });
}

export function useEquipeAjusteDetalhe(id: string | null) {
  return useQuery({
    queryKey: [...equipeKey, 'detalhe', id],
    queryFn: async () => {
      const { data } = await api.get<AjusteFiscalEquipeDetalhe>(`/api/v1/equipe/ajustes-fiscais/${id}`);
      return data;
    },
    enabled: !!id,
    retry: false,
  });
}

export type AcaoEquipe = 'em-analise' | 'regra-geral' | 'recusar';

export function useAcaoEquipeAjuste() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, acao, resposta }: { id: string; acao: AcaoEquipe; resposta?: string }) => {
      const body = acao === 'recusar' ? { resposta: resposta ?? '' } : resposta ? { resposta } : {};
      const { data } = await api.post<AjusteFiscalEquipe>(`/api/v1/equipe/ajustes-fiscais/${id}/${acao}`, body);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: equipeKey });
    },
  });
}

/** `equipe_fiscwise` vem de /auth/me; o menu usa para mostrar a fila da equipe. */
export function useEquipeFiscwise(enabled = true) {
  return useQuery({
    queryKey: ['auth-me', 'equipe'],
    queryFn: async () => {
      const { data } = await api.get<{ equipe_fiscwise?: boolean }>('/api/v1/auth/me');
      return !!data?.equipe_fiscwise;
    },
    enabled,
    staleTime: 10 * 60_000,
    retry: false,
  });
}
