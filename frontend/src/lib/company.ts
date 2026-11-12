/**
 * Dados cadastrais da empresa responsável pelo FiscWise.
 * O CNPJ vem de VITE_COMPANY_CNPJ; vazio → as telas omitem a menção ao CNPJ
 * (nunca exibir número inventado ou placeholder "XX.XXX...").
 */
export const COMPANY_LEGAL_NAME = 'VStack Solutions Ltda';

export const COMPANY_CNPJ: string = String(import.meta.env.VITE_COMPANY_CNPJ ?? '').trim();
