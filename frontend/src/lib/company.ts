/**
 * Dados cadastrais da empresa responsável pelo FiscWise.
 * Conferidos em consulta pública ao CNPJ (2026-11-12): empresário individual,
 * situação ativa, sede em Caieiras/SP. VITE_COMPANY_CNPJ, se definido, sobrepõe o padrão.
 */

/** Como a empresa é identificada nos textos legais (nome comercial + natureza). */
export const COMPANY_LEGAL_NAME = 'VStack Solutions';

export const COMPANY_CNPJ: string =
  String(import.meta.env.VITE_COMPANY_CNPJ ?? '').trim() || '40.204.602/0001-85';

export const COMPANY_CITY = 'Caieiras/SP';

/** Endereço da sede (informado pelo dono em 21/11/2026). CEP ainda não informado. */
export const COMPANY_ADDRESS = `Rua Vicente Lisa, 119, ${COMPANY_CITY}`;
