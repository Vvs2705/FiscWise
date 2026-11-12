/**
 * Procurações — camada fina sobre o módulo e-CAC (`/api/v1/ecac/proxies`).
 *
 * Não existe API própria de "powers-of-attorney": a página de Procurações usa
 * os mesmos hooks/serviço da aba e-CAC e só adiciona mapeamentos puros
 * (status efetivo, dias até o vencimento, dados para renovação).
 */
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useCreateProxy, useProxies, useUpdateProxy } from '@/features/ecac/hooks/useEcac';
import {
  ecacService,
  type EcacProxyCreate,
  type EcacProxyResponse,
} from '@/features/ecac/services/ecac.service';

export type PowerOfAttorney = EcacProxyResponse;
export type PowerOfAttorneyCreate = EcacProxyCreate;

/** Valores gravados pelo backend (domain/ecac): `ativa` na criação, `revogada` ao revogar. */
export type PoaStatus = 'ativa' | 'vencida' | 'revogada';

export const REVOKED_STATUS: PoaStatus = 'revogada';

export function onlyDigits(value: string | null | undefined): string {
  return (value ?? '').replace(/\D/g, '');
}

/** Data de hoje como AAAA-MM-DD no fuso local (evita o −1 dia de `toISOString` em BRT). */
export function todayISO(now: Date = new Date()): string {
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, '0');
  const d = String(now.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

/** Dias corridos de `today` até `dateISO` (AAAA-MM-DD); `null` sem data. */
export function daysUntil(dateISO: string | null | undefined, today: string = todayISO()): number | null {
  if (!dateISO) return null;
  const toUTC = (iso: string) => {
    const [y, m, d] = iso.slice(0, 10).split('-').map(Number);
    return Date.UTC(y, m - 1, d);
  };
  return Math.round((toUTC(dateISO) - toUTC(today)) / 86_400_000);
}

/**
 * Status exibido: o backend não marca `vencida` sozinho, então uma procuração
 * `ativa` com validade passada é tratada como vencida. `revogada` é terminal.
 */
export function effectiveStatus(
  poa: Pick<PowerOfAttorney, 'status' | 'data_validade'>,
  today: string = todayISO(),
): PoaStatus {
  const raw = (poa.status ?? '').toLowerCase();
  if (raw === 'revogada' || raw === 'revoked') return 'revogada';
  if (raw === 'vencida' || raw === 'expired') return 'vencida';
  const days = daysUntil(poa.data_validade, today);
  if (days !== null && days < 0) return 'vencida';
  return 'ativa';
}

/** Pré-preenchimento do formulário de renovação a partir da procuração antiga. */
export function renewalDefaults(poa: PowerOfAttorney, today: string = todayISO()) {
  return {
    client_id: poa.client_id ?? '',
    outorgante_cpf_cnpj: poa.outorgante_cpf_cnpj,
    outorgante_nome: poa.outorgante_nome ?? '',
    procurador_cpf: poa.procurador_cpf,
    tipo: poa.tipo ?? 'e-CAC',
    data_inicio: today,
    data_validade: '',
  };
}

export function usePowersOfAttorney() {
  return useProxies();
}

export function useCreatePowerOfAttorney() {
  return useCreateProxy();
}

export function useRevokePowerOfAttorney() {
  const update = useUpdateProxy();
  return {
    ...update,
    mutateAsync: (id: string) => update.mutateAsync({ id, data: { status: REVOKED_STATUS } }),
  };
}

/** Renovar = cadastrar a nova e, só se der certo, revogar a antiga. */
export function useRenewPowerOfAttorney() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ oldId, data }: { oldId: string; data: PowerOfAttorneyCreate }) => {
      const created = await ecacService.createProxy(data);
      await ecacService.updateProxy(oldId, { status: REVOKED_STATUS });
      return created;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ecac-proxies'] });
      qc.invalidateQueries({ queryKey: ['ecac-proxies-expiring'] });
      qc.invalidateQueries({ queryKey: ['ecac-clients-without-proxy'] });
    },
  });
}
