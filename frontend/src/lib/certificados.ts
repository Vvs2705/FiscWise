/**
 * Cofre de certificados A1 e liberação da emissão de NFS-e por emissor.
 *
 * Contrato: POST/GET /api/v1/certificados, DELETE /{id}, POST /{id}/bloquear
 * e /desbloquear; GET/PUT /api/v1/certificados/emissao/{issuer_id} e
 * POST /emissao/{issuer_id}/testar.
 */
import { formatarDocumento, somenteDigitos } from '@/lib/auth';

export type EscopoCertificado = 'escritorio' | 'cliente';
export type StatusCertificado = 'valido' | 'vencido' | 'revogado' | 'bloqueado';
export type ModoCertificado = 'proprio' | 'procuracao';

export interface CertificadoCofre {
  id: string;
  escopo: EscopoCertificado;
  client_id: string | null;
  titular_nome: string | null;
  documento: string | null;
  tipo_documento: 'cnpj' | 'cpf' | string | null;
  emissor: string | null;
  valido_ate: string;
  status: StatusCertificado;
  ultimo_uso: string | null;
  created_at: string;
  dias_para_vencer: number | null;
}

export interface ConfigEmissao {
  modo_certificado: ModoCertificado | null;
  certificado_id: string | null;
  certificado: CertificadoCofre | null;
  procuracao_confirmada_em: string | null;
  ultimo_teste_em: string | null;
  ultimo_teste_ok: boolean | null;
  ultimo_teste_mensagem: string | null;
  emissao_liberada: boolean;
  pendencias: string[];
}

export interface ConfigEmissaoUpdate {
  modo_certificado: ModoCertificado;
  certificado_id?: string | null;
  procuracao_confirmada?: boolean;
}

/** Limite do arquivo .pfx/.p12 (A1 costuma ter 3 a 10 KB). */
export const CERTIFICADO_MAX_BYTES = 50 * 1024;
export const CERTIFICADO_EXTENSOES = ['.pfx', '.p12'] as const;

export const AJUDA_A1_A3 =
  'O A1 é um arquivo (.pfx ou .p12) instalado no computador; é ele que o FiscWise usa para emitir ' +
  'pelo servidor. O A3 fica num token ou cartão com chip e não pode ser enviado: para emitir pelo ' +
  'sistema, peça um A1 à certificadora (Serasa, Certisign, Valid, Soluti ou outra).';

export const AVISO_SEGURANCA =
  'O arquivo e a senha ficam criptografados; ninguém consegue baixar de volta, nem a equipe FiscWise.';

export const RECEITA_PROCURACAO_URL = 'https://servicos.receitafederal.gov.br/';

export interface ArquivoCertificadoLike {
  name: string;
  size: number;
}

/** Valida o formulário de envio. Devolve a primeira mensagem de erro ou null. */
export function validarEnvioCertificado(params: {
  arquivo: ArquivoCertificadoLike | null | undefined;
  senha: string;
  escopo: EscopoCertificado;
  clientId?: string | null;
}): string | null {
  const { arquivo, senha, escopo, clientId } = params;
  if (!arquivo) return 'Escolha o arquivo do certificado (.pfx ou .p12).';
  const nome = arquivo.name.toLowerCase();
  if (!CERTIFICADO_EXTENSOES.some((ext) => nome.endsWith(ext))) {
    return 'Envie o arquivo .pfx ou .p12 do certificado A1. Certificado A3 (token ou cartão) não pode ser enviado.';
  }
  if (arquivo.size <= 0) return 'O arquivo está vazio.';
  if (arquivo.size > CERTIFICADO_MAX_BYTES) {
    return 'O arquivo passa de 50 KB e não parece um certificado A1.';
  }
  if (!senha || !senha.trim()) return 'Digite a senha do certificado.';
  if (escopo === 'cliente' && !clientId) return 'Escolha de qual cliente é o certificado.';
  return null;
}

/** CNPJ/CPF com máscara; sem documento, travessão. */
export function formatarDocumentoCertificado(documento: string | null | undefined): string {
  const d = somenteDigitos(documento ?? '');
  return d ? formatarDocumento(d) : '—';
}

export type TomSelo = 'success' | 'warning' | 'danger' | 'neutral';

/** Selo de validade: válido / vence em N dias (≤30 em destaque) / vencido / bloqueado / revogado. */
export function seloCertificado(
  cert: Pick<CertificadoCofre, 'status' | 'dias_para_vencer' | 'valido_ate'>,
  hoje: Date = new Date(),
): { label: string; tom: TomSelo } {
  if (cert.status === 'bloqueado') return { label: 'Bloqueado', tom: 'neutral' };
  if (cert.status === 'revogado') return { label: 'Revogado', tom: 'neutral' };
  const dias = cert.dias_para_vencer ?? diasAte(cert.valido_ate, hoje);
  if (cert.status === 'vencido' || dias < 0) return { label: 'Vencido', tom: 'danger' };
  if (dias === 0) return { label: 'Vence hoje', tom: 'danger' };
  if (dias <= 30) return { label: `Vence em ${dias} ${dias === 1 ? 'dia' : 'dias'}`, tom: 'warning' };
  return { label: 'Válido', tom: 'success' };
}

/** Dias de hoje até a data (YYYY-MM-DD ou ISO), contando datas de calendário. */
export function diasAte(data: string, hoje: Date = new Date()): number {
  const alvo = new Date(`${data.slice(0, 10)}T00:00:00`);
  const base = new Date(hoje);
  base.setHours(0, 0, 0, 0);
  return Math.round((alvo.getTime() - base.getTime()) / 86_400_000);
}

export function dataBR(iso: string | null | undefined): string {
  if (!iso) return '—';
  const d = iso.slice(0, 10).split('-');
  return d.length === 3 ? `${d[2]}/${d[1]}/${d[0]}` : iso;
}

export function dataHoraBR(iso: string | null | undefined): string {
  if (!iso) return '—';
  const d = new Date(iso);
  return Number.isNaN(d.getTime())
    ? iso
    : d.toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' });
}

/** Certificado pode ser usado para emitir (não vencido, bloqueado nem revogado). */
export function certificadoUtilizavel(cert: CertificadoCofre): boolean {
  return seloCertificado(cert).tom !== 'danger' && cert.status === 'valido';
}

/** Detalhe de erro do backend (409 da emissão traz as pendências no detail). */
export function pendenciasDoErro(detail: unknown): string[] {
  if (Array.isArray(detail)) return detail.filter((x): x is string => typeof x === 'string');
  if (detail && typeof detail === 'object') {
    const d = detail as { pendencias?: unknown; message?: unknown; detail?: unknown };
    if (Array.isArray(d.pendencias)) return d.pendencias.filter((x): x is string => typeof x === 'string');
    if (typeof d.message === 'string') return [d.message];
    if (typeof d.detail === 'string') return [d.detail];
  }
  if (typeof detail === 'string' && detail.trim()) {
    return detail
      .split(/\n|;\s*/)
      .map((s) => s.replace(/^[-•]\s*/, '').trim())
      .filter(Boolean);
  }
  return [];
}

export const MODO_LABEL: Record<ModoCertificado, string> = {
  proprio: 'Certificado da própria empresa',
  procuracao: 'Certificado do escritório com procuração',
};
