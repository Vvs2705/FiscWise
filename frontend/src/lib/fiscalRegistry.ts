/** Leitura da situação cadastral do CNPJ (Monitor Fiscal / BrasilAPI). */

export type RegistryTone = 'success' | 'warning' | 'error' | 'default';

export interface RegistryBadge {
  label: string;
  tone: RegistryTone;
}

const BADGES: Record<string, RegistryBadge> = {
  ATIVA: { label: 'Ativa', tone: 'success' },
  SUSPENSA: { label: 'Suspensa', tone: 'warning' },
  INAPTA: { label: 'Inapta', tone: 'error' },
  BAIXADA: { label: 'Baixada', tone: 'error' },
  NULA: { label: 'Nula', tone: 'error' },
  ERRO_CONSULTA: { label: 'Erro na consulta', tone: 'warning' },
  PENDENTE: { label: 'Não consultada', tone: 'default' },
};

export function registryBadge(status: string | null | undefined): RegistryBadge {
  const key = (status || 'PENDENTE').trim().toUpperCase();
  return BADGES[key] ?? { label: key.charAt(0) + key.slice(1).toLowerCase(), tone: 'default' };
}

/** Datas da BrasilAPI vêm como AAAA-MM-DD; mostra DD/MM/AAAA sem passar por fuso. */
export function formatRegistryDate(value: string | null | undefined): string | null {
  if (!value) return null;
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(value);
  return match ? `${match[3]}/${match[2]}/${match[1]}` : value;
}

/** Opção pelo Simples/MEI: true/false/null da BrasilAPI → texto. */
export function formatOption(value: boolean | null | undefined): string {
  if (value === true) return 'Sim';
  if (value === false) return 'Não';
  return 'Não informado';
}
